"""Shor's algorithm orchestration."""

from __future__ import annotations

import random
from math import gcd
from typing import TYPE_CHECKING, Protocol

from shorkin.classical.math_utils import is_prime, is_prime_power

if TYPE_CHECKING:
    pass


class OrderFinder(Protocol):
    """Protocol for order-finding implementations."""

    def find_order(self, x: int, n: int) -> int | None: ...


class FactorResult:
    """Result of a factoring attempt."""

    def __init__(self, n: int, factors: list[int], method: str):
        self.n = n
        self.factors = sorted(factors)
        self.method = method

    def __repr__(self) -> str:
        return f"FactorResult(n={self.n}, factors={self.factors}, method={self.method})"


def _try_shor_step(
    x: int,
    n: int,
    order_finder: OrderFinder,
) -> int | None:
    """Try one iteration of Shor's algorithm with base x.

    Returns a non-trivial factor of n, or None if this attempt failed.
    """
    r = order_finder.find_order(x, n)
    if r is None:
        return None

    # Order must be even
    if r % 2 != 0:
        return None

    # Check x^(r/2) ≢ -1 (mod n)
    half_power = pow(x, r // 2, n)
    if half_power == n - 1:
        return None

    # At least one of these should be a non-trivial factor
    for candidate in [gcd(half_power - 1, n), gcd(half_power + 1, n)]:
        if 1 < candidate < n:
            return candidate

    return None


def factor(
    n: int,
    order_finder: OrderFinder,
    max_attempts: int = 30,
    seed: int | None = None,
    verbose_callback=None,
) -> FactorResult:
    """Factor n using Shor's algorithm.

    Args:
        n: The composite integer to factor.
        order_finder: An OrderFinder implementation (quantum or classical).
        max_attempts: Maximum random bases to try.
        seed: Random seed for reproducibility.
        verbose_callback: Optional callback(message: str) for verbose output.

    Returns:
        FactorResult with the prime factorization.

    Raises:
        ValueError: If n < 2, n is prime, or factoring fails.
    """
    if n < 2:
        raise ValueError(f"Cannot factor {n}: must be >= 2")

    method = getattr(order_finder, "method_name", "classical")
    if not method:
        mod = type(order_finder).__module__
        method = "quantum" if "quantum" in mod else "classical"

    if is_prime(n):
        raise ValueError(f"{n} is prime")

    # Check even
    if n % 2 == 0:
        other = n // 2
        return FactorResult(n, _full_factorize(2, other), method)

    # Check prime power
    is_pp, base, exp = is_prime_power(n)
    if is_pp:
        return FactorResult(n, [base] * exp, method)

    rng = random.Random(seed)

    for attempt in range(1, max_attempts + 1):
        x = rng.randint(2, n - 1)

        if verbose_callback:
            verbose_callback(f"Attempt {attempt}: trying base x={x}")

        # Lucky factor from gcd
        g = gcd(x, n)
        if g > 1:
            if verbose_callback:
                verbose_callback(f"  Lucky: gcd({x}, {n}) = {g}")
            return FactorResult(n, _full_factorize(g, n // g), method)

        p = _try_shor_step(x, n, order_finder)
        if p is not None:
            q = n // p
            if verbose_callback:
                verbose_callback(f"  Found factor: {p}")
            return FactorResult(n, _full_factorize(p, q), method)

        if verbose_callback:
            verbose_callback(f"  Attempt {attempt} failed, retrying...")

    raise ValueError(f"Failed to factor {n} after {max_attempts} attempts")


def _full_factorize(*parts: int) -> list[int]:
    """Recursively factorize all parts into primes."""
    result = []
    for part in parts:
        if part <= 1:
            continue
        if is_prime(part):
            result.append(part)
        elif part % 2 == 0:
            while part % 2 == 0:
                result.append(2)
                part //= 2
            if part > 1:
                result.extend(_full_factorize(part))
        else:
            is_pp, base, exp = is_prime_power(part)
            if is_pp:
                result.extend([base] * exp)
            else:
                # For remaining composites, trial division as fallback
                result.extend(_trial_division(part))
    return sorted(result)


def _trial_division(n: int) -> list[int]:
    """Simple trial division for remaining composite factors."""
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors
