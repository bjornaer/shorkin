"""QKD Key Exchange gRPC service implementation.

Usage:
    from shorkin.transport.grpc.servicer import QKDKeyExchangeServicer
    from shorkin.transport.grpc.qkd_pb2_grpc import add_QKDKeyExchangeServicer_to_server

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = QKDKeyExchangeServicer(protocol="bb84")
    add_QKDKeyExchangeServicer_to_server(servicer, server)
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    import grpc
except ImportError as e:
    raise ImportError(
        "gRPC integration requires the 'grpc' extra: "
        "pip install shorkin[grpc]"
    ) from e

from shorkin.transport._key_manager import TransportKeyManager
from shorkin.transport._messages import KeyExchangeInit, SessionStatus
from shorkin.transport.grpc import qkd_pb2, qkd_pb2_grpc


class QKDKeyExchangeServicer(qkd_pb2_grpc.QKDKeyExchangeServicer):
    """gRPC servicer for QKD key exchange.

    Handles the classical channel portion of the QKD protocol
    over gRPC, managing key negotiation and session lifecycle.
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

    def Initiate(self, request, context):
        """Handle QKD key exchange initiation."""
        init = KeyExchangeInit(
            session_id=request.session_id or None,
            protocol=request.protocol or self._key_manager.protocol_name,
            num_qubits=request.num_qubits or 4096,
            target_key_bits=request.target_key_bits or 256,
            peer_id=request.peer_id,
        )

        # If no session_id provided, generate one
        if not init.session_id:
            import uuid
            init.session_id = str(uuid.uuid4())

        try:
            loop = asyncio.new_event_loop()
            try:
                confirm = loop.run_until_complete(
                    self._key_manager.handle_init(init)
                )
            finally:
                loop.close()

            return qkd_pb2.KeyExchangeInitResponse(
                session_id=confirm.session_id,
                key_hash=confirm.key_hash,
                status="ok",
            )
        except Exception as e:
            return qkd_pb2.KeyExchangeInitResponse(
                session_id=init.session_id,
                status="error",
                error_message=str(e),
            )

    def GetStatus(self, request, context):
        """Query session status."""
        status = self._key_manager.get_session_status(request.session_id)
        if status is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Session {request.session_id} not found")
            return qkd_pb2.SessionStatusResponse(
                session_id=request.session_id,
                status="not_found",
            )

        return qkd_pb2.SessionStatusResponse(
            session_id=request.session_id,
            status=status.value,
            protocol=self._key_manager.protocol_name,
        )
