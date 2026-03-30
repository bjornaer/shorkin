"""Tests for the E91 protocol."""

import pytest

from shorkin.qkd.channel import SimulatedChannel
from shorkin.qkd.e91 import E91
from shorkin.qkd.protocol import QKDError


class TestE91:
    def test_generate_key_perfect_channel(self):
        channel = SimulatedChannel(seed=42)
        protocol = E91(seed=42)
        # E91 matching probability is 2/9 (~22%), need many qubits
        result = protocol.generate_key(num_qubits=20000, channel=channel)

        assert result.protocol == "e91"
        assert len(result.final_key) == 32
        assert result.amplified is True
        assert result.qber < 0.05  # near-zero on perfect channel

    def test_name_property(self):
        assert E91().name == "e91"

    def test_no_pairs_raises(self):
        channel = SimulatedChannel(loss_rate=0.99, seed=42)
        protocol = E91(seed=42, bell_threshold=0.0)
        with pytest.raises(QKDError):
            protocol.generate_key(num_qubits=10, channel=channel)

    def test_custom_target_bits(self):
        channel = SimulatedChannel(seed=42)
        protocol = E91(seed=42)
        result = protocol.generate_key(
            num_qubits=20000, channel=channel, target_key_bits=128
        )
        assert len(result.final_key) == 16

    def test_chsh_in_metadata(self):
        channel = SimulatedChannel(seed=42)
        protocol = E91(seed=42)
        result = protocol.generate_key(num_qubits=20000, channel=channel)
        assert "chsh_value" in result.metadata
        assert result.metadata["chsh_value"] > 2.0  # Bell violation

    def test_chsh_violation_detected(self):
        """With a perfect channel, CHSH should exceed 2.0."""
        channel = SimulatedChannel(seed=123)
        protocol = E91(seed=123, bell_threshold=2.0)
        result = protocol.generate_key(num_qubits=20000, channel=channel)
        assert result.metadata["chsh_value"] > 2.0
