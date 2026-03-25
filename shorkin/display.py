"""Terminal output formatting for shorkin."""

from __future__ import annotations

import sys
from collections import Counter


def format_factors(n: int, factors: list[int]) -> str:
    """Format a factorization result as 'n = p1 x p2 x ...'."""
    factor_str = " x ".join(str(f) for f in sorted(factors))
    return f"{n} = {factor_str}"


def format_factors_with_exponents(n: int, factors: list[int]) -> str:
    """Format as 'n = p1^e1 x p2^e2 x ...'."""
    counts = Counter(factors)
    parts = []
    for prime in sorted(counts):
        exp = counts[prime]
        if exp == 1:
            parts.append(str(prime))
        else:
            parts.append(f"{prime}^{exp}")
    return f"{n} = {' x '.join(parts)}"


def print_result(n: int, factors: list[int], method: str, quiet: bool = False) -> None:
    """Print the factoring result to stdout."""
    if quiet:
        print(" ".join(str(f) for f in sorted(factors)))
        return

    print(format_factors(n, factors))
    if len(set(factors)) < len(factors):
        print(format_factors_with_exponents(n, factors))
    print(f"Method: {method}")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def print_info(message: str) -> None:
    """Print an informational message to stderr."""
    print(message, file=sys.stderr)
