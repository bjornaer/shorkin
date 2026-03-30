"""Tests for privacy amplification."""

import pytest

from shorkin.qkd.privacy_amplification import amplify, bits_to_bytes


class TestBitsToBytes:
    def test_full_byte(self):
        assert bits_to_bytes([1, 0, 1, 0, 1, 0, 1, 0]) == bytes([0b10101010])

    def test_all_zeros(self):
        assert bits_to_bytes([0] * 8) == bytes([0])

    def test_all_ones(self):
        assert bits_to_bytes([1] * 8) == bytes([0xFF])

    def test_partial_byte(self):
        result = bits_to_bytes([1, 1, 0])
        assert result == bytes([0b11000000])

    def test_multiple_bytes(self):
        bits = [1] * 8 + [0] * 8
        result = bits_to_bytes(bits)
        assert result == bytes([0xFF, 0x00])

    def test_empty(self):
        assert bits_to_bytes([]) == b""


class TestAmplify:
    def test_256_bit_key(self):
        raw_bits = [1, 0] * 200  # 400 bits
        result = amplify(raw_bits, target_length_bits=256)
        assert len(result) == 32  # 256 / 8

    def test_128_bit_key(self):
        raw_bits = [0, 1, 1, 0] * 100
        result = amplify(raw_bits, target_length_bits=128)
        assert len(result) == 16

    def test_deterministic(self):
        raw_bits = [1, 0, 1] * 200
        r1 = amplify(raw_bits, target_length_bits=256)
        r2 = amplify(raw_bits, target_length_bits=256)
        assert r1 == r2

    def test_different_input_different_output(self):
        r1 = amplify([0] * 300, target_length_bits=256)
        r2 = amplify([1] * 300, target_length_bits=256)
        assert r1 != r2

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            amplify([0, 1, 0], target_length_bits=256)

    def test_long_key(self):
        raw_bits = [0, 1] * 500
        result = amplify(raw_bits, target_length_bits=512)
        assert len(result) == 64
