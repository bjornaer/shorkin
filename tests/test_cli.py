"""Tests for the CLI entry point."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from shorkin.cli import main


class TestCLIFactor:
    def test_factor_15_classical(self):
        exit_code = main(["factor", "15", "--mode", "classical"])
        assert exit_code == 0

    def test_factor_21_classical(self):
        exit_code = main(["factor", "21", "--mode", "classical"])
        assert exit_code == 0

    def test_factor_prime(self):
        exit_code = main(["factor", "7", "--mode", "classical"])
        assert exit_code == 1

    def test_factor_quiet(self, capsys):
        main(["factor", "15", "--mode", "classical", "--quiet"])
        captured = capsys.readouterr()
        # Quiet mode: just the factors
        assert "3" in captured.out
        assert "5" in captured.out

    def test_factor_verbose(self):
        exit_code = main(["factor", "15", "--mode", "classical", "--verbose"])
        assert exit_code == 0

    def test_factor_large_classical_without_force(self):
        # Very large number without --force should fail in classical mode
        big = 2**61 - 1  # Mersenne prime, but bit_length > 60
        exit_code = main(["factor", str(big), "--mode", "classical"])
        assert exit_code == 1


class TestCLIFactorKey:
    def test_factor_key_missing_file(self):
        exit_code = main(["factor-key", "/nonexistent.pem"])
        assert exit_code == 1

    def test_factor_key_with_real_key(self, tmp_path):
        """Generate a tiny RSA key and factor-key it."""
        private_key = tmp_path / "key.pem"
        public_key = tmp_path / "pub.pem"

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

        # Should fail (too large for classical without --force) but should parse the key
        exit_code = main(["factor-key", str(public_key), "--mode", "classical"])
        assert exit_code == 1  # 512-bit is too large for classical
