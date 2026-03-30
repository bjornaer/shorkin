"""Tests for FastAPI QKD middleware and dependency injection."""

import json

import pytest
from fastapi import Depends, FastAPI, Request
from starlette.testclient import TestClient

from shorkin.transport.http.fastapi import QKDMiddleware, QKDSession, qkd_session


def create_app(**middleware_kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(QKDMiddleware, **middleware_kwargs)

    @app.get("/data")
    async def get_data():
        return {"message": "hello"}

    return app


class TestFastAPIMiddleware:
    def test_passthrough(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)
        resp = client.get("/data")
        assert resp.status_code == 200
        assert resp.json() == {"message": "hello"}

    def test_qkd_initiate(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)
        resp = client.post(
            "/.well-known/qkd/initiate",
            json={"protocol": "bb84", "peer_id": "client1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["session_id"]

    def test_encrypted_response(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)

        # Initiate
        init_resp = client.post(
            "/.well-known/qkd/initiate",
            json={"protocol": "bb84", "peer_id": "c1"},
        )
        session_id = init_resp.json()["session_id"]

        # Request with session
        resp = client.get("/data", headers={"X-QKD-Session-Id": session_id})
        assert resp.status_code == 200
        assert resp.headers.get("X-QKD-Encrypted") == "true"


class TestFastAPIDependency:
    def test_qkd_session_dependency(self):
        app = FastAPI()
        dep = qkd_session("bb84", seed=42)

        @app.get("/check")
        async def check(qkd: QKDSession = Depends(dep)):
            return {"active": qkd.is_active, "session_id": qkd.session_id}

        client = TestClient(app)

        # Without session header
        resp = client.get("/check")
        assert resp.json()["active"] is False

        # With session header
        resp = client.get("/check", headers={"X-QKD-Session-Id": "test-session"})
        assert resp.json()["session_id"] == "test-session"
