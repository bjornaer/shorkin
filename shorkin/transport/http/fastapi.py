"""FastAPI middleware and dependency injection for QKD-secured communication.

Usage as middleware:
    from fastapi import FastAPI
    from shorkin.transport.http.fastapi import QKDMiddleware

    app = FastAPI()
    app.add_middleware(QKDMiddleware, protocol="bb84")

Usage as dependency:
    from fastapi import Depends, FastAPI
    from shorkin.transport.http.fastapi import qkd_session, QKDSession

    app = FastAPI()

    @app.get("/secure")
    async def secure_endpoint(qkd: QKDSession = Depends(qkd_session("bb84"))):
        encrypted = qkd.encrypt(b"secret data")
        return {"data": encrypted.hex()}

Usage as decorator:
    from shorkin.transport.http.fastapi import qkd_secured

    @app.get("/secure")
    @qkd_secured(protocol="bb84")
    async def secure_endpoint(request: Request):
        return {"message": "This response will be encrypted"}
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any, Callable

try:
    from fastapi import Request
except ImportError as e:
    raise ImportError(
        "FastAPI integration requires the 'fastapi' extra: "
        "pip install shorkin[fastapi]"
    ) from e

from shorkin.transport._key_manager import TransportKeyManager
from shorkin.transport.http._base import HEADER_SESSION_ID, QKDHTTPHandler
from shorkin.transport.http.starlette import QKDMiddleware as StarletteQKDMiddleware


# Re-export the Starlette middleware (FastAPI is built on Starlette)
class QKDMiddleware(StarletteQKDMiddleware):
    """FastAPI middleware for QKD-encrypted communication.

    Same as the Starlette middleware since FastAPI is built on Starlette.
    """

    pass


@dataclass
class QKDSession:
    """QKD session context for FastAPI dependency injection."""

    session_id: str | None
    key_manager: TransportKeyManager

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data with the session's QKD key."""
        if self.session_id is None:
            raise ValueError("No active QKD session")
        return self.key_manager.encrypt_payload(self.session_id, data)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data with the session's QKD key."""
        if self.session_id is None:
            raise ValueError("No active QKD session")
        return self.key_manager.decrypt_payload(self.session_id, data)

    @property
    def is_active(self) -> bool:
        return self.session_id is not None


def qkd_session(
    protocol: str = "bb84",
    key_manager: TransportKeyManager | None = None,
    **kwargs: Any,
) -> Callable:
    """FastAPI dependency factory for QKD session injection.

    Usage:
        @app.get("/secure")
        async def endpoint(qkd: QKDSession = Depends(qkd_session("bb84"))):
            if qkd.is_active:
                encrypted = qkd.encrypt(b"data")
    """
    mgr = key_manager or TransportKeyManager(protocol=protocol, **kwargs)

    async def _dependency(request: Request) -> QKDSession:
        session_id = request.headers.get(HEADER_SESSION_ID)
        return QKDSession(session_id=session_id, key_manager=mgr)

    return _dependency


def qkd_secured(
    protocol: str = "bb84",
    key_manager: TransportKeyManager | None = None,
    **kwargs: Any,
) -> Callable:
    """Decorator for FastAPI route handlers that require QKD encryption.

    The decorated handler receives the original request. The response
    body is automatically encrypted with the session key.

    Usage:
        @app.get("/secure")
        @qkd_secured(protocol="bb84")
        async def endpoint(request: Request):
            return {"message": "encrypted response"}
    """
    mgr = key_manager or TransportKeyManager(protocol=protocol, **kwargs)
    handler = QKDHTTPHandler(key_manager=mgr)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the Request object in args/kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            if request:
                session_id = request.headers.get(HEADER_SESSION_ID)
                if session_id and isinstance(result, (bytes, str)):
                    body = result.encode() if isinstance(result, str) else result
                    encrypted, _ = handler.try_encrypt_response(session_id, body)
                    return encrypted

            return result

        return wrapper

    return decorator


import asyncio  # noqa: E402 (imported at end to avoid circular issues)
