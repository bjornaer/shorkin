"""Tests for the BB84 protocol."""

import pytest

from shorkin.qkd.bb84 import BB84
from shorkin.qkd.channel import SimulatedChannel
from shorkin.qkd.protocol import QKDError


class TestBB84:
    def test_generate_key_perfect_channel(self):
        channel = SimulatedChannel(seed=42)
        protocol = BB84(seed=42)
        result = protocol.generate_key(num_qubits=4000, channel=channel)

        assert result.protocol == "bb84"
        assert len(result.final_key) == 32  # 256 bits
        assert result.qber == 0.0
        assert result.amplified is True
        assert result.initial_qubit_count == 4000
        assert result.sifted_key_length > 0

    def test_generate_key_with_noise(self):
        channel = SimulatedChannel(error_rate=0.05, seed=42)
        protocol = BB84(seed=42)
        result = protocol.generate_key(num_qubits=8000, channel=channel)

        assert result.protocol == "bb84"
        assert len(result.final_key) == 32
        assert result.qber < 0.11  # below threshold

    def test_high_noise_raises(self):
        channel = SimulatedChannel(error_rate=0.2, seed=42)
        protocol = BB84(seed=42)

        with pytest.raises(QKDError, match="QBER.*exceeds threshold"):
            protocol.generate_key(num_qubits=8000, channel=channel)

    def test_insufficient_qubits_raises(self):
        channel = SimulatedChannel(seed=42)
        protocol = BB84(seed=42)

        with pytest.raises(QKDError):
            protocol.generate_key(num_qubits=100, channel=channel)

    def test_name_property(self):
        assert BB84().name == "bb84"

    def test_custom_target_key_bits(self):
        channel = SimulatedChannel(seed=42)
        protocol = BB84(seed=42)
        result = protocol.generate_key(
            num_qubits=4000, channel=channel, target_key_bits=128
        )
        assert len(result.final_key) == 16  # 128 bits

    def test_deterministic_with_seed(self):
        channel1 = SimulatedChannel(seed=100)
        protocol1 = BB84(seed=100)
        r1 = protocol1.generate_key(num_qubits=4000, channel=channel1)

        channel2 = SimulatedChannel(seed=100)
        protocol2 = BB84(seed=100)
        r2 = protocol2.generate_key(num_qubits=4000, channel=channel2)

        assert r1.final_key == r2.final_key
        assert r1.qber == r2.qber
