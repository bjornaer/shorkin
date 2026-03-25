"""Quantum order finding using phase estimation with Cirq."""

from __future__ import annotations

import cirq
import numpy as np

from shorkin.classical.continued_fractions import phase_to_order
from shorkin.quantum.modular_exp import ModularExp


def _build_order_finding_circuit(
    x: int, n: int, target_qubits: list[cirq.LineQubit], exponent_qubits: list[cirq.LineQubit]
) -> cirq.Circuit:
    """Build the QPE circuit for order finding.

    1. Initialize target register to |1> (set qubit 0)
    2. Hadamard on all exponent qubits
    3. Apply ModularExp gate
    4. Inverse QFT on exponent register
    5. Measure exponent register
    """
    circuit = cirq.Circuit()

    # Initialize target register to |1> (least significant bit)
    circuit.append(cirq.X(target_qubits[0]))

    # Hadamard on exponent register
    circuit.append(cirq.H.on_each(*exponent_qubits))

    # Modular exponentiation
    gate = ModularExp(
        target_size=len(target_qubits),
        exponent_size=len(exponent_qubits),
        base=x,
        modulus=n,
    )
    circuit.append(gate.on(*target_qubits, *exponent_qubits))

    # Inverse QFT on exponent register
    circuit.append(cirq.qft(*exponent_qubits, inverse=True))

    # Measure exponent register
    circuit.append(cirq.measure(*exponent_qubits, key="exponent"))

    return circuit


class QuantumOrderFinder:
    """Find multiplicative order using quantum phase estimation.

    Args:
        max_attempts: Maximum measurement attempts per call to find_order.
        verbose_callback: Optional callback for verbose output.
    """

    method_name = "quantum"

    def __init__(self, max_attempts: int = 20, verbose_callback=None):
        self._max_attempts = max_attempts
        self._verbose_callback = verbose_callback

    def find_order(self, x: int, n: int) -> int | None:
        """Find the order of x modulo n using QPE.

        Returns the order r such that x^r ≡ 1 (mod n), or None if not found.
        """
        L = n.bit_length()
        target_qubits = cirq.LineQubit.range(L)
        exponent_qubits = cirq.LineQubit.range(L, 3 * L + 3)

        circuit = _build_order_finding_circuit(x, n, target_qubits, exponent_qubits)

        if self._verbose_callback:
            self._verbose_callback(f"  Circuit: {len(target_qubits)} target + {len(exponent_qubits)} exponent qubits")
            self._verbose_callback(f"  Circuit diagram:\n{circuit}")

        simulator = cirq.Simulator()
        num_exponent_qubits = len(exponent_qubits)

        for attempt in range(self._max_attempts):
            result = simulator.simulate(circuit)
            # Extract measurement from the final state
            measurement_result = result.final_state_vector

            # Re-run with measurement to get classical outcome
            sampled = simulator.run(circuit, repetitions=1)
            measurement = sampled.measurements["exponent"][0]

            # Convert binary array to integer
            measurement_int = sum(int(bit) << i for i, bit in enumerate(measurement))

            if self._verbose_callback:
                self._verbose_callback(f"  QPE measurement {attempt + 1}: {measurement_int}")

            candidate_r = phase_to_order(measurement_int, num_exponent_qubits, n)
            if candidate_r is None:
                continue

            # Verify the candidate order
            if pow(x, candidate_r, n) == 1:
                if self._verbose_callback:
                    self._verbose_callback(f"  Found order r={candidate_r}")
                return candidate_r

            # Try small multiples of the candidate
            for mult in range(2, 6):
                r = candidate_r * mult
                if r < n and pow(x, r, n) == 1:
                    if self._verbose_callback:
                        self._verbose_callback(f"  Found order r={r} (via {mult}x multiple)")
                    return r

        return None


def qubits_needed(n: int) -> int:
    """Calculate how many qubits are needed to factor n."""
    L = n.bit_length()
    return 3 * L + 3
