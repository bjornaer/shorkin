"""Grover's algorithm for unstructured database search.

Given a function f: {0,1}^n -> {0,1} that marks one or more "winner" items
(f(x) = 1), Grover's algorithm finds a marked item with high probability
using O(sqrt(N)) oracle queries, where N = 2^n.

Classically, the best possible approach requires O(N) queries.
"""

from __future__ import annotations

import math
from typing import Callable

import cirq


class GroverResult:
    """Result of Grover's search algorithm."""

    def __init__(
        self,
        found_items: list[int],
        n_qubits: int,
        iterations: int,
        measurement: list[int],
        num_marked: int,
    ):
        self.found_items = found_items
        self.n_qubits = n_qubits
        self.iterations = iterations
        self.measurement = measurement
        self.num_marked = num_marked

    @property
    def found(self) -> int | None:
        """The first found item, or None if no items were found."""
        return self.found_items[0] if self.found_items else None

    @property
    def search_space_size(self) -> int:
        """Total size of the search space (2^n)."""
        return 2**self.n_qubits

    def __repr__(self) -> str:
        return (
            f"GroverResult(found_items={self.found_items}, "
            f"n_qubits={self.n_qubits}, iterations={self.iterations}, "
            f"num_marked={self.num_marked})"
        )


def _optimal_iterations(n: int, num_marked: int) -> int:
    """Compute the optimal number of Grover iterations.

    Returns floor(pi/4 * sqrt(N/M)) where N = 2^n and M = num_marked.
    """
    N = 2**n
    if num_marked >= N:
        return 0
    return max(1, math.floor(math.pi / 4 * math.sqrt(N / num_marked)))


def _build_oracle(
    f: Callable[[int], int],
    n: int,
    qubits: list[cirq.LineQubit],
) -> list[cirq.Operation]:
    """Build a phase-kickback oracle that flips the phase of marked states.

    For each x where f(x) = 1, applies a phase of -1 to |x>.
    Uses the pattern: X-flip zero bits, multi-controlled Z, X-unflip.
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

        # Flip qubits where the corresponding bit of x is 0
        flips = [
            cirq.X(qubits[i])
            for i in range(n)
            if not (x >> i) & 1
        ]
        operations.extend(flips)

        # Multi-controlled Z (phase flip)
        if n == 1:
            operations.append(cirq.Z(qubits[0]))
        else:
            operations.append(cirq.Z(qubits[-1]).controlled_by(*qubits[:-1]))

        # Undo flips
        operations.extend(flips)

    return operations


def _build_diffuser(qubits: list[cirq.LineQubit]) -> list[cirq.Operation]:
    """Build the Grover diffusion operator (2|s><s| - I).

    Implemented as: H^n, X^n, multi-controlled Z, X^n, H^n.
    """
    n = len(qubits)
    operations: list[cirq.Operation] = []

    # H on all qubits
    operations.extend(cirq.H(q) for q in qubits)

    # X on all qubits
    operations.extend(cirq.X(q) for q in qubits)

    # Multi-controlled Z
    if n == 1:
        operations.append(cirq.Z(qubits[0]))
    else:
        operations.append(cirq.Z(qubits[-1]).controlled_by(*qubits[:-1]))

    # X on all qubits
    operations.extend(cirq.X(q) for q in qubits)

    # H on all qubits
    operations.extend(cirq.H(q) for q in qubits)

    return operations


def _build_circuit(
    f: Callable[[int], int],
    n: int,
    iterations: int,
) -> tuple[cirq.Circuit, list[cirq.LineQubit]]:
    """Build the complete Grover circuit.

    Steps:
        1. Apply Hadamard to all qubits (uniform superposition)
        2. Repeat for `iterations` rounds:
           a. Apply oracle (phase flip on marked states)
           b. Apply diffuser (amplitude amplification)
        3. Measure all qubits
    """
    qubits = cirq.LineQubit.range(n)
    circuit = cirq.Circuit()

    # Uniform superposition
    circuit.append(cirq.H.on_each(*qubits))

    # Grover iterations
    oracle_ops = _build_oracle(f, n, qubits)
    diffuser_ops = _build_diffuser(qubits)
    for _ in range(iterations):
        circuit.append(oracle_ops)
        circuit.append(diffuser_ops)

    # Measure
    circuit.append(cirq.measure(*qubits, key="result"))

    return circuit, qubits


def grover(
    f: Callable[[int], int],
    n: int,
    num_marked: int = 1,
    iterations: int | None = None,
    repetitions: int = 1,
    seed: int | None = None,
    verbose_callback: Callable[[str], None] | None = None,
) -> GroverResult:
    """Search for marked items using Grover's algorithm.

    The function f must map n-bit inputs to {0, 1}, where f(x) = 1 marks
    the "winner" items to search for.

    Args:
        f: Oracle function f: {0,1}^n -> {0,1}. Returns 1 for marked items.
        n: Number of input bits (search space size is 2^n).
        num_marked: Number of marked items (used for optimal iteration count).
        iterations: Number of Grover iterations. If None, uses the optimal
            count: floor(pi/4 * sqrt(2^n / num_marked)).
        repetitions: Number of times to run the circuit.
        seed: Random seed for the simulator (enables reproducible results).
        verbose_callback: Optional callback(message: str) for verbose output.

    Returns:
        GroverResult with the found items and algorithm metadata.

    Raises:
        ValueError: If n < 1 or f returns values other than 0 or 1.
    """
    if n < 1:
        raise ValueError(f"Number of input bits must be >= 1, got {n}")

    if iterations is None:
        iterations = _optimal_iterations(n, num_marked)

    if verbose_callback:
        verbose_callback(
            f"Grover search: {n} qubits, 2^{n}={2**n} items, "
            f"{num_marked} marked, {iterations} iterations"
        )

    circuit, qubits = _build_circuit(f, n, iterations)

    if verbose_callback:
        verbose_callback(f"Circuit:\n{circuit}")

    simulator = cirq.Simulator(seed=seed)
    result = simulator.run(circuit, repetitions=repetitions)
    measurements = result.measurements["result"]

    found_items = []
    last_measurement = []
    for row in measurements:
        bits = [int(b) for b in row]
        last_measurement = bits
        value = sum(bit << i for i, bit in enumerate(bits))
        found_items.append(value)

    if verbose_callback:
        verbose_callback(f"Found items: {found_items}")

    return GroverResult(
        found_items=found_items,
        n_qubits=n,
        iterations=iterations,
        measurement=last_measurement,
        num_marked=num_marked,
    )
