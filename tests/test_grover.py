"""Tests for Grover's search algorithm."""

from __future__ import annotations

import math

import pytest

from shorkin.grover import GroverResult, _optimal_iterations, grover


class TestSingleMarkedItem:
    def test_find_marked_item_3bit(self):
        """Search for item 5 in a space of 8."""
        target = 5
        result = grover(lambda x: int(x == target), n=3, seed=42)
        assert target in result.found_items

    def test_find_marked_item_2bit(self):
        """Search for item 2 in a space of 4."""
        target = 2
        result = grover(lambda x: int(x == target), n=2, seed=42)
        assert target in result.found_items

    def test_find_marked_item_4bit(self):
        """Search for item 10 in a space of 16."""
        target = 10
        result = grover(lambda x: int(x == target), n=4, seed=42)
        assert target in result.found_items

    def test_find_item_0(self):
        """Search for item 0."""
        result = grover(lambda x: int(x == 0), n=3, seed=42)
        assert 0 in result.found_items

    def test_find_item_max(self):
        """Search for the largest item in the space."""
        result = grover(lambda x: int(x == 7), n=3, seed=42)
        assert 7 in result.found_items


class TestMultipleMarkedItems:
    def test_find_one_of_two_marked(self):
        """Mark items 3 and 5 in a space of 8."""
        marked = {3, 5}
        result = grover(lambda x: int(x in marked), n=3, num_marked=2, seed=42)
        assert result.found in marked

    def test_find_one_of_four_marked_4bit(self):
        """Mark 4 items in a space of 16."""
        marked = {1, 5, 9, 13}
        result = grover(lambda x: int(x in marked), n=4, num_marked=4, seed=42)
        assert result.found in marked

    def test_multiple_repetitions(self):
        """Run multiple repetitions and check all find a marked item."""
        target = 3
        result = grover(lambda x: int(x == target), n=3, repetitions=5, seed=42)
        assert len(result.found_items) == 5
        # At least most should find the target (high probability)
        assert result.found_items.count(target) >= 3


class TestOptimalIterations:
    def test_single_marked(self):
        """For 1 marked in 2^3=8, optimal ~ floor(pi/4 * sqrt(8)) = 2."""
        iters = _optimal_iterations(3, 1)
        assert iters == math.floor(math.pi / 4 * math.sqrt(8))

    def test_two_marked(self):
        """For 2 marked in 2^3=8, optimal ~ floor(pi/4 * sqrt(4)) = 1."""
        iters = _optimal_iterations(3, 2)
        assert iters == max(1, math.floor(math.pi / 4 * math.sqrt(4)))

    def test_single_marked_4bit(self):
        """For 1 marked in 2^4=16, optimal ~ floor(pi/4 * sqrt(16)) = 3."""
        iters = _optimal_iterations(4, 1)
        assert iters == math.floor(math.pi / 4 * math.sqrt(16))

    def test_all_marked_returns_zero(self):
        """If all items are marked, zero iterations needed."""
        iters = _optimal_iterations(3, 8)
        assert iters == 0

    def test_manual_iterations_override(self):
        """Manual iteration count should override automatic."""
        result = grover(lambda x: int(x == 0), n=2, iterations=1, seed=42)
        assert result.iterations == 1


class TestEdgeCases:
    def test_n_zero_raises(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            grover(lambda x: 0, n=0)

    def test_n_negative_raises(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            grover(lambda x: 0, n=-1)

    def test_invalid_function_output(self):
        with pytest.raises(ValueError, match="must return 0 or 1"):
            grover(lambda x: 2, n=2, seed=42)

    def test_single_qubit(self):
        """n=1: two-item search space. Grover's is only ~50% accurate here,
        so we run multiple repetitions and check the target appears."""
        result = grover(lambda x: int(x == 1), n=1, repetitions=20, seed=42)
        assert 1 in result.found_items


class TestGroverResult:
    def test_repr(self):
        result = GroverResult([5], 3, 2, [1, 0, 1], 1)
        assert "5" in repr(result)
        assert "3" in repr(result)

    def test_found_property(self):
        result = GroverResult([5, 3], 3, 2, [1, 0, 1], 1)
        assert result.found == 5

    def test_found_empty(self):
        result = GroverResult([], 3, 2, [], 1)
        assert result.found is None

    def test_search_space_size(self):
        result = GroverResult([5], 3, 2, [1, 0, 1], 1)
        assert result.search_space_size == 8

    def test_search_space_size_4bit(self):
        result = GroverResult([10], 4, 3, [0, 1, 0, 1], 1)
        assert result.search_space_size == 16


class TestVerboseCallback:
    def test_callback_receives_messages(self):
        messages = []
        grover(lambda x: int(x == 0), n=2, seed=42, verbose_callback=messages.append)
        assert any("Grover" in m for m in messages)
        assert any("Found" in m for m in messages)

    def test_callback_shows_iterations(self):
        messages = []
        grover(lambda x: int(x == 0), n=2, seed=42, verbose_callback=messages.append)
        assert any("iterations" in m for m in messages)
