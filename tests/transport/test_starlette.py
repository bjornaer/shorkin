"""Tests for Starlette QKD middleware."""

import json

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from shorkin.transport.http.starlette import QKDMiddleware


async def hello(request: Request) -> PlainTextResponse:
    return PlainTextResponse("hello world")


def create_app(**middleware_kwargs) -> Starlette:
    app = Starlette(routes=[Route("/hello", hello)])
    app.add_middleware(QKDMiddleware, **middleware_kwargs)
    return app


class TestStarletteMiddleware:
    def test_passthrough_without_session(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)
        resp = client.get("/hello")
        assert resp.status_code == 200
        assert resp.text == "hello world"

    def test_qkd_initiate(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)
        resp = client.post(
            "/.well-known/qkd/initiate",
            json={"protocol": "bb84", "peer_id": "test-client"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["session_id"]
        assert data["key_hash"]

    def test_qkd_initiate_then_encrypted_response(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)

        # Step 1: Initiate key exchange
        init_resp = client.post(
            "/.well-known/qkd/initiate",
            json={"protocol": "bb84", "peer_id": "client1"},
        )
        assert init_resp.status_code == 200
        session_id = init_resp.json()["session_id"]

        # Step 2: Make request with session ID -> response is encrypted
        resp = client.get("/hello", headers={"X-QKD-Session-Id": session_id})
        assert resp.status_code == 200
        # Response should be encrypted (not plaintext)
        assert resp.headers.get("X-QKD-Encrypted") == "true"
        assert resp.content != b"hello world"

    def test_qkd_status_unknown_session(self):
        app = create_app(protocol="bb84", seed=42)
        client = TestClient(app)
        resp = client.get(
            "/.well-known/qkd/status",
            headers={"X-QKD-Session-Id": "nonexistent"},
        )
        assert resp.status_code == 404

    def test_strict_mode_rejects_no_session(self):
        app = create_app(protocol="bb84", seed=42, strict=True)
        client = TestClient(app)
        resp = client.get("/hello")
        assert resp.status_code == 403

    def test_strict_mode_allows_qkd_endpoints(self):
        app = create_app(protocol="bb84", seed=42, strict=True)
        client = TestClient(app)
        resp = client.post(
            "/.well-known/qkd/initiate",
            json={"protocol": "bb84"},
        )
        assert resp.status_code == 200
