"""Starlette middleware for QKD-secured communication.

Usage:
    from starlette.applications import Starlette
    from shorkin.transport.http.starlette import QKDMiddleware

    app = Starlette()
    app.add_middleware(QKDMiddleware, protocol="bb84")
"""

from __future__ import annotations

from typing import Any

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
except ImportError as e:
    raise ImportError(
        "Starlette integration requires the 'starlette' extra: "
        "pip install shorkin[starlette]"
    ) from e

from shorkin.transport.http._base import (
    ENCRYPTED_CONTENT_TYPE,
    HEADER_ENCRYPTED,
    HEADER_SESSION_ID,
    QKD_INITIATE_PATH,
    QKD_STATUS_PATH,
    QKDHTTPHandler,
)


class QKDMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for QKD-encrypted communication.

    Handles QKD key exchange at well-known endpoints and
    transparently encrypts/decrypts request and response bodies
    for sessions with active QKD keys.
    """

    def __init__(self, app, protocol: str = "bb84", strict: bool = False, **kwargs: Any):
        super().__init__(app)
        self._handler = QKDHTTPHandler(protocol=protocol, strict=strict, **kwargs)

    @property
    def handler(self) -> QKDHTTPHandler:
        return self._handler

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Handle QKD negotiation endpoints
        if path == QKD_INITIATE_PATH and request.method == "POST":
            body = await request.body()
            status, headers, resp_body = await self._handler.handle_initiate(body)
            return Response(
                content=resp_body,
                status_code=status,
                headers=headers,
                media_type="application/json",
            )

        if path == QKD_STATUS_PATH:
            session_id = request.headers.get(HEADER_SESSION_ID, "")
            status, headers, resp_body = await self._handler.handle_status(session_id)
            return Response(
                content=resp_body,
                status_code=status,
                headers=headers,
                media_type="application/json",
            )

        # Check session
        session_id = request.headers.get(HEADER_SESSION_ID)

        if self._handler.should_reject(session_id, path):
            return Response(
                content=b'{"error": "QKD session required"}',
                status_code=403,
                media_type="application/json",
            )

        # Decrypt request body if encrypted
        is_encrypted = request.headers.get(HEADER_ENCRYPTED, "").lower() == "true"

        # Pass through to the application
        response = await call_next(request)

        # Encrypt response body if session is active
        if session_id:
            resp_body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    resp_body += chunk.encode()
                else:
                    resp_body += chunk

            encrypted_body, extra_headers = self._handler.try_encrypt_response(
                session_id, resp_body
            )
            headers = dict(response.headers)
            headers.update(extra_headers)
            return Response(
                content=encrypted_body,
                status_code=response.status_code,
                headers=headers,
                media_type=ENCRYPTED_CONTENT_TYPE if extra_headers else headers.get("content-type"),
            )

        return response
