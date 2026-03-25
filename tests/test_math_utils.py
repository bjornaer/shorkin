"""Tests for classical math utilities."""

import random

from shorkin.classical.math_utils import is_prime, is_prime_power, random_coprime


class TestIsPrime:
    def test_small_primes(self):
        for p in [2, 3, 5, 7, 11, 13, 17, 19, 23]:
            assert is_prime(p), f"{p} should be prime"

    def test_small_composites(self):
        for n in [4, 6, 8, 9, 10, 12, 14, 15, 21]:
            assert not is_prime(n), f"{n} should not be prime"

    def test_edge_cases(self):
        assert not is_prime(0)
        assert not is_prime(1)
        assert is_prime(2)

    def test_larger_primes(self):
        assert is_prime(1000003)
        assert is_prime(104729)

    def test_larger_composites(self):
        assert not is_prime(1000004)
        assert not is_prime(15 * 17)


class TestIsPrimePower:
    def test_prime_squares(self):
        ok, base, exp = is_prime_power(4)
        assert ok and base == 2 and exp == 2

        ok, base, exp = is_prime_power(9)
        assert ok and base == 3 and exp == 2

        ok, base, exp = is_prime_power(25)
        assert ok and base == 5 and exp == 2

    def test_prime_cubes(self):
        ok, base, exp = is_prime_power(8)
        assert ok and base == 2 and exp == 3

        ok, base, exp = is_prime_power(27)
        assert ok and base == 3 and exp == 3

    def test_higher_powers(self):
        ok, base, exp = is_prime_power(16)
        assert ok and base == 2
        # Could be (2,4) or (2,4) depending on which is found first
        assert base**exp == 16

        ok, base, exp = is_prime_power(32)
        assert ok and base == 2
        assert base**exp == 32

    def test_not_prime_power(self):
        ok, _, _ = is_prime_power(6)
        assert not ok

        ok, _, _ = is_prime_power(15)
        assert not ok

        ok, _, _ = is_prime_power(1)
        assert not ok

    def test_primes_are_not_prime_powers(self):
        # p^1 is NOT a prime power in our definition (k >= 2)
        ok, _, _ = is_prime_power(7)
        assert not ok


class TestRandomCoprime:
    def test_returns_value_in_range(self):
        rng = random.Random(42)
        for _ in range(100):
            x = random_coprime(15, rng)
            assert 2 <= x <= 14
