"""Shared data types for QKD protocols."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class Basis(Enum):
    """Measurement/preparation basis."""

    RECTILINEAR = auto()  # Z-basis: |0>, |1>
    DIAGONAL = auto()  # X-basis: |+>, |->


class BitValue(Enum):
    """Encoded bit value."""

    ZERO = 0
    ONE = 1


@dataclass(frozen=True)
class Qubit:
    """Representation of a prepared qubit (basis + value)."""

    basis: Basis
    value: BitValue


@dataclass(frozen=True)
class QKDResult:
    """Result of a QKD key exchange session."""

    raw_key: bytes
    final_key: bytes
    protocol: str
    qber: float
    key_length_bits: int
    initial_qubit_count: int
    sifted_key_length: int
    amplified: bool
    metadata: dict = field(default_factory=dict)


@dataclass
class ChannelResult:
    """Result of transmitting qubits through a quantum channel."""

    received_qubits: list[Qubit | None]  # None = lost/not detected
    error_rate: float
    detection_efficiency: float


@dataclass(frozen=True)
class EntangledPair:
    """An entangled qubit pair (for E91)."""

    alice_qubit: Qubit
    bob_qubit: Qubit
