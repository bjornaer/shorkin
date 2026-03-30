"""Tests for the key store."""

import time

from shorkin.qkd.key_store import KeyStore

import pytest


class TestKeyStore:
    def test_store_and_get(self):
        store = KeyStore()
        store.store("s1", b"key1", "bb84")
        assert store.get("s1") == b"key1"

    def test_get_nonexistent(self):
        store = KeyStore()
        assert store.get("nope") is None

    def test_get_protocol(self):
        store = KeyStore()
        store.store("s1", b"key1", "e91")
        assert store.get_protocol("s1") == "e91"

    def test_rotate(self):
        store = KeyStore()
        store.store("s1", b"old_key", "bb84")
        store.rotate("s1", b"new_key")
        assert store.get("s1") == b"new_key"

    def test_rotate_nonexistent_raises(self):
        store = KeyStore()
        with pytest.raises(KeyError):
            store.rotate("nope", b"key")

    def test_remove(self):
        store = KeyStore()
        store.store("s1", b"key", "bb84")
        store.remove("s1")
        assert store.get("s1") is None

    def test_max_uses_expiration(self):
        store = KeyStore(max_uses=3)
        store.store("s1", b"key", "bb84")
        store.get("s1")  # use 1
        store.get("s1")  # use 2
        store.get("s1")  # use 3 -> now expired
        assert store.get("s1") is None

    def test_time_expiration(self):
        store = KeyStore(max_age_seconds=0.05)
        store.store("s1", b"key", "bb84")
        assert store.get("s1") == b"key"
        time.sleep(0.06)
        assert store.is_expired("s1")

    def test_active_sessions(self):
        store = KeyStore()
        store.store("s1", b"k1", "bb84")
        store.store("s2", b"k2", "e91")
        sessions = store.active_sessions()
        assert set(sessions) == {"s1", "s2"}

    def test_cleanup_expired(self):
        store = KeyStore(max_age_seconds=0.01)
        store.store("s1", b"k1", "bb84")
        time.sleep(0.02)
        removed = store.cleanup_expired()
        assert removed == 1
        assert store.active_sessions() == []
