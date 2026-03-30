"""Tests for sifting algorithms."""

from shorkin.qkd._types import Basis
from shorkin.qkd.sifting import sift_b92, sift_bb84, sift_e91


class TestBB84Sifting:
    def test_all_matching(self):
        bases = [Basis.RECTILINEAR, Basis.DIAGONAL, Basis.RECTILINEAR]
        bits = [0, 1, 1]
        alice_s, bob_s = sift_bb84(bases, bases, bits, bits)
        assert alice_s == [0, 1, 1]
        assert bob_s == [0, 1, 1]

    def test_no_matching(self):
        alice_bases = [Basis.RECTILINEAR, Basis.RECTILINEAR]
        bob_bases = [Basis.DIAGONAL, Basis.DIAGONAL]
        alice_s, bob_s = sift_bb84(alice_bases, bob_bases, [0, 1], [1, 0])
        assert alice_s == []
        assert bob_s == []

    def test_partial_matching(self):
        alice_bases = [Basis.RECTILINEAR, Basis.DIAGONAL, Basis.RECTILINEAR]
        bob_bases = [Basis.RECTILINEAR, Basis.RECTILINEAR, Basis.RECTILINEAR]
        alice_bits = [1, 0, 1]
        bob_bits = [1, 1, 0]
        alice_s, bob_s = sift_bb84(alice_bases, bob_bases, alice_bits, bob_bits)
        assert alice_s == [1, 1]  # indices 0 and 2 match
        assert bob_s == [1, 0]

    def test_empty_input(self):
        alice_s, bob_s = sift_bb84([], [], [], [])
        assert alice_s == []
        assert bob_s == []


class TestB92Sifting:
    def test_conclusive_only(self):
        conclusive = [True, False, True, False, True]
        alice_bits = [0, 1, 1, 0, 0]
        bob_bits = [0, 0, 1, 0, 0]
        alice_s, bob_s = sift_b92(conclusive, alice_bits, bob_bits)
        assert alice_s == [0, 1, 0]
        assert bob_s == [0, 1, 0]

    def test_none_conclusive(self):
        conclusive = [False, False, False]
        alice_s, bob_s = sift_b92(conclusive, [0, 1, 0], [1, 0, 1])
        assert alice_s == []
        assert bob_s == []


class TestE91Sifting:
    def test_same_index_matching_default(self):
        """Default: same index = match (backward compatible)."""
        alice_bases = [0, 1, 1, 2, 0]
        bob_bases = [0, 1, 2, 2, 1]
        alice_bits = [0, 1, 0, 1, 0]
        bob_bits = [0, 1, 1, 1, 1]

        alice_key, bob_key, bell_data = sift_e91(
            alice_bases, bob_bases, alice_bits, bob_bits
        )
        # Matching bases: indices 0 (0,0), 1 (1,1), 3 (2,2)
        assert alice_key == [0, 1, 1]
        assert bob_key == [0, 1, 1]
        assert len(bell_data) == 2

    def test_custom_matching_pairs(self):
        """E91 uses angle-based matching: (1,0) and (2,1)."""
        alice_bases = [0, 1, 1, 2, 0, 2]
        bob_bases = [0, 0, 2, 1, 1, 0]
        alice_bits = [0, 1, 0, 1, 0, 1]
        bob_bits = [0, 1, 1, 1, 1, 0]

        matching = {(1, 0), (2, 1)}
        alice_key, bob_key, bell_data = sift_e91(
            alice_bases, bob_bases, alice_bits, bob_bits,
            matching_pairs=matching,
        )
        # Matches: index 1 (a=1,b=0), index 3 (a=2,b=1)
        assert alice_key == [1, 1]
        assert bob_key == [1, 1]
        # Bell data: indices 0,2,4,5
        assert len(bell_data) == 4
