"""Tests for RSA PEM parsing."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from shorkin.rsa import extract_modulus


@pytest.fixture
def rsa_key_pair(tmp_path):
    """Generate a small RSA key pair for testing."""
    private_key = tmp_path / "test_key.pem"
    public_key = tmp_path / "test_key_pub.pem"

    # Generate a small RSA key (512-bit for speed — insecure, but fine for tests)
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:512", "-out", str(private_key)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
        check=True,
        capture_output=True,
    )

    return public_key


class TestExtractModulus:
    def test_extracts_modulus(self, rsa_key_pair):
        n = extract_modulus(rsa_key_pair)
        assert isinstance(n, int)
        assert n > 0
        # 512-bit key -> modulus should be around 512 bits
        assert n.bit_length() >= 500

    def test_modulus_is_odd(self, rsa_key_pair):
        n = extract_modulus(rsa_key_pair)
        assert n % 2 == 1  # RSA modulus is always odd

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_modulus("/nonexistent/path/key.pem")

    def test_invalid_pem(self, tmp_path):
        bad_file = tmp_path / "bad.pem"
        bad_file.write_text("not a real PEM file")
        with pytest.raises(ValueError, match="Failed to parse"):
            extract_modulus(bad_file)
