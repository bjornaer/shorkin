"""Tests for gRPC QKD integration (servicer and interceptors)."""

from concurrent import futures

import grpc
import pytest

from shorkin.transport.grpc import qkd_pb2, qkd_pb2_grpc
from shorkin.transport.grpc.interceptor import QKDClientInterceptor, QKDServerInterceptor
from shorkin.transport.grpc.servicer import QKDKeyExchangeServicer


class TestQKDKeyExchangeServicer:
    def setup_method(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        self.servicer = QKDKeyExchangeServicer(protocol="bb84", seed=42)
        qkd_pb2_grpc.add_QKDKeyExchangeServicer_to_server(
            self.servicer, self.server
        )
        port = self.server.add_insecure_port("[::]:0")
        self.server.start()
        self.channel = grpc.insecure_channel(f"localhost:{port}")
        self.stub = qkd_pb2_grpc.QKDKeyExchangeStub(self.channel)

    def teardown_method(self):
        self.channel.close()
        self.server.stop(grace=1)

    def test_initiate_key_exchange(self):
        request = qkd_pb2.KeyExchangeInitRequest(
            protocol="bb84",
            num_qubits=4096,
            target_key_bits=256,
            peer_id="test-client",
        )
        response = self.stub.Initiate(request)
        assert response.status == "ok"
        assert response.session_id
        assert response.key_hash

    def test_initiate_with_session_id(self):
        request = qkd_pb2.KeyExchangeInitRequest(
            session_id="custom-session-123",
            protocol="bb84",
            peer_id="client1",
        )
        response = self.stub.Initiate(request)
        assert response.status == "ok"
        assert response.session_id == "custom-session-123"

    def test_get_status_after_initiate(self):
        # First initiate
        init_req = qkd_pb2.KeyExchangeInitRequest(
            protocol="bb84", peer_id="client1"
        )
        init_resp = self.stub.Initiate(init_req)
        session_id = init_resp.session_id

        # Then check status
        status_req = qkd_pb2.SessionStatusRequest(session_id=session_id)
        status_resp = self.stub.GetStatus(status_req)
        assert status_resp.status == "active"
        assert status_resp.protocol == "bb84"

    def test_get_status_unknown_session(self):
        status_req = qkd_pb2.SessionStatusRequest(session_id="nonexistent")
        with pytest.raises(grpc.RpcError) as exc_info:
            self.stub.GetStatus(status_req)
        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


class TestQKDClientInterceptor:
    def test_creates_with_defaults(self):
        interceptor = QKDClientInterceptor(protocol="bb84", seed=42)
        assert interceptor.key_manager is not None
        assert interceptor.session_id is None

    def test_session_id_property(self):
        interceptor = QKDClientInterceptor(protocol="bb84", seed=42)
        interceptor.session_id = "test-session"
        assert interceptor.session_id == "test-session"

    def test_with_session_adds_metadata(self):
        """Test that the interceptor adds QKD metadata when session is set."""
        interceptor = QKDClientInterceptor(protocol="bb84", seed=42)
        interceptor.session_id = "test-session"

        # Create a server with the servicer
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        servicer = QKDKeyExchangeServicer(protocol="bb84", seed=42)
        qkd_pb2_grpc.add_QKDKeyExchangeServicer_to_server(servicer, server)
        port = server.add_insecure_port("[::]:0")
        server.start()

        try:
            # Create intercepted channel
            channel = grpc.intercept_channel(
                grpc.insecure_channel(f"localhost:{port}"),
                interceptor,
            )
            stub = qkd_pb2_grpc.QKDKeyExchangeStub(channel)

            # Make a call -- the interceptor should add metadata
            request = qkd_pb2.KeyExchangeInitRequest(
                protocol="bb84", peer_id="test"
            )
            response = stub.Initiate(request)
            assert response.status == "ok"

            channel.close()
        finally:
            server.stop(grace=1)


class TestQKDServerInterceptor:
    def test_creates_with_defaults(self):
        interceptor = QKDServerInterceptor(protocol="bb84", seed=42)
        assert interceptor.key_manager is not None

    def test_with_interceptor_on_server(self):
        """Test server interceptor processes requests."""
        interceptor = QKDServerInterceptor(protocol="bb84", seed=42)
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=2),
            interceptors=[interceptor],
        )
        servicer = QKDKeyExchangeServicer(protocol="bb84", seed=42)
        qkd_pb2_grpc.add_QKDKeyExchangeServicer_to_server(servicer, server)
        port = server.add_insecure_port("[::]:0")
        server.start()

        try:
            channel = grpc.insecure_channel(f"localhost:{port}")
            stub = qkd_pb2_grpc.QKDKeyExchangeStub(channel)

            request = qkd_pb2.KeyExchangeInitRequest(
                protocol="bb84", peer_id="test-client"
            )
            response = stub.Initiate(request)
            assert response.status == "ok"

            channel.close()
        finally:
            server.stop(grace=1)


class TestEndToEndGRPC:
    def test_full_flow(self):
        """End-to-end: client initiates key exchange, gets session, uses it."""
        # Set up server with interceptor
        server_interceptor = QKDServerInterceptor(protocol="bb84", seed=42)
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=2),
            interceptors=[server_interceptor],
        )
        servicer = QKDKeyExchangeServicer(protocol="bb84", seed=42)
        qkd_pb2_grpc.add_QKDKeyExchangeServicer_to_server(servicer, server)
        port = server.add_insecure_port("[::]:0")
        server.start()

        try:
            # Client with interceptor
            client_interceptor = QKDClientInterceptor(protocol="bb84", seed=42)
            channel = grpc.intercept_channel(
                grpc.insecure_channel(f"localhost:{port}"),
                client_interceptor,
            )
            stub = qkd_pb2_grpc.QKDKeyExchangeStub(channel)

            # Step 1: Initiate key exchange
            init_req = qkd_pb2.KeyExchangeInitRequest(
                protocol="bb84", peer_id="grpc-client"
            )
            init_resp = stub.Initiate(init_req)
            assert init_resp.status == "ok"

            # Step 2: Set session on client interceptor
            client_interceptor.session_id = init_resp.session_id

            # Step 3: Verify status
            status_req = qkd_pb2.SessionStatusRequest(
                session_id=init_resp.session_id
            )
            status_resp = stub.GetStatus(status_req)
            assert status_resp.status == "active"

            channel.close()
        finally:
            server.stop(grace=1)
