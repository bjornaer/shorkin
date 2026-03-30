"""Classical channel message types for QKD key exchange over HTTP/gRPC."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum


class SessionStatus(str, Enum):
    """QKD session status."""

    INITIATING = "initiating"
    SIFTING = "sifting"
    VERIFYING = "verifying"
    ACTIVE = "active"
    EXPIRED = "expired"
    ABORTED = "aborted"


@dataclass
class KeyExchangeInit:
    """Alice -> Bob: Initiate QKD session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol: str = "bb84"
    num_qubits: int = 4096
    target_key_bits: int = 256
    peer_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> KeyExchangeInit:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BasisAnnouncement:
    """Announce measurement bases for sifting."""

    session_id: str = ""
    bases: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BasisAnnouncement:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SiftingResult:
    """Announce which indices to keep."""

    session_id: str = ""
    matching_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SiftingResult:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ErrorEstimationRequest:
    """Share sample bit values for QBER estimation."""

    session_id: str = ""
    sample_indices: list[int] = field(default_factory=list)
    sample_values: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ErrorEstimationRequest:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ErrorEstimationResponse:
    """Response with counterpart's sample values."""

    session_id: str = ""
    sample_values: list[int] = field(default_factory=list)
    qber: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ErrorEstimationResponse:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class KeyConfirmation:
    """Final handshake confirming key hash matches."""

    session_id: str = ""
    key_hash: str = ""
    status: str = "ok"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> KeyConfirmation:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def serialize(msg) -> str:
    """Serialize a message to JSON."""
    return json.dumps(msg.to_dict())


def deserialize(data: str | bytes, msg_type: type):
    """Deserialize JSON to a message type."""
    raw = json.loads(data)
    return msg_type.from_dict(raw)
