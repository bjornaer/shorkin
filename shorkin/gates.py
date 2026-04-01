"""Convenience quantum gate abstractions wrapping cirq gates.

Provides gate aliases, operation constructor functions, rotation gate
constructors, and a fluent GateChain builder for composing sequences
of gate operations.

Usage::

    from shorkin.gates import H, CNOT, hadamard, cnot, rotate_x, GateChain

    # Gate aliases (cirq gate objects)
    circuit.append(H(q0))
    circuit.append(CNOT(q0, q1))

    # Operation functions
    circuit.append(hadamard(q0))
    circuit.append(cnot(q0, q1))
    circuit.append(rotate_x(q0, math.pi / 2))

    # Fluent chaining
    chain = GateChain().h(q0).cnot(q0, q1).rz(q1, math.pi / 4)
    circuit.append(chain.operations)
"""

from __future__ import annotations

import cirq

# ---------------------------------------------------------------------------
# Gate aliases (cirq gate objects — use as H(qubit), CNOT(q0, q1), etc.)
# ---------------------------------------------------------------------------

H = cirq.H
X = cirq.X
Y = cirq.Y
Z = cirq.Z
S = cirq.S
T = cirq.T
CNOT = cirq.CNOT
CZ = cirq.CZ
SWAP = cirq.SWAP
CCX = cirq.CCX  # Toffoli
CSWAP = cirq.CSWAP  # Fredkin


# ---------------------------------------------------------------------------
# Rotation gate constructors (return cirq.Gate objects)
# ---------------------------------------------------------------------------

def rx(rads: float) -> cirq.Gate:
    """X-rotation gate by the given angle in radians."""
    return cirq.rx(rads)


def ry(rads: float) -> cirq.Gate:
    """Y-rotation gate by the given angle in radians."""
    return cirq.ry(rads)


def rz(rads: float) -> cirq.Gate:
    """Z-rotation gate by the given angle in radians."""
    return cirq.rz(rads)


# ---------------------------------------------------------------------------
# Operation functions (return cirq.Operation objects ready for circuit.append)
# ---------------------------------------------------------------------------

def hadamard(qubit: cirq.Qid) -> cirq.Operation:
    """Apply Hadamard gate to a qubit."""
    return cirq.H(qubit)


def pauli_x(qubit: cirq.Qid) -> cirq.Operation:
    """Apply Pauli-X (NOT) gate to a qubit."""
    return cirq.X(qubit)


def pauli_y(qubit: cirq.Qid) -> cirq.Operation:
    """Apply Pauli-Y gate to a qubit."""
    return cirq.Y(qubit)


def pauli_z(qubit: cirq.Qid) -> cirq.Operation:
    """Apply Pauli-Z gate to a qubit."""
    return cirq.Z(qubit)


def phase(qubit: cirq.Qid) -> cirq.Operation:
    """Apply S (phase) gate to a qubit."""
    return cirq.S(qubit)


def t_gate(qubit: cirq.Qid) -> cirq.Operation:
    """Apply T (pi/8) gate to a qubit."""
    return cirq.T(qubit)


def cnot(control: cirq.Qid, target: cirq.Qid) -> cirq.Operation:
    """Apply CNOT (controlled-X) gate."""
    return cirq.CNOT(control, target)


def cz(q1: cirq.Qid, q2: cirq.Qid) -> cirq.Operation:
    """Apply CZ (controlled-Z) gate."""
    return cirq.CZ(q1, q2)


def toffoli(c1: cirq.Qid, c2: cirq.Qid, target: cirq.Qid) -> cirq.Operation:
    """Apply Toffoli (CCX / doubly-controlled X) gate."""
    return cirq.CCX(c1, c2, target)


def swap(q1: cirq.Qid, q2: cirq.Qid) -> cirq.Operation:
    """Apply SWAP gate."""
    return cirq.SWAP(q1, q2)


def rotate_x(qubit: cirq.Qid, rads: float) -> cirq.Operation:
    """Apply X-rotation to a qubit."""
    return cirq.rx(rads)(qubit)


def rotate_y(qubit: cirq.Qid, rads: float) -> cirq.Operation:
    """Apply Y-rotation to a qubit."""
    return cirq.ry(rads)(qubit)


def rotate_z(qubit: cirq.Qid, rads: float) -> cirq.Operation:
    """Apply Z-rotation to a qubit."""
    return cirq.rz(rads)(qubit)


# ---------------------------------------------------------------------------
# GateChain — fluent builder for composing gate sequences
# ---------------------------------------------------------------------------

class GateChain:
    """Compose a sequence of gate operations for reuse.

    Example::

        q0, q1 = cirq.LineQubit.range(2)
        chain = GateChain().h(q0).cnot(q0, q1).rz(q1, math.pi / 4)
        circuit = cirq.Circuit()
        circuit.append(chain.operations)
    """

    def __init__(self) -> None:
        self._operations: list[cirq.Operation] = []

    @property
    def operations(self) -> list[cirq.Operation]:
        """Return a copy of the accumulated operations."""
        return list(self._operations)

    def add(self, operation: cirq.Operation) -> GateChain:
        """Add an arbitrary cirq.Operation."""
        self._operations.append(operation)
        return self

    # Single-qubit gates

    def h(self, qubit: cirq.Qid) -> GateChain:
        """Append Hadamard gate."""
        self._operations.append(cirq.H(qubit))
        return self

    def x(self, qubit: cirq.Qid) -> GateChain:
        """Append Pauli-X gate."""
        self._operations.append(cirq.X(qubit))
        return self

    def y(self, qubit: cirq.Qid) -> GateChain:
        """Append Pauli-Y gate."""
        self._operations.append(cirq.Y(qubit))
        return self

    def z(self, qubit: cirq.Qid) -> GateChain:
        """Append Pauli-Z gate."""
        self._operations.append(cirq.Z(qubit))
        return self

    def s(self, qubit: cirq.Qid) -> GateChain:
        """Append S (phase) gate."""
        self._operations.append(cirq.S(qubit))
        return self

    def t(self, qubit: cirq.Qid) -> GateChain:
        """Append T (pi/8) gate."""
        self._operations.append(cirq.T(qubit))
        return self

    # Rotation gates

    def rx(self, qubit: cirq.Qid, rads: float) -> GateChain:
        """Append X-rotation gate."""
        self._operations.append(cirq.rx(rads)(qubit))
        return self

    def ry(self, qubit: cirq.Qid, rads: float) -> GateChain:
        """Append Y-rotation gate."""
        self._operations.append(cirq.ry(rads)(qubit))
        return self

    def rz(self, qubit: cirq.Qid, rads: float) -> GateChain:
        """Append Z-rotation gate."""
        self._operations.append(cirq.rz(rads)(qubit))
        return self

    # Two-qubit gates

    def cnot(self, control: cirq.Qid, target: cirq.Qid) -> GateChain:
        """Append CNOT (controlled-X) gate."""
        self._operations.append(cirq.CNOT(control, target))
        return self

    def cz(self, q1: cirq.Qid, q2: cirq.Qid) -> GateChain:
        """Append CZ (controlled-Z) gate."""
        self._operations.append(cirq.CZ(q1, q2))
        return self

    def swap(self, q1: cirq.Qid, q2: cirq.Qid) -> GateChain:
        """Append SWAP gate."""
        self._operations.append(cirq.SWAP(q1, q2))
        return self

    # Three-qubit gates

    def toffoli(self, c1: cirq.Qid, c2: cirq.Qid, target: cirq.Qid) -> GateChain:
        """Append Toffoli (CCX) gate."""
        self._operations.append(cirq.CCX(c1, c2, target))
        return self

    def __len__(self) -> int:
        return len(self._operations)

    def __repr__(self) -> str:
        return f"GateChain({len(self._operations)} operations)"
