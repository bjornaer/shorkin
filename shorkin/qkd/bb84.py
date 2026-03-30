"""BB84 Quantum Key Distribution protocol (Bennett-Brassard 1984).

The original QKD protocol using 2 conjugate bases (rectilinear and diagonal)
with 4 possible qubit states: |0>, |1>, |+>, |->.
Expected sifting yield: ~50%.
Secure QBER threshold: ~11%.
"""

from __future__ import annotations

import random

from shorkin.qkd._types import Basis, BitValue, QKDResult, Qubit
from shorkin.qkd.channel import QuantumChannel
from shorkin.qkd.error_estimation import estimate_qber
from shorkin.qkd.privacy_amplification import amplify, bits_to_bytes
from shorkin.qkd.protocol import QKDError
from shorkin.qkd.sifting import sift_bb84


class BB84:
    """BB84 QKD protocol implementation.

    Steps:
        1. Alice randomly chooses bits and bases, prepares qubits.
        2. Qubits are sent through the quantum channel.
        3. Bob randomly chooses measurement bases and measures.
        4. Sifting: Alice and Bob compare bases, keep matching ones (~50%).
        5. Error estimation: sample a subset to compute QBER.
        6. Privacy amplification: hash to distill a secure key.
    """

    QBER_THRESHOLD = 0.11

    def __init__(
        self,
        seed: int | None = None,
        qber_threshold: float | None = None,
        sample_fraction: float = 0.1,
    ):
        self._rng = random.Random(seed)
        self._seed = seed
        self._qber_threshold = (
            qber_threshold if qber_threshold is not None else self.QBER_THRESHOLD
        )
        self._sample_fraction = sample_fraction

    @property
    def name(self) -> str:
        return "bb84"

    def generate_key(
        self,
        num_qubits: int,
        channel: QuantumChannel,
        target_key_bits: int = 256,
    ) -> QKDResult:
        """Execute the full BB84 protocol."""
        # Step 1: Alice prepares random bits and bases
        alice_bits: list[int] = []
        alice_bases: list[Basis] = []
        alice_qubits: list[Qubit] = []

        for _ in range(num_qubits):
            bit = self._rng.randint(0, 1)
            basis = self._rng.choice([Basis.RECTILINEAR, Basis.DIAGONAL])
            value = BitValue.ONE if bit == 1 else BitValue.ZERO
            qubit = Qubit(basis=basis, value=value)

            alice_bits.append(bit)
            alice_bases.append(basis)
            alice_qubits.append(qubit)

        # Step 2: Transmit through quantum channel
        channel_result = channel.transmit(alice_qubits)

        # Step 3: Bob measures in random bases
        bob_bases: list[Basis] = []
        bob_bits: list[int] = []

        for received_qubit in channel_result.received_qubits:
            bob_basis = self._rng.choice([Basis.RECTILINEAR, Basis.DIAGONAL])
            bob_bases.append(bob_basis)

            if received_qubit is None:
                bob_bits.append(self._rng.randint(0, 1))  # random if lost
                continue

            result = channel.measure(received_qubit, bob_basis)
            bob_bits.append(result if result is not None else self._rng.randint(0, 1))

        # Step 4: Sifting
        alice_sifted, bob_sifted = sift_bb84(
            alice_bases, bob_bases, alice_bits, bob_bits
        )

        if len(alice_sifted) == 0:
            raise QKDError("No bits survived sifting")

        sifted_length = len(alice_sifted)

        # Step 5: Error estimation
        qber, alice_remaining, bob_remaining = estimate_qber(
            alice_sifted,
            bob_sifted,
            sample_fraction=self._sample_fraction,
            seed=self._seed,
        )

        if qber > self._qber_threshold:
            raise QKDError(
                f"QBER {qber:.3f} exceeds threshold {self._qber_threshold:.3f} -- "
                f"possible eavesdropper detected"
            )

        if len(alice_remaining) < target_key_bits:
            raise QKDError(
                f"Insufficient key material after error estimation: "
                f"{len(alice_remaining)} bits < {target_key_bits} target"
            )

        # Step 6: Privacy amplification
        raw_key = bits_to_bytes(alice_remaining)
        final_key = amplify(alice_remaining, target_key_bits)

        return QKDResult(
            raw_key=raw_key,
            final_key=final_key,
            protocol="bb84",
            qber=qber,
            key_length_bits=target_key_bits,
            initial_qubit_count=num_qubits,
            sifted_key_length=sifted_length,
            amplified=True,
        )
