"""Quantum channel abstraction and simulated implementation."""

from __future__ import annotations

import math
import random
from typing import Protocol, Sequence

import cirq
import numpy as np

from shorkin.qkd._types import Basis, BitValue, ChannelResult, EntangledPair, Qubit


class QuantumChannel(Protocol):
    """Abstraction for the quantum channel between Alice and Bob."""

    def transmit(self, qubits: Sequence[Qubit]) -> ChannelResult: ...

    def measure(self, qubit: Qubit, basis: Basis) -> int | None: ...


class EntangledChannel(QuantumChannel, Protocol):
    """Extended channel that supports entangled pair generation (for E91)."""

    def generate_entangled_pairs(self, count: int) -> list[EntangledPair]: ...

    def measure_entangled(
        self, angle_a: float, angle_b: float
    ) -> tuple[int, int] | None: ...


class SimulatedChannel:
    """Simulated quantum channel using cirq.

    Implements both QuantumChannel and EntangledChannel protocols.
    Supports configurable noise and photon loss.
    """

    def __init__(
        self,
        error_rate: float = 0.0,
        loss_rate: float = 0.0,
        seed: int | None = None,
    ):
        if not 0.0 <= error_rate <= 1.0:
            raise ValueError(f"error_rate must be in [0, 1], got {error_rate}")
        if not 0.0 <= loss_rate < 1.0:
            raise ValueError(f"loss_rate must be in [0, 1), got {loss_rate}")
        self.error_rate = error_rate
        self.loss_rate = loss_rate
        self._rng = random.Random(seed)
        self._np_rng = np.random.RandomState(seed)

    def transmit(self, qubits: Sequence[Qubit]) -> ChannelResult:
        """Transmit qubits, applying loss and noise."""
        received: list[Qubit | None] = []
        lost_count = 0

        for qubit in qubits:
            if self._rng.random() < self.loss_rate:
                received.append(None)
                lost_count += 1
            elif self._rng.random() < self.error_rate:
                # Bit-flip error: flip the value
                flipped_value = (
                    BitValue.ONE if qubit.value == BitValue.ZERO else BitValue.ZERO
                )
                received.append(Qubit(basis=qubit.basis, value=flipped_value))
            else:
                received.append(qubit)

        total = len(qubits)
        detection_eff = (total - lost_count) / total if total > 0 else 0.0
        return ChannelResult(
            received_qubits=received,
            error_rate=self.error_rate,
            detection_efficiency=detection_eff,
        )

    def measure(self, qubit: Qubit, basis: Basis) -> int | None:
        """Measure a qubit in the given basis using cirq simulation.

        Returns 0 or 1 on successful measurement, None if lost.
        """
        if self._rng.random() < self.loss_rate:
            return None

        q = cirq.LineQubit(0)
        circuit = cirq.Circuit()

        # Prepare the qubit state
        if qubit.value == BitValue.ONE:
            circuit.append(cirq.X(q))
        if qubit.basis == Basis.DIAGONAL:
            circuit.append(cirq.H(q))

        # Apply noise (bit-flip with error_rate probability)
        if self.error_rate > 0:
            circuit.append(
                cirq.bit_flip(self.error_rate).on(q)
            )

        # Change to measurement basis if needed
        if basis == Basis.DIAGONAL:
            circuit.append(cirq.H(q))

        circuit.append(cirq.measure(q, key="m"))

        simulator = cirq.DensityMatrixSimulator(seed=self._np_rng)
        sample_result = simulator.run(circuit, repetitions=1)
        return int(sample_result.measurements["m"][0, 0])

    def measure_entangled(
        self, angle_a: float, angle_b: float
    ) -> tuple[int, int] | None:
        """Simulate measurement of an entangled Bell pair |Phi+>.

        For |Phi+> = (|00> + |11>) / sqrt(2):
            P(same outcome) = cos^2(angle_a - angle_b)
            P(different outcome) = sin^2(angle_a - angle_b)

        This directly computes the quantum correlations without
        needing to track individual qubit states.

        Returns:
            (alice_result, bob_result) or None if lost.
        """
        if self._rng.random() < self.loss_rate:
            return None

        p_same = math.cos(angle_a - angle_b) ** 2

        # Apply noise: reduce correlation strength
        if self.error_rate > 0:
            # Noise flips Bob's bit with probability error_rate
            p_same = p_same * (1 - self.error_rate) + (1 - p_same) * self.error_rate

        a_bit = self._rng.randint(0, 1)
        if self._rng.random() < p_same:
            b_bit = a_bit
        else:
            b_bit = 1 - a_bit

        return a_bit, b_bit

    def generate_entangled_pairs(self, count: int) -> list[EntangledPair]:
        """Generate simulated Bell pairs |Phi+> = (|00> + |11>) / sqrt(2).

        For E91, each pair is measured independently by Alice and Bob.
        We simulate the correlations directly.
        """
        pairs: list[EntangledPair] = []
        for _ in range(count):
            if self._rng.random() < self.loss_rate:
                continue

            # In a perfect Bell state, both qubits are correlated in Z-basis
            # Random bit determines the correlated outcome
            bit = BitValue.ZERO if self._rng.random() < 0.5 else BitValue.ONE

            # Apply noise
            alice_bit = bit
            bob_bit = bit
            if self._rng.random() < self.error_rate:
                bob_bit = (
                    BitValue.ONE if bob_bit == BitValue.ZERO else BitValue.ZERO
                )

            alice_qubit = Qubit(basis=Basis.RECTILINEAR, value=alice_bit)
            bob_qubit = Qubit(basis=Basis.RECTILINEAR, value=bob_bit)
            pairs.append(EntangledPair(alice_qubit=alice_qubit, bob_qubit=bob_qubit))

        return pairs
