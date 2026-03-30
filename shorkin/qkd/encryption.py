"""AES-256-GCM encryption using QKD-derived keys."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12  # 96-bit nonce for AES-GCM


def encrypt(
    plaintext: bytes,
    key: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """Encrypt using AES-256-GCM with a QKD-derived key.

    Returns:
        nonce (12 bytes) || ciphertext || tag (16 bytes), concatenated.
    """
    if len(key) not in (16, 24, 32):
        raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce + ciphertext


def decrypt(
    ciphertext_bundle: bytes,
    key: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """Decrypt an AES-256-GCM encrypted payload.

    Expects the format produced by encrypt(): nonce || ciphertext || tag.

    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (tampered data).
    """
    if len(key) not in (16, 24, 32):
        raise ValueError(f"Key must be 16, 24, or 32 bytes, got {len(key)}")

    if len(ciphertext_bundle) < _NONCE_SIZE + 16:
        raise ValueError("Ciphertext too short")

    nonce = ciphertext_bundle[:_NONCE_SIZE]
    ciphertext = ciphertext_bundle[_NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)
