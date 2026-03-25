"""Tests for the classical order finder."""

import pytest

from shorkin.classical.order_finder import find_order


class TestClassicalOrderFinder:
    def test_order_2_mod_15(self):
        # 2^1=2, 2^2=4, 2^3=8, 2^4=1 (mod 15) -> order 4
        assert find_order(2, 15) == 4

    def test_order_7_mod_15(self):
        # 7^1=7, 7^2=4, 7^3=13, 7^4=1 (mod 15) -> order 4
        assert find_order(7, 15) == 4

    def test_order_4_mod_15(self):
        # 4^1=4, 4^2=1 (mod 15) -> order 2
        assert find_order(4, 15) == 2

    def test_order_11_mod_15(self):
        # 11^1=11, 11^2=1 (mod 15) -> order 2
        assert find_order(11, 15) == 2

    def test_order_2_mod_21(self):
        # 2^1=2, 2^2=4, 2^3=8, 2^4=16, 2^5=11, 2^6=1 (mod 21) -> order 6
        assert find_order(2, 21) == 6

    def test_order_with_max_iterations(self):
        # With very small limit, should return None
        assert find_order(2, 15, max_iterations=2) is None

    def test_not_coprime_raises(self):
        with pytest.raises(ValueError, match="not coprime"):
            find_order(3, 15)

    def test_order_1(self):
        # 1^r = 1 for all r, so order is 1
        assert find_order(1, 15) == 1

    def test_larger_modulus(self):
        # 2 mod 77: order should divide lcm(ord_7(2), ord_11(2))
        r = find_order(2, 77)
        assert r is not None
        assert pow(2, r, 77) == 1
