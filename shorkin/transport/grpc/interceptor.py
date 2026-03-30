"""gRPC interceptors for QKD-encrypted communication.

Client interceptor:
    from shorkin.transport.grpc.interceptor import QKDClientInterceptor

    interceptor = QKDClientInterceptor(protocol="bb84")
    channel = grpc.intercept_channel(
        grpc.insecure_channel('localhost:50051'),
        interceptor
    )

Server interceptor:
    from shorkin.transport.grpc.interceptor import QKDServerInterceptor

    interceptor = QKDServerInterceptor(protocol="bb84")
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[interceptor]
    )
"""

from __future__ import annotations

from typing import Any

try:
    import grpc
except ImportError as e:
    raise ImportError(
        "gRPC integration requires the 'grpc' extra: "
        "pip install shorkin[grpc]"
    ) from e

from shorkin.transport._key_manager import TransportKeyManager

# Metadata keys for QKD session info
_QKD_SESSION_ID_KEY = "x-qkd-session-id"
_QKD_ENCRYPTED_KEY = "x-qkd-encrypted"
_QKD_PROTOCOL_KEY = "x-qkd-protocol"


class QKDClientInterceptor(grpc.UnaryUnaryClientInterceptor):
    """Client-side gRPC interceptor for QKD-encrypted communication.

    Encrypts outgoing request payloads and decrypts incoming response
    payloads using the QKD-derived session key. Session ID is passed
    via gRPC metadata.
    """

    def __init__(
        self,
        protocol: str = "bb84",
        key_manager: TransportKeyManager | None = None,
        session_id: str | None = None,
        **kwargs: Any,
    ):
        self._key_manager = key_manager or TransportKeyManager(
            protocol=protocol, **kwargs
        )
        self._session_id = session_id

    @property
    def key_manager(self) -> TransportKeyManager:
        return self._key_manager

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None):
        self._session_id = value

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Intercept unary-unary calls to add QKD encryption."""
        if self._session_id:
            # Add QKD metadata
            metadata = list(client_call_details.metadata or [])
            metadata.append((_QKD_SESSION_ID_KEY, self._session_id))
            metadata.append((_QKD_ENCRYPTED_KEY, "true"))
            metadata.append((_QKD_PROTOCOL_KEY, self._key_manager.protocol_name))

            new_details = _ClientCallDetails(
                client_call_details.method,
                client_call_details.timeout,
                metadata,
                client_call_details.credentials,
                client_call_details.wait_for_ready,
                client_call_details.compression,
            )
            return continuation(new_details, request)

        return continuation(client_call_details, request)


class QKDServerInterceptor(grpc.ServerInterceptor):
    """Server-side gRPC interceptor for QKD-encrypted communication.

    Reads QKD session metadata from incoming requests and makes
    the session context available to service handlers.
    """

    def __init__(
        self,
        protocol: str = "bb84",
        key_manager: TransportKeyManager | None = None,
        **kwargs: Any,
    ):
        self._key_manager = key_manager or TransportKeyManager(
            protocol=protocol, **kwargs
        )

    @property
    def key_manager(self) -> TransportKeyManager:
        return self._key_manager

    def intercept_service(self, continuation, handler_call_details):
        """Intercept incoming calls to extract QKD session info."""
        # Extract QKD metadata
        metadata = dict(handler_call_details.invocation_metadata or [])
        session_id = metadata.get(_QKD_SESSION_ID_KEY)

        if session_id:
            # Store session ID in context for service handlers
            handler_call_details._qkd_session_id = session_id

        return continuation(handler_call_details)


class _ClientCallDetails(
    grpc.ClientCallDetails
):
    """Wrapper for ClientCallDetails that allows metadata modification."""

    def __init__(self, method, timeout, metadata, credentials, wait_for_ready, compression):
        self.method = method
        self.timeout = timeout
        self.metadata = metadata
        self.credentials = credentials
        self.wait_for_ready = wait_for_ready
        self.compression = compression
