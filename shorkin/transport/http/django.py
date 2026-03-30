"""Django middleware for QKD-secured communication.

Usage in settings.py:
    MIDDLEWARE = [
        ...
        'shorkin.transport.http.django.QKDMiddleware',
        ...
    ]

    SHORKIN_QKD = {
        'PROTOCOL': 'bb84',
        'NUM_QUBITS': 4096,
        'TARGET_KEY_BITS': 256,
        'STRICT': False,
    }
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    from django.conf import settings
    from django.http import HttpRequest, HttpResponse, JsonResponse
except ImportError as e:
    raise ImportError(
        "Django integration requires the 'django' extra: "
        "pip install shorkin[django]"
    ) from e

from shorkin.transport.http._base import (
    HEADER_ENCRYPTED,
    HEADER_SESSION_ID,
    QKD_INITIATE_PATH,
    QKD_STATUS_PATH,
    QKDHTTPHandler,
)


def _get_config() -> dict[str, Any]:
    """Read QKD configuration from Django settings."""
    return getattr(settings, "SHORKIN_QKD", {})


class QKDMiddleware:
    """Django middleware for QKD-encrypted communication.

    Handles QKD key exchange at well-known endpoints and
    transparently encrypts/decrypts payloads for active sessions.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        config = _get_config()
        self._handler = QKDHTTPHandler(
            protocol=config.get("PROTOCOL", "bb84"),
            strict=config.get("STRICT", False),
            num_qubits=config.get("NUM_QUBITS", 4096),
            target_key_bits=config.get("TARGET_KEY_BITS", 256),
            seed=config.get("SEED"),
        )

    @property
    def handler(self) -> QKDHTTPHandler:
        return self._handler

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path

        # Handle QKD negotiation endpoints
        if path == QKD_INITIATE_PATH and request.method == "POST":
            return self._handle_initiate(request)

        if path == QKD_STATUS_PATH:
            return self._handle_status(request)

        # Check session
        session_id = request.META.get("HTTP_X_QKD_SESSION_ID")

        if self._handler.should_reject(session_id, path):
            return JsonResponse({"error": "QKD session required"}, status=403)

        # Process the request normally
        response = self.get_response(request)

        # Encrypt response if session is active
        if session_id and hasattr(response, "content"):
            encrypted_body, extra_headers = self._handler.try_encrypt_response(
                session_id, response.content
            )
            if extra_headers:
                response.content = encrypted_body
                response["Content-Type"] = "application/octet-stream"
                for key, value in extra_headers.items():
                    response[key] = value

        return response

    def _handle_initiate(self, request: HttpRequest) -> HttpResponse:
        """Handle POST /.well-known/qkd/initiate."""
        loop = asyncio.new_event_loop()
        try:
            status, headers, resp_body = loop.run_until_complete(
                self._handler.handle_initiate(request.body)
            )
        finally:
            loop.close()

        response = HttpResponse(
            content=resp_body,
            status=status,
            content_type="application/json",
        )
        for key, value in headers.items():
            response[key] = value
        return response

    def _handle_status(self, request: HttpRequest) -> HttpResponse:
        """Handle /.well-known/qkd/status."""
        session_id = request.META.get("HTTP_X_QKD_SESSION_ID", "")
        loop = asyncio.new_event_loop()
        try:
            status, headers, resp_body = loop.run_until_complete(
                self._handler.handle_status(session_id)
            )
        finally:
            loop.close()

        response = HttpResponse(
            content=resp_body,
            status=status,
            content_type="application/json",
        )
        for key, value in headers.items():
            response[key] = value
        return response
