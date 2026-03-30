"""Basis reconciliation / sifting for QKD protocols."""

from __future__ import annotations

from typing import Sequence

from shorkin.qkd._types import Basis


def sift_bb84(
    alice_bases: Sequence[Basis],
    bob_bases: Sequence[Basis],
    alice_bits: Sequence[int],
    bob_bits: Sequence[int],
) -> tuple[list[int], list[int]]:
    """BB84 sifting: keep bits where bases match.

    Returns:
        (alice_sifted, bob_sifted) -- matching-basis bit lists.
    """
    alice_sifted: list[int] = []
    bob_sifted: list[int] = []

    for a_basis, b_basis, a_bit, b_bit in zip(
        alice_bases, bob_bases, alice_bits, bob_bits
    ):
        if a_basis == b_basis:
            alice_sifted.append(a_bit)
            bob_sifted.append(b_bit)

    return alice_sifted, bob_sifted


def sift_b92(
    bob_conclusive: Sequence[bool],
    alice_bits: Sequence[int],
    bob_bits: Sequence[int],
) -> tuple[list[int], list[int]]:
    """B92 sifting: keep bits where Bob had a conclusive measurement.

    In B92, Bob announces which positions gave conclusive results,
    but not which basis he used. Alice keeps her corresponding bits.

    Returns:
        (alice_sifted, bob_sifted) -- conclusive bit lists.
    """
    alice_sifted: list[int] = []
    bob_sifted: list[int] = []

    for conclusive, a_bit, b_bit in zip(bob_conclusive, alice_bits, bob_bits):
        if conclusive:
            alice_sifted.append(a_bit)
            bob_sifted.append(b_bit)

    return alice_sifted, bob_sifted


def sift_e91(
    alice_bases: Sequence[int],
    bob_bases: Sequence[int],
    alice_bits: Sequence[int],
    bob_bits: Sequence[int],
    matching_pairs: set[tuple[int, int]] | None = None,
) -> tuple[list[int], list[int], list[tuple[int, int, int, int]]]:
    """E91 sifting: separate key bits from Bell test data.

    Key bits come from measurement pairs where Alice and Bob used
    the same angle. Non-matching angle pairs contribute to the
    CHSH Bell inequality test.

    Args:
        alice_bases: Alice's basis choice indices (0, 1, or 2).
        bob_bases: Bob's basis choice indices (0, 1, or 2).
        alice_bits: Alice's measurement results.
        bob_bits: Bob's measurement results.
        matching_pairs: Set of (alice_index, bob_index) pairs that
            correspond to the same measurement angle. If None,
            defaults to same-index matching.

    Returns:
        (alice_key_bits, bob_key_bits, bell_test_data)
        where bell_test_data entries are (alice_basis, bob_basis, alice_bit, bob_bit).
    """
    alice_key: list[int] = []
    bob_key: list[int] = []
    bell_data: list[tuple[int, int, int, int]] = []

    for a_basis, b_basis, a_bit, b_bit in zip(
        alice_bases, bob_bases, alice_bits, bob_bits
    ):
        if matching_pairs is not None:
            is_match = (a_basis, b_basis) in matching_pairs
        else:
            is_match = a_basis == b_basis

        if is_match:
            alice_key.append(a_bit)
            bob_key.append(b_bit)
        else:
            bell_data.append((a_basis, b_basis, a_bit, b_bit))

    return alice_key, bob_key, bell_data
