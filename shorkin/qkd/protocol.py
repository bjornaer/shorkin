"""QKD protocol abstraction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from shorkin.qkd._types import QKDResult
    from shorkin.qkd.channel import QuantumChannel


class QKDError(Exception):
    """Raised when a QKD protocol fails (QBER too high, insufficient key material, etc.)."""


class QKDProtocol(Protocol):
    """Protocol interface for QKD key exchange implementations."""

    @property
    def name(self) -> str: ...

    def generate_key(
        self,
        num_qubits: int,
        channel: QuantumChannel,
        target_key_bits: int = 256,
    ) -> QKDResult: ...
