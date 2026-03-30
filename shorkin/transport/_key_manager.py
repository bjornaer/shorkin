"""Transport-level key lifecycle management.

Bridges QKD protocol engines and transport layers (HTTP/gRPC).
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from shorkin.qkd.b92 import B92
from shorkin.qkd.bb84 import BB84
from shorkin.qkd.channel import SimulatedChannel
from shorkin.qkd.e91 import E91
from shorkin.qkd.encryption import decrypt, encrypt
from shorkin.qkd.key_store import KeyStore
from shorkin.qkd.protocol import QKDError
from shorkin.transport._messages import (
    KeyConfirmation,
    KeyExchangeInit,
    SessionStatus,
)

_PROTOCOL_CLASSES = {
    "bb84": BB84,
    "b92": B92,
    "e91": E91,
}


class TransportKeyManager:
    """Manages QKD key exchange sessions for HTTP/gRPC transports.

    This is the bridge between the QKD protocol engines and the
    transport layer. It handles:
    - Initiating new key exchange sessions
    - Running QKD protocols to derive shared keys
    - Storing and rotating keys
    - Encrypting/decrypting payloads using active session keys
    """

    def __init__(
        self,
        protocol: str = "bb84",
        channel: SimulatedChannel | None = None,
        key_store: KeyStore | None = None,
        num_qubits: int = 4096,
        target_key_bits: int = 256,
        seed: int | None = None,
    ):
        if protocol not in _PROTOCOL_CLASSES:
            raise ValueError(
                f"Unknown protocol '{protocol}'. "
                f"Available: {', '.join(_PROTOCOL_CLASSES)}"
            )
        self._protocol_name = protocol
        self._channel = channel or SimulatedChannel(seed=seed)
        self._key_store = key_store or KeyStore()
        self._num_qubits = num_qubits
        self._target_key_bits = target_key_bits
        self._seed = seed
        self._sessions: dict[str, SessionStatus] = {}
        self._peer_sessions: dict[str, str] = {}  # peer_id -> session_id

    @property
    def protocol_name(self) -> str:
        return self._protocol_name

    def _create_protocol(self):
        """Create a fresh protocol instance."""
        cls = _PROTOCOL_CLASSES[self._protocol_name]
        if self._protocol_name == "e91":
            return cls(seed=self._seed, bell_threshold=0.0)
        return cls(seed=self._seed)

    async def initiate_exchange(self, peer_id: str) -> KeyExchangeInit:
        """Start a new QKD key exchange session with a peer."""
        init = KeyExchangeInit(
            protocol=self._protocol_name,
            num_qubits=self._num_qubits,
            target_key_bits=self._target_key_bits,
            peer_id=peer_id,
        )
        self._sessions[init.session_id] = SessionStatus.INITIATING
        self._peer_sessions[peer_id] = init.session_id
        return init

    async def run_exchange(self, session_id: str) -> bytes:
        """Execute the QKD protocol and store the derived key.

        This runs the protocol simulation in a thread to avoid
        blocking the async event loop.
        """
        protocol = self._create_protocol()

        def _run():
            num = self._num_qubits
            if self._protocol_name == "e91":
                num = max(num, 20000)
            elif self._protocol_name == "b92":
                num = max(num, 8000)
            return protocol.generate_key(
                num_qubits=num,
                channel=self._channel,
                target_key_bits=self._target_key_bits,
            )

        try:
            result = await asyncio.get_event_loop().run_in_executor(None, _run)
        except QKDError:
            self._sessions[session_id] = SessionStatus.ABORTED
            raise

        self._key_store.store(session_id, result.final_key, self._protocol_name)
        self._sessions[session_id] = SessionStatus.ACTIVE
        return result.final_key

    async def handle_init(self, init: KeyExchangeInit) -> KeyConfirmation:
        """Handle an incoming key exchange initiation.

        Runs the QKD protocol and returns a confirmation.
        """
        self._sessions[init.session_id] = SessionStatus.INITIATING
        if init.peer_id:
            self._peer_sessions[init.peer_id] = init.session_id

        key = await self.run_exchange(init.session_id)
        key_hash = hashlib.sha256(key).hexdigest()

        return KeyConfirmation(
            session_id=init.session_id,
            key_hash=key_hash,
            status="ok",
        )

    def encrypt_payload(self, session_id: str, data: bytes) -> bytes:
        """Encrypt data using the session's QKD-derived key."""
        key = self._key_store.get(session_id)
        if key is None:
            raise QKDError(f"No active key for session {session_id}")
        return encrypt(data, key)

    def decrypt_payload(self, session_id: str, data: bytes) -> bytes:
        """Decrypt data using the session's QKD-derived key."""
        key = self._key_store.get(session_id)
        if key is None:
            raise QKDError(f"No active key for session {session_id}")
        return decrypt(data, key)

    def get_session_for_peer(self, peer_id: str) -> str | None:
        """Get the active session ID for a peer."""
        session_id = self._peer_sessions.get(peer_id)
        if session_id and not self._key_store.is_expired(session_id):
            return session_id
        return None

    def get_session_status(self, session_id: str) -> SessionStatus | None:
        """Get the status of a session."""
        return self._sessions.get(session_id)

    def get_key_hash(self, session_id: str) -> str | None:
        """Get the SHA-256 hash of a session's key (for verification)."""
        key = self._key_store.get(session_id)
        if key is None:
            return None
        return hashlib.sha256(key).hexdigest()
