"""Tests for the B92 protocol."""

import pytest

from shorkin.qkd.b92 import B92
from shorkin.qkd.channel import SimulatedChannel
from shorkin.qkd.protocol import QKDError


class TestB92:
    def test_generate_key_perfect_channel(self):
        channel = SimulatedChannel(seed=42)
        protocol = B92(seed=42)
        # B92 has ~25% yield, so need more qubits
        result = protocol.generate_key(num_qubits=8000, channel=channel)

        assert result.protocol == "b92"
        assert len(result.final_key) == 32
        assert result.qber == 0.0
        assert result.amplified is True

    def test_name_property(self):
        assert B92().name == "b92"

    def test_lower_yield_than_bb84(self):
        channel = SimulatedChannel(seed=42)
        b92 = B92(seed=42)
        result = b92.generate_key(num_qubits=8000, channel=channel)

        # B92 sifted key length should be roughly 25% of initial
        ratio = result.sifted_key_length / result.initial_qubit_count
        assert ratio < 0.4  # significantly less than BB84's ~50%

    def test_insufficient_qubits_raises(self):
        channel = SimulatedChannel(seed=42)
        protocol = B92(seed=42)

        with pytest.raises(QKDError):
            protocol.generate_key(num_qubits=100, channel=channel)

    def test_custom_target_bits(self):
        channel = SimulatedChannel(seed=42)
        protocol = B92(seed=42)
        result = protocol.generate_key(
            num_qubits=8000, channel=channel, target_key_bits=128
        )
        assert len(result.final_key) == 16
