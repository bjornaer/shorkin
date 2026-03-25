"""RSA PEM key parsing."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_public_key


def extract_modulus(pem_path: str | Path) -> int:
    """Extract the RSA modulus (n) from a PEM public key file.

    Args:
        pem_path: Path to a PEM-encoded RSA public key file.

    Returns:
        The RSA modulus as an integer.

    Raises:
        FileNotFoundError: If the PEM file doesn't exist.
        ValueError: If the file is not a valid RSA public key.
    """
    pem_path = Path(pem_path)
    pem_data = pem_path.read_bytes()

    try:
        key = load_pem_public_key(pem_data)
    except Exception as exc:
        raise ValueError(f"Failed to parse PEM file: {exc}") from exc

    # Access RSA public numbers
    try:
        public_numbers = key.public_numbers()
    except AttributeError:
        raise ValueError("Key is not an RSA public key")

    return public_numbers.n
