"""Quantum teleportation protocol.

Allows two parties (Alice and Bob) to transfer an arbitrary single-qubit
quantum state using a shared Bell pair and two bits of classical communication.

The protocol uses three qubits:
    - q0 (message): the qubit whose state is to be teleported
    - q1 (alice): Alice's half of the entangled Bell pair
    - q2 (bob): Bob's half of the entangled Bell pair

The circuit uses the deferred measurement principle: quantum-controlled
corrections replace classically-controlled gates, avoiding mid-circuit
measurement issues while producing equivalent results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import cirq
import numpy as np


@dataclass(frozen=True)
class QubitState:
    """Specification of a single-qubit state via Bloch sphere angles.

    The state is: cos(theta/2)|0> + e^(i*phi)*sin(theta/2)|1>

    Args:
        theta: Polar angle in radians [0, pi].
        phi: Azimuthal angle in radians [0, 2*pi).
    """

    theta: float = 0.0
    phi: float = 0.0

    def to_statevector(self) -> np.ndarray:
        """Return the 2-element complex statevector for this state."""
        return np.array([
            np.cos(self.theta / 2),
            np.exp(1j * self.phi) * np.sin(self.theta / 2),
        ], dtype=complex)


class TeleportationResult:
    """Result of a quantum teleportation."""

    def __init__(
        self,
        input_state: QubitState,
        circuit: cirq.Circuit,
        bell_measurement: list[int],
        fidelity: float,
    ):
        self.input_state = input_state
        self.circuit = circuit
        self.bell_measurement = bell_measurement
        self.fidelity = fidelity

    @property
    def success(self) -> bool:
        """True if fidelity is close to 1.0 (teleportation succeeded)."""
        return self.fidelity > 0.99

    @property
    def alice_bits(self) -> tuple[int, int]:
        """The two classical bits from Alice's Bell measurement."""
        return (self.bell_measurement[0], self.bell_measurement[1])

    def __repr__(self) -> str:
        return (
            f"TeleportationResult(input_state={self.input_state}, "
            f"fidelity={self.fidelity:.6f}, "
            f"alice_bits={self.alice_bits})"
        )


def _build_circuit(
    state: QubitState,
    state_prep_circuit: cirq.Circuit | None,
) -> cirq.Circuit:
    """Build the teleportation circuit using the deferred measurement principle.

    Steps:
        1. Prepare the message qubit in the desired state
        2. Create a Bell pair between Alice and Bob
        3. Bell measurement: CNOT(msg, alice), H(msg)
        4. Deferred corrections: CNOT(alice, bob), CZ(msg, bob)
        5. Measure all qubits
    """
    msg, alice, bob = cirq.LineQubit.range(3)
    circuit = cirq.Circuit()

    # 1. Prepare message qubit state
    if state_prep_circuit is not None:
        circuit.append(state_prep_circuit.all_operations())
    else:
        if state.theta != 0.0:
            circuit.append(cirq.ry(state.theta)(msg))
        if state.phi != 0.0:
            circuit.append(cirq.rz(state.phi)(msg))

    # 2. Create Bell pair (alice, bob)
    circuit.append(cirq.H(alice))
    circuit.append(cirq.CNOT(alice, bob))

    # 3. Bell measurement on (msg, alice)
    circuit.append(cirq.CNOT(msg, alice))
    circuit.append(cirq.H(msg))

    # 4. Deferred classical corrections (quantum-controlled equivalents)
    circuit.append(cirq.CNOT(alice, bob))
    circuit.append(cirq.CZ(msg, bob))

    # 5. Measure
    circuit.append(cirq.measure(msg, alice, key="alice"))
    circuit.append(cirq.measure(bob, key="bob"))

    return circuit


def _compute_fidelity(
    target: QubitState,
    full_statevector: np.ndarray,
) -> float:
    """Compute teleportation fidelity from the full 3-qubit statevector.

    After the deferred-measurement teleportation circuit, Bob's qubit is
    guaranteed to be in the target state (disentangled from Alice's qubits).
    We verify this by tracing out Alice's qubits and computing the overlap
    of Bob's reduced state with the target.
    """
    # full_statevector has 8 amplitudes for 3 qubits (msg, alice, bob)
    # Reshape to (msg_dim, alice_dim, bob_dim) = (2, 2, 2)
    psi = full_statevector.reshape(2, 2, 2)

    # Trace out msg and alice to get Bob's reduced density matrix
    # rho_bob = sum_{i,j} |<i,j|psi>|^2 contributions
    rho_bob = np.einsum("ijk,ijl->kl", psi, np.conj(psi))

    # Target statevector
    target_sv = target.to_statevector()

    # Fidelity = <target|rho_bob|target>
    fidelity = float(np.real(target_sv.conj() @ rho_bob @ target_sv))
    return fidelity


def teleport(
    theta: float = 0.0,
    phi: float = 0.0,
    state_prep_circuit: cirq.Circuit | None = None,
    verbose_callback: Callable[[str], None] | None = None,
) -> TeleportationResult:
    """Teleport a single-qubit state from Alice to Bob.

    The state to teleport is specified either by Bloch sphere angles (theta, phi)
    or by a custom state-preparation circuit operating on cirq.LineQubit(0).

    The state is: cos(theta/2)|0> + e^(i*phi)*sin(theta/2)|1>

    Args:
        theta: Polar angle in radians. 0 gives |0>, pi gives |1>, pi/2 gives |+>.
        phi: Azimuthal angle in radians. Controls the relative phase.
        state_prep_circuit: Optional cirq.Circuit that prepares the desired state
            on cirq.LineQubit(0). If provided, theta and phi are ignored.
        verbose_callback: Optional callback(message: str) for verbose output.

    Returns:
        TeleportationResult with fidelity, circuit, and measurement outcomes.
    """
    state = QubitState(theta=theta, phi=phi)

    if verbose_callback:
        if state_prep_circuit is not None:
            verbose_callback("Teleporting state from custom preparation circuit")
        else:
            verbose_callback(
                f"Teleporting state: theta={theta:.4f}, phi={phi:.4f}"
            )

    circuit = _build_circuit(state, state_prep_circuit)

    if verbose_callback:
        verbose_callback(f"Circuit:\n{circuit}")

    simulator = cirq.Simulator()

    # Get statevector for fidelity computation (circuit without measurements)
    ops_no_measure = [
        op for moment in circuit.moments for op in moment.operations
        if not cirq.is_measurement(op)
    ]
    circuit_no_measure = cirq.Circuit(ops_no_measure)
    sim_result = simulator.simulate(circuit_no_measure)
    full_sv = sim_result.final_state_vector

    # Compute fidelity
    if state_prep_circuit is not None:
        # For custom circuits, compute the target state by simulating the prep.
        # An empty circuit means |0>, so we simulate with an explicit qubit.
        if state_prep_circuit.all_qubits():
            prep_result = simulator.simulate(state_prep_circuit)
            prep_sv = prep_result.final_state_vector
        else:
            prep_sv = np.array([1.0, 0.0], dtype=complex)  # |0>
        psi = full_sv.reshape(2, 2, 2)
        rho_bob = np.einsum("ijk,ijl->kl", psi, np.conj(psi))
        fidelity = float(np.real(prep_sv.conj() @ rho_bob @ prep_sv))
    else:
        fidelity = _compute_fidelity(state, full_sv)

    # Run circuit with measurements for the classical bits
    run_result = simulator.run(circuit, repetitions=1)
    alice_bits = [int(b) for b in run_result.measurements["alice"][0]]

    if verbose_callback:
        verbose_callback(f"Alice's measurement: {alice_bits}")
        verbose_callback(f"Fidelity: {fidelity:.6f}")
        verbose_callback(
            f"Teleportation {'succeeded' if fidelity > 0.99 else 'failed'}"
        )

    return TeleportationResult(
        input_state=state,
        circuit=circuit,
        bell_measurement=alice_bits,
        fidelity=fidelity,
    )
