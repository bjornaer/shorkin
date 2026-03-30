"""Tests for AES-GCM encryption."""

import pytest

from shorkin.qkd.encryption import decrypt, encrypt


class TestEncryption:
    def setup_method(self):
        self.key = bytes(range(32))  # 256-bit key

    def test_roundtrip(self):
        plaintext = b"hello quantum world"
        ct = encrypt(plaintext, self.key)
        pt = decrypt(ct, self.key)
        assert pt == plaintext

    def test_roundtrip_with_aad(self):
        plaintext = b"secret data"
        aad = b"session-123"
        ct = encrypt(plaintext, self.key, associated_data=aad)
        pt = decrypt(ct, self.key, associated_data=aad)
        assert pt == plaintext

    def test_wrong_key_fails(self):
        plaintext = b"secret"
        ct = encrypt(plaintext, self.key)
        wrong_key = bytes(range(1, 33))
        with pytest.raises(Exception):  # InvalidTag
            decrypt(ct, wrong_key)

    def test_wrong_aad_fails(self):
        plaintext = b"secret"
        ct = encrypt(plaintext, self.key, associated_data=b"correct")
        with pytest.raises(Exception):
            decrypt(ct, self.key, associated_data=b"wrong")

    def test_tampered_ciphertext_fails(self):
        plaintext = b"secret"
        ct = bytearray(encrypt(plaintext, self.key))
        ct[-1] ^= 0xFF  # flip last byte
        with pytest.raises(Exception):
            decrypt(bytes(ct), self.key)

    def test_different_nonces(self):
        plaintext = b"same plaintext"
        ct1 = encrypt(plaintext, self.key)
        ct2 = encrypt(plaintext, self.key)
        assert ct1 != ct2  # different nonces

    def test_invalid_key_length(self):
        with pytest.raises(ValueError, match="16, 24, or 32"):
            encrypt(b"data", b"short")

    def test_ciphertext_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            decrypt(b"tiny", self.key)

    def test_empty_plaintext(self):
        ct = encrypt(b"", self.key)
        pt = decrypt(ct, self.key)
        assert pt == b""

    def test_16_byte_key(self):
        key = bytes(range(16))
        ct = encrypt(b"data", key)
        pt = decrypt(ct, key)
        assert pt == b"data"
