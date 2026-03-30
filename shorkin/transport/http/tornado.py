"""Tornado integration for QKD-secured communication.

Usage as a mixin:
    import tornado.web
    from shorkin.transport.http.tornado import QKDRequestMixin

    class SecureHandler(QKDRequestMixin, tornado.web.RequestHandler):
        def get(self):
            self.write(b"This response will be encrypted if QKD session is active")

Usage as a decorator:
    from shorkin.transport.http.tornado import qkd_secured

    class MyHandler(tornado.web.RequestHandler):
        @qkd_secured(protocol="bb84")
        def get(self):
            self.write(b"encrypted response")
"""

from __future__ import annotations

import asyncio
import functools
import json
from typing import Any, Callable

try:
    import tornado.web
except ImportError as e:
    raise ImportError(
        "Tornado integration requires the 'tornado' extra: "
        "pip install shorkin[tornado]"
    ) from e

from shorkin.transport._key_manager import TransportKeyManager
from shorkin.transport.http._base import (
    HEADER_ENCRYPTED,
    HEADER_SESSION_ID,
    QKD_INITIATE_PATH,
    QKD_STATUS_PATH,
    QKDHTTPHandler,
)

# Module-level shared handler (created on first use)
_shared_handlers: dict[str, QKDHTTPHandler] = {}


def _get_handler(protocol: str = "bb84", **kwargs: Any) -> QKDHTTPHandler:
    """Get or create a shared QKD handler for a protocol."""
    if protocol not in _shared_handlers:
        _shared_handlers[protocol] = QKDHTTPHandler(protocol=protocol, **kwargs)
    return _shared_handlers[protocol]


class QKDRequestMixin:
    """Mixin for Tornado RequestHandler that adds QKD support.

    Automatically encrypts response body if a QKD session is active.
    Provides helper methods for encryption/decryption.
    """

    _qkd_handler: QKDHTTPHandler | None = None
    _qkd_protocol: str = "bb84"

    def initialize(self, qkd_protocol: str = "bb84", **kwargs: Any):
        self._qkd_protocol = qkd_protocol
        self._qkd_handler = _get_handler(qkd_protocol)
        super().initialize(**kwargs)  # type: ignore[misc]

    @property
    def qkd_session_id(self) -> str | None:
        """Get the QKD session ID from the request headers."""
        return self.request.headers.get(HEADER_SESSION_ID)  # type: ignore[attr-defined]

    def qkd_decrypt(self, data: bytes) -> bytes:
        """Decrypt request data using the QKD session key."""
        sid = self.qkd_session_id
        if sid is None or self._qkd_handler is None:
            raise ValueError("No active QKD session")
        return self._qkd_handler.key_manager.decrypt_payload(sid, data)

    def qkd_encrypt(self, data: bytes) -> bytes:
        """Encrypt data using the QKD session key."""
        sid = self.qkd_session_id
        if sid is None or self._qkd_handler is None:
            raise ValueError("No active QKD session")
        return self._qkd_handler.key_manager.encrypt_payload(sid, data)

    def finish(self, chunk=None):
        """Override finish to encrypt response if QKD session is active."""
        sid = self.qkd_session_id
        if sid and self._qkd_handler and chunk:
            if isinstance(chunk, str):
                chunk = chunk.encode()
            if isinstance(chunk, bytes):
                encrypted, headers = self._qkd_handler.try_encrypt_response(sid, chunk)
                if headers:
                    for key, value in headers.items():
                        self.set_header(key, value)  # type: ignore[attr-defined]
                    chunk = encrypted
        super().finish(chunk)  # type: ignore[misc]


class QKDInitiateHandler(tornado.web.RequestHandler):
    """Tornado handler for QKD key exchange initiation."""

    def initialize(self, qkd_handler: QKDHTTPHandler):
        self._handler = qkd_handler

    async def post(self):
        body = self.request.body
        status, headers, resp_body = await self._handler.handle_initiate(body)
        self.set_status(status)
        for key, value in headers.items():
            self.set_header(key, value)
        self.set_header("Content-Type", "application/json")
        self.write(resp_body)


class QKDStatusHandler(tornado.web.RequestHandler):
    """Tornado handler for QKD session status."""

    def initialize(self, qkd_handler: QKDHTTPHandler):
        self._handler = qkd_handler

    async def get(self):
        session_id = self.request.headers.get(HEADER_SESSION_ID, "")
        status, headers, resp_body = await self._handler.handle_status(session_id)
        self.set_status(status)
        for key, value in headers.items():
            self.set_header(key, value)
        self.set_header("Content-Type", "application/json")
        self.write(resp_body)


def qkd_routes(protocol: str = "bb84", **kwargs: Any) -> list:
    """Create Tornado URL routes for QKD endpoints.

    Usage:
        app = tornado.web.Application(
            qkd_routes("bb84") + [
                (r"/api/data", MyHandler),
            ]
        )
    """
    handler = _get_handler(protocol, **kwargs)
    return [
        (QKD_INITIATE_PATH, QKDInitiateHandler, {"qkd_handler": handler}),
        (QKD_STATUS_PATH, QKDStatusHandler, {"qkd_handler": handler}),
    ]


def qkd_secured(
    protocol: str = "bb84",
    key_manager: TransportKeyManager | None = None,
    **kwargs: Any,
) -> Callable:
    """Decorator for Tornado handler methods that encrypts responses.

    Usage:
        class MyHandler(tornado.web.RequestHandler):
            @qkd_secured(protocol="bb84")
            def get(self):
                self.write(b"will be encrypted")
    """
    handler = _get_handler(protocol, **kwargs)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            return result

        return wrapper

    return decorator
