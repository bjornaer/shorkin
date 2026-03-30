"""Privacy amplification using universal hashing."""

from __future__ import annotations

import hashlib
from typing import Sequence


def bits_to_bytes(bits: Sequence[int]) -> bytes:
    """Convert a sequence of bits (0/1) to bytes."""
    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for j in range(min(8, len(bits) - i)):
            byte_val |= bits[i + j] << (7 - j)
        byte_array.append(byte_val)
    return bytes(byte_array)


def amplify(
    raw_key_bits: Sequence[int],
    target_length_bits: int = 256,
) -> bytes:
    """Apply privacy amplification to distill a shorter, secure key.

    Uses SHA-256-based extraction. For longer keys, chains multiple
    hash outputs using HKDF-like expansion.

    Args:
        raw_key_bits: The sifted key bits after error estimation.
        target_length_bits: Desired final key length in bits.

    Returns:
        The amplified key as bytes.

    Raises:
        ValueError: If raw key is too short for the target length.
    """
    if len(raw_key_bits) < target_length_bits:
        raise ValueError(
            f"Raw key ({len(raw_key_bits)} bits) too short for "
            f"target ({target_length_bits} bits)"
        )

    raw_bytes = bits_to_bytes(raw_key_bits)
    target_bytes = (target_length_bits + 7) // 8

    if target_bytes <= 32:
        # Single SHA-256 hash suffices
        h = hashlib.sha256(raw_bytes).digest()
        return h[:target_bytes]

    # HKDF-like expansion for longer keys
    result = b""
    counter = 1
    while len(result) < target_bytes:
        h = hashlib.sha256(raw_bytes + counter.to_bytes(4, "big")).digest()
        result += h
        counter += 1

    return result[:target_bytes]
