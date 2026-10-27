"""Security & Utilities Tool Module.

Provides cryptographically secure temporary password generation and data sanitization.
"""

import string
import secrets
from typing import Dict, Any


def get_crypto_password(length: int = 16) -> Dict[str, Any]:
    """Produce a random, cryptographically strong temporary password.

    Ensures password compliance:
    - Minimum length: 14 characters (default: 16)
    - Contains at least 1 uppercase, 1 lowercase, 1 digit, and 1 special symbol
    - Uses Python's `secrets` cryptographically secure random number generator (CSPRNG)

    Args:
        length: Desired password length (minimum 14, default 16).

    Returns:
        Dict containing generated password and compliance metadata.

    Raises:
        ValueError: If length is less than 14.
    """
    if length < 14:
        raise ValueError(f"Password length must be at least 14 characters; requested: {length}")

    alphabet_upper = string.ascii_uppercase
    alphabet_lower = string.ascii_lowercase
    digits = string.digits
    special_chars = "!@#$%^&*"
    all_chars = alphabet_upper + alphabet_lower + digits + special_chars

    # Guarantee at least one from each required character class
    password_chars = [
        secrets.choice(alphabet_upper),
        secrets.choice(alphabet_lower),
        secrets.choice(digits),
        secrets.choice(special_chars),
    ]

    # Fill remaining positions using CSPRNG
    for _ in range(length - 4):
        password_chars.append(secrets.choice(all_chars))

    # Shuffle cryptographically using SystemRandom
    sr = secrets.SystemRandom()
    sr.shuffle(password_chars)
    password = "".join(password_chars)

    return {
        "password": password,
        "length": length,
        "entropy_bits": length * 6.5,
        "meets_complexity": True,
    }
