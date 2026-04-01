"""Deutsch-Jozsa algorithm for determining if a function is constant or balanced.

Given a function f: {0,1}^n -> {0,1} that is promised to be either constant
(same output for all inputs) or balanced (outputs 0 for exactly half the inputs),
this algorithm determines which case holds with a single quantum query.

Classically, the worst case requires 2^(n-1) + 1 evaluations.
"""

from __future__ import annotations

from typing import Callable

import cirq


class DeutschJozsaResult:
    """Result of the Deutsch-Jozsa algorithm."""

    def __init__(self, function_type: str, n_qubits: int, measurement: list[int]):
        self.function_type = function_type
        self.n_qubits = n_qubits
        self.measurement = measurement

    @property
    def is_constant(self) -> bool:
        """True if the function was determined to be constant."""
        return self.function_type == "constant"

    @property
    def is_balanced(self) -> bool:
        """True if the function was determined to be balanced."""
        return self.function_type == "balanced"

    def __repr__(self) -> str:
        return (
            f"DeutschJozsaResult(function_type='{self.function_type}', "
            f"n_qubits={self.n_qubits}, measurement={self.measurement})"
        )


def _build_oracle(
    f: Callable[[int], int],
    n: int,
    input_qubits: list[cirq.LineQubit],
    ancilla: cirq.LineQubit,
) -> list[cirq.Operation]:
    """Build the oracle U_f: |x>|y> -> |x>|y XOR f(x)> from a classical function.

    For each input x where f(x) = 1, applies a multi-controlled X gate
    on the ancilla conditioned on the input matching x.
    """
    operations: list[cirq.Operation] = []
    for x in range(2**n):
        val = f(x)
        if val not in (0, 1):
            raise ValueError(
                f"f({x}) = {val}, but function must return 0 or 1"
            )
        if val != 1:
            continue

        # Flip input qubits where the corresponding bit of x is 0,
        # so all controls are satisfied when the input is x
        flips = [
            cirq.X(input_qubits[i])
            for i in range(n)
            if not (x >> i) & 1
        ]
        operations.extend(flips)

        # Multi-controlled X on ancilla (all input qubits as controls)
        operations.append(cirq.X(ancilla).controlled_by(*input_qubits))

        # Undo the flips
        operations.extend(flips)

    return operations


def _build_circuit(
    f: Callable[[int], int],
    n: int,
) -> tuple[cirq.Circuit, list[cirq.LineQubit]]:
    """Build the Deutsch-Jozsa circuit.

    Steps:
        1. Initialize ancilla to |1>
        2. Apply Hadamard to all qubits
        3. Apply oracle U_f
        4. Apply Hadamard to input qubits
        5. Measure input qubits
    """
    input_qubits = cirq.LineQubit.range(n)
    ancilla = cirq.LineQubit(n)

    circuit = cirq.Circuit()

    # Initialize ancilla to |1>
    circuit.append(cirq.X(ancilla))

    # Hadamard on all qubits
    circuit.append(cirq.H.on_each(*input_qubits, ancilla))

    # Oracle
    circuit.append(_build_oracle(f, n, input_qubits, ancilla))

    # Hadamard on input qubits
    circuit.append(cirq.H.on_each(*input_qubits))

    # Measure input qubits
    circuit.append(cirq.measure(*input_qubits, key="result"))

    return circuit, input_qubits


def deutsch_jozsa(
    f: Callable[[int], int],
    n: int,
    verbose_callback: Callable[[str], None] | None = None,
) -> DeutschJozsaResult:
    """Determine if a function is constant or balanced using the Deutsch-Jozsa algorithm.

    The function f must map n-bit inputs to {0, 1} and must be either:
    - Constant: f(x) is the same for all x
    - Balanced: f(x) = 0 for exactly half the inputs, and 1 for the rest

    The algorithm determines this with a single quantum query to f, compared
    to the classical worst case of 2^(n-1) + 1 evaluations.

    Args:
        f: A function f: {0,1}^n -> {0,1} promised to be constant or balanced.
        n: The number of input bits (must be >= 1).
        verbose_callback: Optional callback(message: str) for verbose output.

    Returns:
        DeutschJozsaResult indicating whether f is constant or balanced.

    Raises:
        ValueError: If n < 1 or f returns values other than 0 or 1.
    """
    if n < 1:
        raise ValueError(f"Number of input bits must be >= 1, got {n}")

    circuit, input_qubits = _build_circuit(f, n)

    if verbose_callback:
        verbose_callback(
            f"Deutsch-Jozsa circuit for {n}-qubit function ({n + 1} qubits total)"
        )
        verbose_callback(f"Circuit:\n{circuit}")

    simulator = cirq.Simulator()
    result = simulator.run(circuit, repetitions=1)
    measurement = [int(bit) for bit in result.measurements["result"][0]]

    if verbose_callback:
        verbose_callback(f"Measurement: {measurement}")

    all_zero = all(bit == 0 for bit in measurement)
    function_type = "constant" if all_zero else "balanced"

    if verbose_callback:
        verbose_callback(f"Function is {function_type}")

    return DeutschJozsaResult(
        function_type=function_type,
        n_qubits=n,
        measurement=measurement,
    )
