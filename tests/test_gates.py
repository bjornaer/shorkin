"""Tests for the quantum gates module."""

from __future__ import annotations

import math

import cirq
import numpy as np
import pytest

from shorkin.gates import (
    CCX,
    CNOT,
    CSWAP,
    CZ,
    H,
    S,
    SWAP,
    T,
    X,
    Y,
    Z,
    GateChain,
    cnot,
    cz,
    hadamard,
    pauli_x,
    pauli_y,
    pauli_z,
    phase,
    rotate_x,
    rotate_y,
    rotate_z,
    rx,
    ry,
    rz,
    swap,
    t_gate,
    toffoli,
)


class TestGateAliases:
    def test_h_is_cirq_h(self):
        assert H is cirq.H

    def test_x_is_cirq_x(self):
        assert X is cirq.X

    def test_y_is_cirq_y(self):
        assert Y is cirq.Y

    def test_z_is_cirq_z(self):
        assert Z is cirq.Z

    def test_s_is_cirq_s(self):
        assert S is cirq.S

    def test_t_is_cirq_t(self):
        assert T is cirq.T

    def test_cnot_is_cirq_cnot(self):
        assert CNOT is cirq.CNOT

    def test_cz_is_cirq_cz(self):
        assert CZ is cirq.CZ

    def test_swap_is_cirq_swap(self):
        assert SWAP is cirq.SWAP

    def test_ccx_is_cirq_ccx(self):
        assert CCX is cirq.CCX

    def test_cswap_is_cirq_cswap(self):
        assert CSWAP is cirq.CSWAP


class TestOperationFunctions:
    def test_hadamard(self):
        q = cirq.LineQubit(0)
        op = hadamard(q)
        assert op == cirq.H(q)

    def test_pauli_x(self):
        q = cirq.LineQubit(0)
        op = pauli_x(q)
        assert op == cirq.X(q)

    def test_pauli_y(self):
        q = cirq.LineQubit(0)
        op = pauli_y(q)
        assert op == cirq.Y(q)

    def test_pauli_z(self):
        q = cirq.LineQubit(0)
        op = pauli_z(q)
        assert op == cirq.Z(q)

    def test_phase(self):
        q = cirq.LineQubit(0)
        op = phase(q)
        assert op == cirq.S(q)

    def test_t_gate(self):
        q = cirq.LineQubit(0)
        op = t_gate(q)
        assert op == cirq.T(q)

    def test_cnot(self):
        q0, q1 = cirq.LineQubit.range(2)
        op = cnot(q0, q1)
        assert op == cirq.CNOT(q0, q1)

    def test_cz(self):
        q0, q1 = cirq.LineQubit.range(2)
        op = cz(q0, q1)
        assert op == cirq.CZ(q0, q1)

    def test_toffoli(self):
        q0, q1, q2 = cirq.LineQubit.range(3)
        op = toffoli(q0, q1, q2)
        assert op == cirq.CCX(q0, q1, q2)

    def test_swap(self):
        q0, q1 = cirq.LineQubit.range(2)
        op = swap(q0, q1)
        assert op == cirq.SWAP(q0, q1)

    def test_rotate_x(self):
        q = cirq.LineQubit(0)
        op = rotate_x(q, math.pi)
        assert op == cirq.rx(math.pi)(q)

    def test_rotate_y(self):
        q = cirq.LineQubit(0)
        op = rotate_y(q, math.pi / 2)
        assert op == cirq.ry(math.pi / 2)(q)

    def test_rotate_z(self):
        q = cirq.LineQubit(0)
        op = rotate_z(q, math.pi / 4)
        assert op == cirq.rz(math.pi / 4)(q)


class TestRotationGates:
    def test_rx_returns_gate(self):
        gate = rx(math.pi)
        assert isinstance(gate, cirq.Gate)

    def test_ry_returns_gate(self):
        gate = ry(math.pi)
        assert isinstance(gate, cirq.Gate)

    def test_rz_returns_gate(self):
        gate = rz(math.pi)
        assert isinstance(gate, cirq.Gate)

    def test_rx_pi_equivalent_to_x(self):
        """rx(pi) should be equivalent to X up to global phase."""
        q = cirq.LineQubit(0)
        circuit_rx = cirq.Circuit(cirq.rx(math.pi)(q))
        circuit_x = cirq.Circuit(cirq.X(q))
        sim = cirq.Simulator()
        sv_rx = sim.simulate(circuit_rx).final_state_vector
        sv_x = sim.simulate(circuit_x).final_state_vector
        # Equal up to global phase
        overlap = abs(np.vdot(sv_rx, sv_x))
        assert overlap == pytest.approx(1.0, abs=1e-8)


class TestGateChain:
    def test_empty_chain(self):
        chain = GateChain()
        assert len(chain) == 0
        assert chain.operations == []

    def test_single_operation(self):
        q = cirq.LineQubit(0)
        chain = GateChain().h(q)
        assert len(chain) == 1
        assert chain.operations[0] == cirq.H(q)

    def test_fluent_chaining(self):
        q0, q1 = cirq.LineQubit.range(2)
        chain = GateChain().h(q0).cnot(q0, q1)
        assert len(chain) == 2

    def test_all_single_qubit_gates(self):
        q = cirq.LineQubit(0)
        chain = GateChain().h(q).x(q).y(q).z(q).s(q).t(q)
        assert len(chain) == 6

    def test_rotation_gates(self):
        q = cirq.LineQubit(0)
        chain = GateChain().rx(q, math.pi).ry(q, math.pi / 2).rz(q, math.pi / 4)
        assert len(chain) == 3

    def test_two_qubit_gates(self):
        q0, q1 = cirq.LineQubit.range(2)
        chain = GateChain().cnot(q0, q1).cz(q0, q1).swap(q0, q1)
        assert len(chain) == 3

    def test_toffoli(self):
        q0, q1, q2 = cirq.LineQubit.range(3)
        chain = GateChain().toffoli(q0, q1, q2)
        assert len(chain) == 1
        assert chain.operations[0] == cirq.CCX(q0, q1, q2)

    def test_add_arbitrary_operation(self):
        q = cirq.LineQubit(0)
        chain = GateChain().add(cirq.X(q))
        assert chain.operations[0] == cirq.X(q)

    def test_operations_returns_copy(self):
        q = cirq.LineQubit(0)
        chain = GateChain().h(q)
        ops = chain.operations
        ops.append(cirq.X(q))
        assert len(chain) == 1  # original unchanged

    def test_repr(self):
        q = cirq.LineQubit(0)
        chain = GateChain().h(q).x(q)
        assert repr(chain) == "GateChain(2 operations)"

    def test_repr_empty(self):
        assert repr(GateChain()) == "GateChain(0 operations)"


class TestCircuitIntegration:
    def test_bell_pair_with_functions(self):
        """Build a Bell pair using gate operation functions."""
        q0, q1 = cirq.LineQubit.range(2)
        circuit = cirq.Circuit()
        circuit.append(hadamard(q0))
        circuit.append(cnot(q0, q1))
        circuit.append(cirq.measure(q0, q1, key="result"))

        sim = cirq.Simulator()
        result = sim.run(circuit, repetitions=100)
        measurements = result.measurements["result"]
        # All measurements should be 00 or 11
        for row in measurements:
            assert list(row) in ([0, 0], [1, 1])

    def test_ghz_state_with_chain(self):
        """Build a 3-qubit GHZ state using GateChain."""
        q0, q1, q2 = cirq.LineQubit.range(3)
        chain = GateChain().h(q0).cnot(q0, q1).cnot(q0, q2)
        circuit = cirq.Circuit()
        circuit.append(chain.operations)
        circuit.append(cirq.measure(q0, q1, q2, key="result"))

        sim = cirq.Simulator()
        result = sim.run(circuit, repetitions=100)
        measurements = result.measurements["result"]
        # All measurements should be 000 or 111
        for row in measurements:
            assert list(row) in ([0, 0, 0], [1, 1, 1])

    def test_gate_aliases_in_circuit(self):
        """Use gate aliases directly in a circuit."""
        q = cirq.LineQubit(0)
        circuit = cirq.Circuit([H(q), X(q), cirq.measure(q, key="m")])
        sim = cirq.Simulator()
        # H|0> = |+>, X|+> = |->, measuring |-> gives 0 or 1 with equal prob
        result = sim.run(circuit, repetitions=1)
        assert result.measurements["m"][0, 0] in (0, 1)
