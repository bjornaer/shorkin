"""Quantum Key Distribution (QKD) protocols.

Supported protocols:
    - BB84 (Bennett-Brassard 1984): 2 bases, 4 states
    - B92 (Bennett 1992): 2 non-orthogonal states
    - E91 (Ekert 1991): Entanglement-based with Bell inequality test

Usage:
    from shorkin.qkd import BB84, SimulatedChannel

    channel = SimulatedChannel(seed=42)
    protocol = BB84(seed=42)
    result = protocol.generate_key(num_qubits=4096, channel=channel)
    print(result.final_key.hex())
"""

from shorkin.qkd._types import Basis, BitValue, ChannelResult, EntangledPair, QKDResult, Qubit
from shorkin.qkd.b92 import B92
from shorkin.qkd.bb84 import BB84
from shorkin.qkd.channel import EntangledChannel, QuantumChannel, SimulatedChannel
from shorkin.qkd.e91 import E91
from shorkin.qkd.encryption import decrypt, encrypt
from shorkin.qkd.key_store import KeyStore
from shorkin.qkd.protocol import QKDError, QKDProtocol

__all__ = [
    "BB84",
    "B92",
    "E91",
    "Basis",
    "BitValue",
    "ChannelResult",
    "EntangledChannel",
    "EntangledPair",
    "KeyStore",
    "QKDError",
    "QKDProtocol",
    "QKDResult",
    "QuantumChannel",
    "Qubit",
    "SimulatedChannel",
    "decrypt",
    "encrypt",
]
