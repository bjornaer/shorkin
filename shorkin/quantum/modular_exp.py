"""Modular exponentiation gate for Shor's algorithm."""

from __future__ import annotations

from typing import Sequence

import cirq
import numpy as np


class ModularExp(cirq.ArithmeticGate):
    """Gate that computes |y>|e> -> |y * base^e mod modulus>|e>.

    The target register holds y and the exponent register holds e.
    This gate is used in quantum phase estimation for order finding.
    """

    def __init__(self, target_size: int, exponent_size: int, base: int, modulus: int):
        self._target_size = target_size
        self._exponent_size = exponent_size
        self._base = base
        self._modulus = modulus

    def registers(self) -> Sequence[int | Sequence[int]]:
        return [2] * self._target_size, [2] * self._exponent_size

    def with_registers(self, *new_registers) -> "ModularExp":
        if len(new_registers) != 2:
            raise ValueError("Expected 2 registers")
        target_reg, exponent_reg = new_registers
        # Infer sizes from the new registers
        target_size = len(target_reg) if isinstance(target_reg, (list, tuple)) else self._target_size
        exponent_size = len(exponent_reg) if isinstance(exponent_reg, (list, tuple)) else self._exponent_size
        return ModularExp(target_size, exponent_size, self._base, self._modulus)

    def apply(self, *register_values: int) -> tuple[int, int]:
        target_val, exponent_val = register_values
        if target_val >= self._modulus:
            return target_val, exponent_val
        result = (target_val * pow(self._base, exponent_val, self._modulus)) % self._modulus
        return result, exponent_val

    @property
    def base(self) -> int:
        return self._base

    @property
    def modulus(self) -> int:
        return self._modulus

    @property
    def target_size(self) -> int:
        return self._target_size

    @property
    def exponent_size(self) -> int:
        return self._exponent_size

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        wire_symbols = [f"y{i}" for i in range(self._target_size)]
        wire_symbols += [f"e{i}" for i in range(self._exponent_size)]
        return cirq.CircuitDiagramInfo(wire_symbols=wire_symbols)

    def __repr__(self) -> str:
        return (
            f"ModularExp(target_size={self._target_size}, "
            f"exponent_size={self._exponent_size}, "
            f"base={self._base}, modulus={self._modulus})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, ModularExp):
            return NotImplemented
        return (
            self._target_size == other._target_size
            and self._exponent_size == other._exponent_size
            and self._base == other._base
            and self._modulus == other._modulus
        )

    def __hash__(self) -> int:
        return hash((self._target_size, self._exponent_size, self._base, self._modulus))
