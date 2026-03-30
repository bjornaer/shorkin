"""Tests for the transport key manager."""

import asyncio

import pytest

from shorkin.qkd.channel import SimulatedChannel
from shorkin.qkd.protocol import QKDError
from shorkin.transport._key_manager import TransportKeyManager
from shorkin.transport._messages import KeyExchangeInit


def run_async(coro):
    """Helper to run async code in tests."""
    return asyncio.new_event_loop().run_until_complete(coro)


class TestTransportKeyManager:
    def test_create_with_default_protocol(self):
        mgr = TransportKeyManager(seed=42)
        assert mgr.protocol_name == "bb84"

    def test_create_with_e91(self):
        mgr = TransportKeyManager(protocol="e91", seed=42)
        assert mgr.protocol_name == "e91"

    def test_unknown_protocol_raises(self):
        with pytest.raises(ValueError, match="Unknown protocol"):
            TransportKeyManager(protocol="unknown")

    def test_initiate_exchange(self):
        mgr = TransportKeyManager(seed=42)
        init = run_async(mgr.initiate_exchange("peer1"))
        assert init.protocol == "bb84"
        assert init.peer_id == "peer1"
        assert init.session_id

    def test_run_exchange(self):
        mgr = TransportKeyManager(seed=42)
        init = run_async(mgr.initiate_exchange("peer1"))
        key = run_async(mgr.run_exchange(init.session_id))
        assert len(key) == 32  # 256-bit key

    def test_encrypt_decrypt_roundtrip(self):
        mgr = TransportKeyManager(seed=42)
        init = run_async(mgr.initiate_exchange("peer1"))
        run_async(mgr.run_exchange(init.session_id))

        plaintext = b"secret message"
        ct = mgr.encrypt_payload(init.session_id, plaintext)
        pt = mgr.decrypt_payload(init.session_id, ct)
        assert pt == plaintext

    def test_encrypt_no_session_raises(self):
        mgr = TransportKeyManager(seed=42)
        with pytest.raises(QKDError, match="No active key"):
            mgr.encrypt_payload("nonexistent", b"data")

    def test_handle_init(self):
        mgr = TransportKeyManager(seed=42)
        init = KeyExchangeInit(protocol="bb84", peer_id="server1")
        confirm = run_async(mgr.handle_init(init))
        assert confirm.status == "ok"
        assert confirm.key_hash  # non-empty hash

    def test_get_session_for_peer(self):
        mgr = TransportKeyManager(seed=42)
        init = run_async(mgr.initiate_exchange("peer1"))
        run_async(mgr.run_exchange(init.session_id))
        assert mgr.get_session_for_peer("peer1") == init.session_id

    def test_get_session_for_unknown_peer(self):
        mgr = TransportKeyManager(seed=42)
        assert mgr.get_session_for_peer("nobody") is None

    def test_b92_protocol(self):
        mgr = TransportKeyManager(protocol="b92", seed=42, num_qubits=8000)
        init = run_async(mgr.initiate_exchange("peer1"))
        key = run_async(mgr.run_exchange(init.session_id))
        assert len(key) == 32

    def test_e91_protocol(self):
        mgr = TransportKeyManager(protocol="e91", seed=42, num_qubits=20000)
        init = run_async(mgr.initiate_exchange("peer1"))
        key = run_async(mgr.run_exchange(init.session_id))
        assert len(key) == 32

    def test_key_hash(self):
        mgr = TransportKeyManager(seed=42)
        init = run_async(mgr.initiate_exchange("peer1"))
        run_async(mgr.run_exchange(init.session_id))
        h = mgr.get_key_hash(init.session_id)
        assert h is not None
        assert len(h) == 64  # SHA-256 hex digest
