"""Tests for Shor's algorithm orchestration."""

import pytest

from shorkin.classical.order_finder import find_order
from shorkin.factor import FactorResult, factor


class SimpleClassicalOrderFinder:
    """Simple classical order finder matching the OrderFinder protocol."""

    def find_order(self, x: int, n: int) -> int | None:
        return find_order(x, n)


@pytest.fixture
def classical():
    return SimpleClassicalOrderFinder()


class TestFactor:
    def test_factor_15(self, classical):
        result = factor(15, classical, seed=42)
        assert sorted(result.factors) == [3, 5]
        assert result.n == 15

    def test_factor_21(self, classical):
        result = factor(21, classical, seed=42)
        assert sorted(result.factors) == [3, 7]

    def test_factor_77(self, classical):
        result = factor(77, classical, seed=42)
        assert sorted(result.factors) == [7, 11]

    def test_factor_91(self, classical):
        result = factor(91, classical, seed=42)
        assert sorted(result.factors) == [7, 13]

    def test_factor_even(self, classical):
        result = factor(6, classical)
        assert sorted(result.factors) == [2, 3]

    def test_factor_power_of_two(self, classical):
        result = factor(8, classical)
        assert sorted(result.factors) == [2, 2, 2]

    def test_factor_prime_power(self, classical):
        result = factor(9, classical)
        assert sorted(result.factors) == [3, 3]

    def test_factor_prime_raises(self, classical):
        with pytest.raises(ValueError, match="prime"):
            factor(7, classical)

    def test_factor_small_raises(self, classical):
        with pytest.raises(ValueError, match="must be >= 2"):
            factor(1, classical)

    def test_factor_143(self, classical):
        result = factor(143, classical, seed=42)
        assert sorted(result.factors) == [11, 13]

    def test_factor_large_composite(self, classical):
        # 323 = 17 * 19
        result = factor(323, classical, seed=42)
        assert sorted(result.factors) == [17, 19]

    def test_factor_result_repr(self):
        r = FactorResult(15, [3, 5], "classical")
        assert "15" in repr(r)
        assert "3" in repr(r)
