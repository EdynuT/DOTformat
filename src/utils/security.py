"""Security utilities for local authentication.

Uses PBKDF2-HMAC (SHA256) for password hashing; stores salt + iterations.
No external dependency required, keeps portability for offline usage.
Format: iterations$salt_hex$hash_hex
"""
from __future__ import annotations
import os
import hashlib
import hmac
from typing import Tuple

DEFAULT_ITERATIONS = 130_000  # Reasonable for local desktop apps
SALT_BYTES = 16

def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=32)

def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    salt = os.urandom(SALT_BYTES)
    dk = _pbkdf2(password, salt, iterations)
    return f"{iterations}${salt.hex()}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        iterations_s, salt_hex, hash_hex = stored.split('$')
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False
    candidate = _pbkdf2(password, salt, iterations)
    return hmac.compare_digest(candidate, expected)

__all__ = ["hash_password", "verify_password"]
