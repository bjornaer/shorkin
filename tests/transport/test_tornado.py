"""Tests for Tornado QKD integration."""

import json

import pytest
import tornado.testing
import tornado.web

from shorkin.transport.http._base import QKDHTTPHandler
from shorkin.transport.http.tornado import (
    QKDInitiateHandler,
    QKDRequestMixin,
    QKDStatusHandler,
    qkd_routes,
)


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(b"hello tornado")


class SecureHandler(QKDRequestMixin, tornado.web.RequestHandler):
    def get(self):
        self.write(b"secure data")


class TestTornadoIntegration(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        handler = QKDHTTPHandler(protocol="bb84", seed=42)
        routes = [
            (r"/hello", HelloHandler),
            (r"/secure", SecureHandler, {"qkd_protocol": "bb84"}),
        ] + qkd_routes("bb84", seed=42)
        return tornado.web.Application(routes)

    def test_hello_passthrough(self):
        resp = self.fetch("/hello")
        assert resp.code == 200
        assert resp.body == b"hello tornado"

    def test_qkd_initiate(self):
        body = json.dumps({"protocol": "bb84", "peer_id": "client1"}).encode()
        resp = self.fetch(
            "/.well-known/qkd/initiate",
            method="POST",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.code == 200
        data = json.loads(resp.body)
        assert data["status"] == "ok"
        assert data["session_id"]

    def test_qkd_status_unknown(self):
        resp = self.fetch(
            "/.well-known/qkd/status",
            headers={"X-QKD-Session-Id": "nonexistent"},
        )
        assert resp.code == 404


class TestQKDRoutes:
    def test_creates_routes(self):
        routes = qkd_routes("bb84")
        assert len(routes) == 2
        paths = [r[0] for r in routes]
        assert "/.well-known/qkd/initiate" in paths
        assert "/.well-known/qkd/status" in paths
