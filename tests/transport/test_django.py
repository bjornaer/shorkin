"""Tests for Django QKD middleware."""

import json
import os

import django
from django.conf import settings

# Configure Django settings before importing anything else
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={},
        ROOT_URLCONF=__name__,
        MIDDLEWARE=[
            "shorkin.transport.http.django.QKDMiddleware",
        ],
        SHORKIN_QKD={
            "PROTOCOL": "bb84",
            "SEED": 42,
        },
        SECRET_KEY="test-secret-key",
    )
    django.setup()

from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory
from django.urls import path

from shorkin.transport.http.django import QKDMiddleware


# Simple view for testing
def hello_view(request):
    return HttpResponse(b"hello django", content_type="text/plain")


# URL configuration
urlpatterns = [
    path("hello", hello_view),
]


class TestDjangoMiddleware:
    def setup_method(self):
        self.factory = RequestFactory()
        self.middleware = QKDMiddleware(get_response=hello_view)

    def test_passthrough(self):
        request = self.factory.get("/hello")
        response = self.middleware(request)
        assert response.status_code == 200
        assert response.content == b"hello django"

    def test_qkd_initiate(self):
        body = json.dumps({"protocol": "bb84", "peer_id": "client1"}).encode()
        request = self.factory.post(
            "/.well-known/qkd/initiate",
            data=body,
            content_type="application/json",
        )
        response = self.middleware._handle_initiate(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert data["session_id"]

    def test_encrypted_response(self):
        # First initiate
        body = json.dumps({"protocol": "bb84", "peer_id": "c1"}).encode()
        init_request = self.factory.post(
            "/.well-known/qkd/initiate",
            data=body,
            content_type="application/json",
        )
        init_response = self.middleware._handle_initiate(init_request)
        session_id = json.loads(init_response.content)["session_id"]

        # Then request with session
        request = self.factory.get(
            "/hello",
            HTTP_X_QKD_SESSION_ID=session_id,
        )
        response = self.middleware(request)
        assert response.status_code == 200
        # Response should be encrypted
        assert response["X-QKD-Encrypted"] == "true"
        assert response.content != b"hello django"

    def test_handler_property(self):
        assert self.middleware.handler is not None
