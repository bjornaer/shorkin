"""Tests for the Deutsch-Jozsa algorithm."""

import pytest

from shorkin.deutsch_jozsa import DeutschJozsaResult, deutsch_jozsa


class TestConstantFunctions:
    """Constant functions should always be identified as constant."""

    def test_constant_zero_3bit(self):
        result = deutsch_jozsa(lambda x: 0, n=3)
        assert result.is_constant
        assert result.measurement == [0, 0, 0]

    def test_constant_one_3bit(self):
        result = deutsch_jozsa(lambda x: 1, n=3)
        assert result.is_constant
        assert result.measurement == [0, 0, 0]

    def test_constant_zero_1bit(self):
        result = deutsch_jozsa(lambda x: 0, n=1)
        assert result.is_constant

    def test_constant_one_1bit(self):
        result = deutsch_jozsa(lambda x: 1, n=1)
        assert result.is_constant

    def test_constant_zero_2bit(self):
        result = deutsch_jozsa(lambda x: 0, n=2)
        assert result.is_constant

    def test_constant_4bit(self):
        result = deutsch_jozsa(lambda x: 0, n=4)
        assert result.is_constant


class TestBalancedFunctions:
    """Balanced functions should always be identified as balanced."""

    def test_parity(self):
        """f(x) = XOR of all bits."""
        result = deutsch_jozsa(lambda x: bin(x).count("1") % 2, n=3)
        assert result.is_balanced

    def test_msb(self):
        """f(x) = most significant bit."""
        result = deutsch_jozsa(lambda x: (x >> 2) & 1, n=3)
        assert result.is_balanced

    def test_lsb(self):
        """f(x) = least significant bit."""
        result = deutsch_jozsa(lambda x: x & 1, n=3)
        assert result.is_balanced

    def test_identity_1bit(self):
        """n=1, f(x) = x."""
        result = deutsch_jozsa(lambda x: x, n=1)
        assert result.is_balanced

    def test_negation_1bit(self):
        """n=1, f(x) = NOT x."""
        result = deutsch_jozsa(lambda x: 1 - x, n=1)
        assert result.is_balanced

    def test_custom_balanced_2bit(self):
        """n=2, custom balanced: f(0)=0, f(1)=1, f(2)=1, f(3)=0."""
        table = {0: 0, 1: 1, 2: 1, 3: 0}
        result = deutsch_jozsa(lambda x: table[x], n=2)
        assert result.is_balanced

    def test_parity_4bit(self):
        """n=4, parity function."""
        result = deutsch_jozsa(lambda x: bin(x).count("1") % 2, n=4)
        assert result.is_balanced

    def test_half_split_4bit(self):
        """n=4, f(x) = 1 if x < 8, else 0."""
        result = deutsch_jozsa(lambda x: 1 if x < 8 else 0, n=4)
        assert result.is_balanced


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_invalid_n_zero(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            deutsch_jozsa(lambda x: 0, n=0)

    def test_invalid_n_negative(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            deutsch_jozsa(lambda x: 0, n=-1)

    def test_invalid_function_output(self):
        with pytest.raises(ValueError, match="must return 0 or 1"):
            deutsch_jozsa(lambda x: 2, n=1)

    def test_invalid_function_output_negative(self):
        with pytest.raises(ValueError, match="must return 0 or 1"):
            deutsch_jozsa(lambda x: -1, n=1)


class TestDeutschJozsaResult:
    """Tests for the result class."""

    def test_repr(self):
        result = DeutschJozsaResult("constant", 3, [0, 0, 0])
        assert "constant" in repr(result)
        assert "3" in repr(result)

    def test_is_constant(self):
        result = DeutschJozsaResult("constant", 2, [0, 0])
        assert result.is_constant
        assert not result.is_balanced

    def test_is_balanced(self):
        result = DeutschJozsaResult("balanced", 2, [1, 0])
        assert result.is_balanced
        assert not result.is_constant

    def test_n_qubits(self):
        result = deutsch_jozsa(lambda x: 0, n=3)
        assert result.n_qubits == 3


class TestVerboseCallback:
    """Tests for verbose output."""

    def test_callback_receives_messages(self):
        messages = []
        deutsch_jozsa(lambda x: 0, n=2, verbose_callback=messages.append)
        assert any("Deutsch-Jozsa" in m for m in messages)
        assert any("constant" in m for m in messages)

    def test_callback_balanced(self):
        messages = []
        deutsch_jozsa(lambda x: x & 1, n=2, verbose_callback=messages.append)
        assert any("balanced" in m for m in messages)
