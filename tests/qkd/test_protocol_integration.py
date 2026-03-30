"""End-to-end integration tests: protocol -> key -> encrypt -> decrypt."""

import pytest

from shorkin.qkd.bb84 import BB84
from shorkin.qkd.b92 import B92
from shorkin.qkd.e91 import E91
from shorkin.qkd.channel import SimulatedChannel
from shorkin.qkd.encryption import decrypt, encrypt


class TestProtocolIntegration:
    """Test full pipeline for each protocol."""

    def test_bb84_encrypt_decrypt(self):
        channel = SimulatedChannel(seed=42)
        protocol = BB84(seed=42)
        result = protocol.generate_key(num_qubits=4000, channel=channel)

        plaintext = b"Top secret quantum message"
        ciphertext = encrypt(plaintext, result.final_key)
        decrypted = decrypt(ciphertext, result.final_key)
        assert decrypted == plaintext

    def test_b92_encrypt_decrypt(self):
        channel = SimulatedChannel(seed=42)
        protocol = B92(seed=42)
        result = protocol.generate_key(num_qubits=8000, channel=channel)

        plaintext = b"B92 secured data"
        ciphertext = encrypt(plaintext, result.final_key)
        decrypted = decrypt(ciphertext, result.final_key)
        assert decrypted == plaintext

    def test_e91_encrypt_decrypt(self):
        channel = SimulatedChannel(seed=42)
        protocol = E91(seed=42)
        result = protocol.generate_key(num_qubits=20000, channel=channel)

        plaintext = b"E91 entangled secrets"
        ciphertext = encrypt(plaintext, result.final_key)
        decrypted = decrypt(ciphertext, result.final_key)
        assert decrypted == plaintext

    def test_different_protocols_different_keys(self):
        channel1 = SimulatedChannel(seed=42)
        channel2 = SimulatedChannel(seed=42)

        bb84 = BB84(seed=42)
        b92 = B92(seed=42)

        r1 = bb84.generate_key(num_qubits=4000, channel=channel1)
        r2 = b92.generate_key(num_qubits=8000, channel=channel2)

        # Different protocols should produce different keys
        assert r1.final_key != r2.final_key
        assert r1.protocol != r2.protocol
