"""Tests for the quantum teleportation protocol."""

from __future__ import annotations

import math

import cirq
import numpy as np
import pytest

from shorkin.teleportation import QubitState, TeleportationResult, teleport


class TestTeleportBasicStates:
    def test_teleport_zero_state(self):
        """Teleport |0> (theta=0, phi=0)."""
        result = teleport(theta=0.0, phi=0.0)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)
        assert result.success

    def test_teleport_one_state(self):
        """Teleport |1> (theta=pi, phi=0)."""
        result = teleport(theta=math.pi, phi=0.0)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)
        assert result.success

    def test_teleport_plus_state(self):
        """Teleport |+> (theta=pi/2, phi=0)."""
        result = teleport(theta=math.pi / 2, phi=0.0)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_teleport_minus_state(self):
        """Teleport |-> (theta=pi/2, phi=pi)."""
        result = teleport(theta=math.pi / 2, phi=math.pi)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_teleport_i_plus_state(self):
        """Teleport |i+> (theta=pi/2, phi=pi/2)."""
        result = teleport(theta=math.pi / 2, phi=math.pi / 2)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)


class TestTeleportArbitraryStates:
    def test_arbitrary_state_1(self):
        result = teleport(theta=math.pi / 3, phi=math.pi / 4)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_arbitrary_state_2(self):
        result = teleport(theta=2 * math.pi / 5, phi=3 * math.pi / 7)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_arbitrary_state_3(self):
        result = teleport(theta=0.7, phi=1.3)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)


class TestTeleportWithCircuit:
    def test_custom_hadamard_prep(self):
        """Teleport H|0> = |+> using a custom prep circuit."""
        q = cirq.LineQubit(0)
        prep = cirq.Circuit(cirq.H(q))
        result = teleport(state_prep_circuit=prep)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_custom_x_prep(self):
        """Teleport X|0> = |1> using a custom prep circuit."""
        q = cirq.LineQubit(0)
        prep = cirq.Circuit(cirq.X(q))
        result = teleport(state_prep_circuit=prep)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_custom_rotation_prep(self):
        """Teleport an arbitrary state using rotation gates."""
        q = cirq.LineQubit(0)
        prep = cirq.Circuit(cirq.ry(math.pi / 3)(q), cirq.rz(math.pi / 5)(q))
        result = teleport(state_prep_circuit=prep)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_circuit_overrides_angles(self):
        """When both circuit and angles are given, circuit takes precedence."""
        q = cirq.LineQubit(0)
        prep = cirq.Circuit(cirq.X(q))  # prepares |1>
        # theta=0 would give |0>, but circuit should override
        result = teleport(theta=0.0, phi=0.0, state_prep_circuit=prep)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_identity_prep_circuit(self):
        """Empty prep circuit teleports |0>."""
        prep = cirq.Circuit()
        result = teleport(state_prep_circuit=prep)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)


class TestFidelity:
    def test_perfect_fidelity_zero(self):
        result = teleport(theta=0.0)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_perfect_fidelity_one(self):
        result = teleport(theta=math.pi)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)

    def test_perfect_fidelity_plus(self):
        result = teleport(theta=math.pi / 2)
        assert result.fidelity == pytest.approx(1.0, abs=1e-6)


class TestQubitState:
    def test_default_is_zero(self):
        state = QubitState()
        sv = state.to_statevector()
        assert abs(sv[0]) == pytest.approx(1.0)
        assert abs(sv[1]) == pytest.approx(0.0)

    def test_one_state(self):
        state = QubitState(theta=math.pi)
        sv = state.to_statevector()
        assert abs(sv[0]) == pytest.approx(0.0, abs=1e-10)
        assert abs(sv[1]) == pytest.approx(1.0)

    def test_plus_state(self):
        state = QubitState(theta=math.pi / 2)
        sv = state.to_statevector()
        expected = 1.0 / math.sqrt(2)
        assert abs(sv[0]) == pytest.approx(expected)
        assert abs(sv[1]) == pytest.approx(expected)

    def test_frozen_dataclass(self):
        state = QubitState(theta=1.0, phi=2.0)
        with pytest.raises(AttributeError):
            state.theta = 0.5  # type: ignore[misc]


class TestTeleportationResult:
    def test_repr(self):
        result = teleport(theta=0.0)
        r = repr(result)
        assert "fidelity" in r
        assert "alice_bits" in r

    def test_alice_bits_are_binary(self):
        result = teleport(theta=math.pi / 3, phi=0.5)
        a, b = result.alice_bits
        assert a in (0, 1)
        assert b in (0, 1)

    def test_success_property(self):
        result = teleport(theta=0.0)
        assert result.success is True


class TestVerboseCallback:
    def test_callback_receives_messages(self):
        messages = []
        teleport(theta=math.pi / 4, verbose_callback=messages.append)
        assert any("Teleporting" in m for m in messages)
        assert any("Fidelity" in m for m in messages)

    def test_callback_custom_circuit(self):
        messages = []
        q = cirq.LineQubit(0)
        prep = cirq.Circuit(cirq.H(q))
        teleport(state_prep_circuit=prep, verbose_callback=messages.append)
        assert any("custom" in m.lower() for m in messages)
