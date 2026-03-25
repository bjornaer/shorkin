"""Brute-force classical order finding."""

from math import gcd


def find_order(x: int, n: int, max_iterations: int = 10_000_000) -> int | None:
    """Find the multiplicative order of x modulo n by brute force.

    The order r is the smallest positive integer such that x^r ≡ 1 (mod n).

    Returns the order r, or None if not found within max_iterations.
    """
    if gcd(x, n) != 1:
        raise ValueError(f"x={x} and n={n} are not coprime")

    power = x % n
    for r in range(1, max_iterations + 1):
        if power == 1:
            return r
        power = (power * x) % n

    return None
