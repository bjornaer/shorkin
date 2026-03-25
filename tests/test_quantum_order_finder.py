"""Tests for the quantum order finder."""

import pytest

from shorkin.quantum.modular_exp import ModularExp
from shorkin.quantum.order_finder import QuantumOrderFinder, qubits_needed


class TestModularExp:
    def test_apply_basic(self):
        # base=2, modulus=15: |1>|e> -> |2^e mod 15>|e>
        gate = ModularExp(target_size=4, exponent_size=11, base=2, modulus=15)
        assert gate.apply(1, 0) == (1, 0)  # 1 * 2^0 mod 15 = 1
        assert gate.apply(1, 1) == (2, 1)  # 1 * 2^1 mod 15 = 2
        assert gate.apply(1, 2) == (4, 2)  # 1 * 2^2 mod 15 = 4
        assert gate.apply(1, 3) == (8, 3)  # 1 * 2^3 mod 15 = 8
        assert gate.apply(1, 4) == (1, 4)  # 1 * 2^4 mod 15 = 1

    def test_apply_target_overflow(self):
        gate = ModularExp(target_size=4, exponent_size=11, base=2, modulus=15)
        # If target >= modulus, should be unchanged
        assert gate.apply(15, 3) == (15, 3)
        assert gate.apply(16, 1) == (16, 1)

    def test_properties(self):
        gate = ModularExp(target_size=4, exponent_size=11, base=7, modulus=15)
        assert gate.base == 7
        assert gate.modulus == 15
        assert gate.target_size == 4
        assert gate.exponent_size == 11

    def test_equality(self):
        g1 = ModularExp(4, 11, 2, 15)
        g2 = ModularExp(4, 11, 2, 15)
        g3 = ModularExp(4, 11, 3, 15)
        assert g1 == g2
        assert g1 != g3
        assert hash(g1) == hash(g2)

    def test_repr(self):
        gate = ModularExp(4, 11, 2, 15)
        r = repr(gate)
        assert "ModularExp" in r
        assert "2" in r
        assert "15" in r


class TestQubitsNeeded:
    def test_n_15(self):
        assert qubits_needed(15) == 3 * 4 + 3  # L=4, 3*4+3=15

    def test_n_21(self):
        assert qubits_needed(21) == 3 * 5 + 3  # L=5, 3*5+3=18

    def test_n_77(self):
        assert qubits_needed(77) == 3 * 7 + 3  # L=7, 3*7+3=24


@pytest.mark.timeout(120)
class TestQuantumOrderFinder:
    def test_find_order_n15(self):
        """Test quantum order finding for N=15 (15 qubits, fast)."""
        qof = QuantumOrderFinder(max_attempts=20)
        # Try several bases known to work
        for x in [2, 7, 4, 11, 13]:
            r = qof.find_order(x, 15)
            if r is not None:
                assert pow(x, r, 15) == 1, f"x={x}: {x}^{r} mod 15 != 1"

    def test_find_order_n15_specific(self):
        """At least one base should succeed for N=15."""
        qof = QuantumOrderFinder(max_attempts=30)
        successes = 0
        for x in [2, 4, 7, 8, 11, 13, 14]:
            r = qof.find_order(x, 15)
            if r is not None and pow(x, r, 15) == 1:
                successes += 1
        assert successes >= 1, "At least one base should find a valid order for N=15"
