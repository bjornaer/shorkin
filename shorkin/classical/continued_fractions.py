"""Convert quantum phase measurements to candidate orders via continued fractions."""

from fractions import Fraction


def phase_to_order(measurement: int, num_qubits: int, n: int) -> int | None:
    """Extract a candidate order from a phase estimation measurement.

    The measurement is an integer from the exponent register. We interpret it
    as a fraction measurement / 2^num_qubits ≈ s/r, then extract r via
    continued fraction expansion.

    Args:
        measurement: Integer measured from the exponent register.
        num_qubits: Number of qubits in the exponent register.
        n: The number being factored (order must be < n).

    Returns:
        Candidate order r, or None if measurement is 0.
    """
    if measurement == 0:
        return None

    phase = Fraction(measurement, 2**num_qubits)
    # Limit denominator to n-1 since the order must be less than n
    frac = phase.limit_denominator(n - 1)

    if frac.denominator == 0:
        return None

    return frac.denominator
