"""Framework-agnostic QKD HTTP handler logic.

All framework-specific integrations delegate to this module for
the core QKD key exchange and payload encryption/decryption logic.
"""

from __future__ import annotations

import json
from typing import Any

from shorkin.transport._key_manager import TransportKeyManager
from shorkin.transport._messages import (
    KeyConfirmation,
    KeyExchangeInit,
    SessionStatus,
)

# HTTP headers used for QKD session management
HEADER_SESSION_ID = "X-QKD-Session-Id"
HEADER_PROTOCOL = "X-QKD-Protocol"
HEADER_STATUS = "X-QKD-Status"
HEADER_ENCRYPTED = "X-QKD-Encrypted"

# Well-known endpoints for QKD negotiation
QKD_INITIATE_PATH = "/.well-known/qkd/initiate"
QKD_STATUS_PATH = "/.well-known/qkd/status"

# Content type for encrypted payloads
ENCRYPTED_CONTENT_TYPE = "application/octet-stream"


class QKDHTTPHandler:
    """Framework-agnostic handler for QKD HTTP integration.

    Manages QKD key negotiation endpoints and transparent
    encryption/decryption of request/response bodies.
    """

    def __init__(
        self,
        key_manager: TransportKeyManager | None = None,
        protocol: str = "bb84",
        strict: bool = False,
        **kwargs: Any,
    ):
        """
        Args:
            key_manager: Shared TransportKeyManager instance. Created if None.
            protocol: QKD protocol to use (bb84, b92, e91).
            strict: If True, reject requests without active QKD session.
            **kwargs: Passed to TransportKeyManager if created.
        """
        self.key_manager = key_manager or TransportKeyManager(
            protocol=protocol, **kwargs
        )
        self.strict = strict

    def is_qkd_endpoint(self, path: str) -> bool:
        """Check if the path is a QKD negotiation endpoint."""
        return path in (QKD_INITIATE_PATH, QKD_STATUS_PATH)

    async def handle_initiate(self, body: bytes) -> tuple[int, dict, bytes]:
        """Handle POST /.well-known/qkd/initiate.

        Returns (status_code, headers, response_body).
        """
        try:
            data = json.loads(body) if body else {}
            init = KeyExchangeInit.from_dict(data)
            confirm = await self.key_manager.handle_init(init)
            response_body = json.dumps(confirm.to_dict()).encode()
            headers = {
                HEADER_SESSION_ID: confirm.session_id,
                HEADER_PROTOCOL: self.key_manager.protocol_name,
                HEADER_STATUS: SessionStatus.ACTIVE.value,
            }
            return 200, headers, response_body
        except Exception as e:
            error_body = json.dumps({"error": str(e)}).encode()
            return 500, {}, error_body

    async def handle_status(self, session_id: str) -> tuple[int, dict, bytes]:
        """Handle GET/POST /.well-known/qkd/status."""
        status = self.key_manager.get_session_status(session_id)
        if status is None:
            return 404, {}, json.dumps({"error": "Session not found"}).encode()

        body = json.dumps({
            "session_id": session_id,
            "status": status.value,
            "protocol": self.key_manager.protocol_name,
        }).encode()
        return 200, {HEADER_STATUS: status.value}, body

    def try_decrypt_request(
        self, session_id: str | None, body: bytes, is_encrypted: bool
    ) -> bytes:
        """Attempt to decrypt request body if session is active."""
        if session_id and is_encrypted and body:
            return self.key_manager.decrypt_payload(session_id, body)
        return body

    def try_encrypt_response(
        self, session_id: str | None, body: bytes
    ) -> tuple[bytes, dict]:
        """Attempt to encrypt response body if session is active.

        Returns (body, extra_headers).
        """
        if session_id and body:
            try:
                encrypted = self.key_manager.encrypt_payload(session_id, body)
                headers = {
                    HEADER_ENCRYPTED: "true",
                    HEADER_SESSION_ID: session_id,
                }
                return encrypted, headers
            except Exception:
                pass
        return body, {}

    def should_reject(self, session_id: str | None, path: str) -> bool:
        """In strict mode, reject requests without active QKD session."""
        if not self.strict:
            return False
        if self.is_qkd_endpoint(path):
            return False
        return session_id is None
