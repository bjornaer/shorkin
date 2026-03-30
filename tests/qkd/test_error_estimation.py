"""Tests for error estimation and CHSH computation."""

import math
import random

import pytest

from shorkin.qkd.error_estimation import compute_chsh, estimate_qber


class TestEstimateQBER:
    def test_zero_error(self):
        bits = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1] * 10
        qber, alice_rem, bob_rem = estimate_qber(bits, bits, sample_fraction=0.1, seed=42)
        assert qber == 0.0
        assert len(alice_rem) < len(bits)
        assert alice_rem == bob_rem

    def test_full_error(self):
        alice = [0] * 100
        bob = [1] * 100
        qber, _, _ = estimate_qber(alice, bob, sample_fraction=0.5, seed=42)
        assert qber == 1.0

    def test_partial_error(self):
        alice = [0] * 50 + [1] * 50
        bob = [0] * 50 + [0] * 50
        qber, _, _ = estimate_qber(alice, bob, sample_fraction=0.5, seed=42)
        assert 0.3 < qber < 0.7

    def test_sample_bits_removed(self):
        bits = list(range(100))
        qber, alice_rem, bob_rem = estimate_qber(
            bits, bits, sample_fraction=0.2, seed=42
        )
        assert len(alice_rem) == 80
        assert len(bob_rem) == 80

    def test_empty_input(self):
        qber, a, b = estimate_qber([], [], seed=42)
        assert qber == 0.0
        assert a == []
        assert b == []

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError):
            estimate_qber([0, 1], [0], seed=42)


class TestComputeCHSH:
    def test_empty_data(self):
        assert compute_chsh([]) == 0.0

    def test_quantum_correlations_violate_bell(self):
        """Simulate quantum correlations using the E91 angles.

        Alice: a1=0, a2=pi/8, a3=pi/4
        Bob:   b1=pi/8, b2=pi/4, b3=3*pi/8

        For |Phi+>, P(same) = cos^2(angle_a - angle_b).
        CHSH uses non-matching pairs: (a1,b1), (a1,b3), (a3,b1), (a3,b3).
        """
        alice_angles = [0.0, math.pi / 8, math.pi / 4]
        bob_angles = [math.pi / 8, math.pi / 4, 3 * math.pi / 8]

        # Matching pairs that go to key (excluded from bell test)
        matching = {(1, 0), (2, 1)}

        rng = random.Random(42)
        data: list[tuple[int, int, int, int]] = []

        for _ in range(50000):
            a_idx = rng.randint(0, 2)
            b_idx = rng.randint(0, 2)
            if (a_idx, b_idx) in matching:
                continue

            angle_diff = alice_angles[a_idx] - bob_angles[b_idx]
            p_same = math.cos(angle_diff) ** 2
            a_bit = rng.randint(0, 1)
            b_bit = a_bit if rng.random() < p_same else 1 - a_bit
            data.append((a_idx, b_idx, a_bit, b_bit))

        s = compute_chsh(data)
        # Should be close to 2*sqrt(2) ~ 2.828
        assert s > 2.5

    def test_uncorrelated_below_bound(self):
        """Completely random measurements should not violate Bell inequality."""
        rng = random.Random(42)
        data = [
            (rng.choice([0, 2]), rng.choice([0, 2]), rng.randint(0, 1), rng.randint(0, 1))
            for _ in range(10000)
        ]
        s = compute_chsh(data)
        assert s < 2.1
