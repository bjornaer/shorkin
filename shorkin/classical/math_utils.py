"""Pure math utilities for Shor's algorithm."""

from math import gcd, isqrt

import sympy


def is_prime(n: int) -> bool:
    """Check if n is prime using sympy's robust implementation."""
    return sympy.isprime(n)


def is_prime_power(n: int) -> tuple[bool, int | None, int | None]:
    """Check if n = p^k for some prime p and k >= 2.

    Returns (True, p, k) if n is a prime power, (False, None, None) otherwise.
    """
    if n < 2:
        return False, None, None

    for k in range(2, n.bit_length() + 1):
        root = isqrt(n) if k == 2 else int(round(n ** (1.0 / k)))
        # Check root and neighbors to handle floating-point imprecision
        for candidate in [root - 1, root, root + 1]:
            if candidate >= 2 and candidate**k == n and is_prime(candidate):
                return True, candidate, k

    return False, None, None


def random_coprime(n: int, rng) -> int:
    """Pick a random x in [2, n-1] that is coprime to n.

    Args:
        n: The modulus.
        rng: A random.Random instance for reproducibility.

    Returns:
        A random integer coprime to n, or an integer whose gcd with n
        reveals a factor (caller should check gcd).
    """
    x = rng.randint(2, n - 1)
    return x
