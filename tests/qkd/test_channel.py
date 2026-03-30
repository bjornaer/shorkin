"""Tests for the simulated quantum channel."""

import pytest

from shorkin.qkd._types import Basis, BitValue, Qubit
from shorkin.qkd.channel import SimulatedChannel


class TestSimulatedChannel:
    def test_perfect_channel_transmit(self):
        channel = SimulatedChannel(seed=42)
        qubits = [
            Qubit(Basis.RECTILINEAR, BitValue.ZERO),
            Qubit(Basis.RECTILINEAR, BitValue.ONE),
            Qubit(Basis.DIAGONAL, BitValue.ZERO),
            Qubit(Basis.DIAGONAL, BitValue.ONE),
        ]
        result = channel.transmit(qubits)
        assert len(result.received_qubits) == 4
        assert result.detection_efficiency == 1.0
        assert result.error_rate == 0.0
        assert all(q is not None for q in result.received_qubits)

    def test_lossy_channel(self):
        channel = SimulatedChannel(loss_rate=0.5, seed=42)
        qubits = [Qubit(Basis.RECTILINEAR, BitValue.ZERO)] * 1000
        result = channel.transmit(qubits)
        lost = sum(1 for q in result.received_qubits if q is None)
        assert 400 < lost < 600  # ~50% loss

    def test_noisy_channel(self):
        channel = SimulatedChannel(error_rate=0.5, seed=42)
        qubits = [Qubit(Basis.RECTILINEAR, BitValue.ZERO)] * 1000
        result = channel.transmit(qubits)
        flipped = sum(
            1 for q in result.received_qubits
            if q is not None and q.value == BitValue.ONE
        )
        assert 400 < flipped < 600  # ~50% error

    def test_measure_same_basis(self):
        channel = SimulatedChannel(seed=42)
        qubit = Qubit(Basis.RECTILINEAR, BitValue.ONE)
        # Measuring in same basis should give deterministic result
        results = [channel.measure(qubit, Basis.RECTILINEAR) for _ in range(20)]
        assert all(r == 1 for r in results)

    def test_measure_same_basis_zero(self):
        channel = SimulatedChannel(seed=42)
        qubit = Qubit(Basis.RECTILINEAR, BitValue.ZERO)
        results = [channel.measure(qubit, Basis.RECTILINEAR) for _ in range(20)]
        assert all(r == 0 for r in results)

    def test_measure_cross_basis_random(self):
        channel = SimulatedChannel(seed=42)
        qubit = Qubit(Basis.RECTILINEAR, BitValue.ZERO)
        # Measuring |0> in diagonal basis should give ~50/50
        results = [channel.measure(qubit, Basis.DIAGONAL) for _ in range(200)]
        zeros = results.count(0)
        assert 60 < zeros < 140  # roughly 50/50

    def test_generate_entangled_pairs(self):
        channel = SimulatedChannel(seed=42)
        pairs = channel.generate_entangled_pairs(100)
        assert len(pairs) == 100
        # In a perfect channel, all pairs should be correlated
        for pair in pairs:
            assert pair.alice_qubit.value == pair.bob_qubit.value

    def test_entangled_pairs_with_noise(self):
        channel = SimulatedChannel(error_rate=0.3, seed=42)
        pairs = channel.generate_entangled_pairs(1000)
        mismatched = sum(
            1 for p in pairs if p.alice_qubit.value != p.bob_qubit.value
        )
        assert 200 < mismatched < 400  # ~30% error

    def test_invalid_error_rate(self):
        with pytest.raises(ValueError):
            SimulatedChannel(error_rate=1.5)

    def test_invalid_loss_rate(self):
        with pytest.raises(ValueError):
            SimulatedChannel(loss_rate=1.0)
