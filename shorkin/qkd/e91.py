"""E91 Quantum Key Distribution protocol (Ekert 1991).

Entanglement-based QKD protocol using Bell pairs. Security is certified
by violation of the CHSH Bell inequality, which proves the correlations
cannot be explained by a local hidden variable theory (i.e., no eavesdropper
can have pre-existing knowledge of the measurement outcomes).

Measurement angles (optimized for maximal CHSH violation):
    Alice: a1=0, a2=pi/8, a3=pi/4
    Bob:   b1=pi/8, b2=pi/4, b3=3*pi/8

Matching angle pairs (for key generation):
    (a2, b1) = (pi/8, pi/8)
    (a3, b2) = (pi/4, pi/4)

Non-matching pairs contribute to CHSH test:
    S = E(a1,b1) - E(a1,b3) + E(a3,b1) + E(a3,b3)
    Maximum quantum value: 2*sqrt(2) ~ 2.828
"""

from __future__ import annotations

import math
import random

from shorkin.qkd._types import QKDResult
from shorkin.qkd.channel import EntangledChannel
from shorkin.qkd.error_estimation import compute_chsh, estimate_qber
from shorkin.qkd.privacy_amplification import amplify, bits_to_bytes
from shorkin.qkd.protocol import QKDError
from shorkin.qkd.sifting import sift_e91

# Optimal E91 measurement angles (in radians)
ALICE_ANGLES = [0.0, math.pi / 8, math.pi / 4]
BOB_ANGLES = [math.pi / 8, math.pi / 4, 3 * math.pi / 8]

# Pairs of (alice_index, bob_index) where angles match -> key bits
MATCHING_PAIRS = {(1, 0), (2, 1)}


class E91:
    """E91 QKD protocol implementation.

    Steps:
        1. A source generates entangled Bell pairs (|00> + |11>) / sqrt(2).
        2. Alice and Bob each randomly choose from 3 measurement angles.
        3. They measure their respective qubits from each pair.
        4. Matching angles produce key bits; non-matching feed the CHSH test.
        5. CHSH value must exceed 2.0 to certify security.
        6. Error estimation + privacy amplification on key bits.
    """

    BELL_THRESHOLD = 2.0

    def __init__(
        self,
        seed: int | None = None,
        bell_threshold: float | None = None,
        sample_fraction: float = 0.1,
        qber_threshold: float = 0.11,
    ):
        self._rng = random.Random(seed)
        self._seed = seed
        self._bell_threshold = (
            bell_threshold if bell_threshold is not None else self.BELL_THRESHOLD
        )
        self._qber_threshold = qber_threshold
        self._sample_fraction = sample_fraction

    @property
    def name(self) -> str:
        return "e91"

    def generate_key(
        self,
        num_qubits: int,
        channel: EntangledChannel,
        target_key_bits: int = 256,
    ) -> QKDResult:
        """Execute the full E91 protocol."""
        # Step 1: Generate entangled pairs
        # We don't actually use the stored pair objects for measurement;
        # instead we use measure_entangled() which directly simulates
        # the quantum correlations of a Bell state.
        num_generated = 0
        alice_bases: list[int] = []
        bob_bases: list[int] = []
        alice_bits: list[int] = []
        bob_bits: list[int] = []

        for _ in range(num_qubits):
            # Random basis choice (index into angle arrays)
            a_basis = self._rng.randint(0, 2)
            b_basis = self._rng.randint(0, 2)

            # Measure the entangled pair at the chosen angles
            result = channel.measure_entangled(
                ALICE_ANGLES[a_basis], BOB_ANGLES[b_basis]
            )
            if result is None:
                continue

            a_bit, b_bit = result
            num_generated += 1
            alice_bases.append(a_basis)
            bob_bases.append(b_basis)
            alice_bits.append(a_bit)
            bob_bits.append(b_bit)

        if num_generated == 0:
            raise QKDError("No entangled pairs measured successfully")

        # Step 2: Sifting -- separate key bits from Bell test data
        alice_key, bob_key, bell_data = sift_e91(
            alice_bases, bob_bases, alice_bits, bob_bits,
            matching_pairs=MATCHING_PAIRS,
        )

        if len(alice_key) == 0:
            raise QKDError("No key bits after sifting")

        sifted_length = len(alice_key)

        # Step 3: CHSH Bell inequality test
        if bell_data:
            chsh_value = compute_chsh(bell_data)
            if chsh_value < self._bell_threshold:
                raise QKDError(
                    f"CHSH value {chsh_value:.3f} below threshold "
                    f"{self._bell_threshold:.3f} -- "
                    f"entanglement not verified, possible eavesdropper"
                )
        else:
            chsh_value = 0.0

        # Step 4: Error estimation
        qber, alice_remaining, bob_remaining = estimate_qber(
            alice_key,
            bob_key,
            sample_fraction=self._sample_fraction,
            seed=self._seed,
        )

        if qber > self._qber_threshold:
            raise QKDError(
                f"QBER {qber:.3f} exceeds threshold {self._qber_threshold:.3f}"
            )

        if len(alice_remaining) < target_key_bits:
            raise QKDError(
                f"Insufficient key material: "
                f"{len(alice_remaining)} bits < {target_key_bits} target"
            )

        # Step 5: Privacy amplification
        raw_key = bits_to_bytes(alice_remaining)
        final_key = amplify(alice_remaining, target_key_bits)

        return QKDResult(
            raw_key=raw_key,
            final_key=final_key,
            protocol="e91",
            qber=qber,
            key_length_bits=target_key_bits,
            initial_qubit_count=num_qubits,
            sifted_key_length=sifted_length,
            amplified=True,
            metadata={"chsh_value": chsh_value},
        )
