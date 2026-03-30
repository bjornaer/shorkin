"""QBER estimation and Bell inequality computation."""

from __future__ import annotations

import random
from typing import Sequence


def estimate_qber(
    alice_bits: Sequence[int],
    bob_bits: Sequence[int],
    sample_fraction: float = 0.1,
    seed: int | None = None,
) -> tuple[float, list[int], list[int]]:
    """Estimate QBER by comparing a random sample of sifted bits.

    The sampled bits are discarded (they've been revealed publicly).

    Args:
        alice_bits: Alice's sifted key bits.
        bob_bits: Bob's sifted key bits.
        sample_fraction: Fraction of bits to sample for estimation.
        seed: Random seed for reproducibility.

    Returns:
        (qber, remaining_alice_bits, remaining_bob_bits)
    """
    if len(alice_bits) != len(bob_bits):
        raise ValueError("Bit sequences must have equal length")

    n = len(alice_bits)
    if n == 0:
        return 0.0, [], []

    sample_size = max(1, int(n * sample_fraction))
    rng = random.Random(seed)
    sample_indices = set(rng.sample(range(n), min(sample_size, n)))

    errors = 0
    for i in sample_indices:
        if alice_bits[i] != bob_bits[i]:
            errors += 1

    qber = errors / len(sample_indices) if sample_indices else 0.0

    remaining_alice = [b for i, b in enumerate(alice_bits) if i not in sample_indices]
    remaining_bob = [b for i, b in enumerate(bob_bits) if i not in sample_indices]

    return qber, remaining_alice, remaining_bob


def compute_chsh(
    bell_test_data: Sequence[tuple[int, int, int, int]],
) -> float:
    """Compute the CHSH inequality value from E91 Bell test measurements.

    The CHSH value S is computed as:
        S = |E(a1,b1) - E(a1,b3) + E(a3,b1) + E(a3,b3)|

    where E(a,b) is the correlation function for basis choices a and b.
    Basis indices refer to:
        Alice: a1=0 (angle 0), a2=1 (pi/8), a3=2 (pi/4)
        Bob:   b1=0 (pi/8), b2=1 (pi/4), b3=2 (3pi/8)

    Matching pairs (a2,b1) and (a3,b2) go to key, not Bell test.
    The CHSH test uses the remaining non-matching pairs.

    Args:
        bell_test_data: List of (alice_basis, bob_basis, alice_bit, bob_bit).

    Returns:
        The CHSH S value. |S| > 2 indicates entanglement.
        Maximum quantum value is 2*sqrt(2) ~ 2.828.
    """
    if not bell_test_data:
        return 0.0

    # Group measurements by basis pair
    correlations: dict[tuple[int, int], list[float]] = {}
    for a_basis, b_basis, a_bit, b_bit in bell_test_data:
        key = (a_basis, b_basis)
        # Convert 0/1 to +1/-1
        a_val = 1 - 2 * a_bit
        b_val = 1 - 2 * b_bit
        correlations.setdefault(key, []).append(a_val * b_val)

    def E(a: int, b: int) -> float:
        vals = correlations.get((a, b), [])
        return sum(vals) / len(vals) if vals else 0.0

    # CHSH: S = E(a1,b1) - E(a1,b3) + E(a3,b1) + E(a3,b3)
    # a1=0, a3=2, b1=0, b3=2
    s = E(0, 0) - E(0, 2) + E(2, 0) + E(2, 2)
    return abs(s)
