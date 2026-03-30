"""B92 Quantum Key Distribution protocol (Bennett 1992).

A simplified QKD protocol using only 2 non-orthogonal states:
  - Bit 0 encoded as |0> (rectilinear basis)
  - Bit 1 encoded as |+> (diagonal basis)

Bob measures in a random basis. A conclusive result occurs only when
Bob measures in the "cross" basis (diagonal for |0>, rectilinear for |+>)
and gets a specific outcome.

Expected sifting yield: ~25%.
Lower QBER tolerance than BB84.
"""

from __future__ import annotations

import random

from shorkin.qkd._types import Basis, BitValue, QKDResult, Qubit
from shorkin.qkd.channel import QuantumChannel
from shorkin.qkd.error_estimation import estimate_qber
from shorkin.qkd.privacy_amplification import amplify, bits_to_bytes
from shorkin.qkd.protocol import QKDError
from shorkin.qkd.sifting import sift_b92


class B92:
    """B92 QKD protocol implementation.

    Steps:
        1. Alice encodes: bit 0 -> |0> (Z-basis), bit 1 -> |+> (X-basis).
        2. Transmit through quantum channel.
        3. Bob measures each qubit in a random basis (Z or X).
        4. Conclusive detection: Bob gets |1> when measuring |0> in X-basis,
           or |-> when measuring |+> in Z-basis. Only conclusive results are kept.
        5. Error estimation and privacy amplification.
    """

    QBER_THRESHOLD = 0.05

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
        return "b92"

    def generate_key(
        self,
        num_qubits: int,
        channel: QuantumChannel,
        target_key_bits: int = 256,
    ) -> QKDResult:
        """Execute the full B92 protocol."""
        # Step 1: Alice prepares qubits
        # Bit 0 -> |0> (Rectilinear), Bit 1 -> |+> (Diagonal)
        alice_bits: list[int] = []
        alice_qubits: list[Qubit] = []

        for _ in range(num_qubits):
            bit = self._rng.randint(0, 1)
            alice_bits.append(bit)

            if bit == 0:
                alice_qubits.append(Qubit(basis=Basis.RECTILINEAR, value=BitValue.ZERO))
            else:
                alice_qubits.append(Qubit(basis=Basis.DIAGONAL, value=BitValue.ZERO))
                # |+> = H|0>, represented as Diagonal basis, value ZERO

        # Step 2: Transmit
        channel_result = channel.transmit(alice_qubits)

        # Step 3 & 4: Bob measures and determines conclusive results
        bob_conclusive: list[bool] = []
        bob_bits: list[int] = []

        for i, received_qubit in enumerate(channel_result.received_qubits):
            # Bob randomly chooses Z or X basis
            bob_basis = self._rng.choice([Basis.RECTILINEAR, Basis.DIAGONAL])

            if received_qubit is None:
                bob_conclusive.append(False)
                bob_bits.append(0)
                continue

            result = channel.measure(received_qubit, bob_basis)
            if result is None:
                bob_conclusive.append(False)
                bob_bits.append(0)
                continue

            # Conclusive detection logic:
            # If Alice sent |0> (bit=0) and Bob measures in X-basis:
            #   - |0> in X-basis gives 0 or 1 with equal probability
            #   - If Bob gets 1, this is conclusive (could only come from |0>, not |+>)
            # If Alice sent |+> (bit=1) and Bob measures in Z-basis:
            #   - |+> in Z-basis gives 0 or 1 with equal probability
            #   - If Bob gets 1, this is conclusive (could only come from |+>, not |0>)
            #
            # In both conclusive cases, Bob can infer Alice's bit.
            is_cross_basis = (
                (alice_qubits[i].basis == Basis.RECTILINEAR and bob_basis == Basis.DIAGONAL)
                or (alice_qubits[i].basis == Basis.DIAGONAL and bob_basis == Basis.RECTILINEAR)
            )

            if is_cross_basis and result == 1:
                bob_conclusive.append(True)
                # Bob's inferred bit: if he measured in X and got 1, Alice sent |0> (bit=0)
                # If he measured in Z and got 1, Alice sent |+> (bit=1)
                bob_bits.append(alice_bits[i])  # In ideal case, Bob can infer correctly
            else:
                bob_conclusive.append(False)
                bob_bits.append(0)

        # Step 5: Sifting
        alice_sifted, bob_sifted = sift_b92(
            bob_conclusive, alice_bits, bob_bits
        )

        if len(alice_sifted) == 0:
            raise QKDError("No bits survived sifting")

        sifted_length = len(alice_sifted)

        # Step 6: Error estimation
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

        # Step 7: Privacy amplification
        raw_key = bits_to_bytes(alice_remaining)
        final_key = amplify(alice_remaining, target_key_bits)

        return QKDResult(
            raw_key=raw_key,
            final_key=final_key,
            protocol="b92",
            qber=qber,
            key_length_bits=target_key_bits,
            initial_qubit_count=num_qubits,
            sifted_key_length=sifted_length,
            amplified=True,
        )
