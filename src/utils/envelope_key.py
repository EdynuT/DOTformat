"""Envelope key management for Option C.

Generates a random application master key (K_APP) used to encrypt the main data DB.
Stores only an encrypted (wrapped) form of K_APP in the auth database (key_wrappers table).
Each user can have one wrapper; currently we store a single wrapper per user with alg='AES-EAX-PBKDF2'.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import os
import hashlib
from Crypto.Cipher import AES  # type: ignore
from ..db.auth_connection import get_auth_connection

PBKDF2_ITERATIONS_WRAP = 160_000
K_APP_LEN = 32
SALT_LEN = 16

@dataclass
class KeyWrapperRecord:
    id: int
    user_id: int
    alg: str
    salt: bytes
    nonce: bytes
    tag: bytes
    wrapped_key: bytes


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS_WRAP, dklen=32)


def create_and_store_wrapper(user_id: int, user_password: str, k_app: bytes | None = None) -> bytes:
    """Create (or reuse provided) K_APP and store its encrypted form for user_id.
    Returns the plaintext K_APP.
    """
    if k_app is None:
        k_app = os.urandom(K_APP_LEN)
    salt = os.urandom(SALT_LEN)
    key = _derive(user_password, salt)
    cipher = AES.new(key, AES.MODE_EAX)
    nonce = cipher.nonce
    wrapped_key, tag = cipher.encrypt_and_digest(k_app)
    with get_auth_connection() as conn:
        conn.execute(
            "INSERT INTO key_wrappers (user_id, alg, salt, nonce, tag, wrapped_key) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'AES-EAX-PBKDF2', salt, nonce, tag, wrapped_key)
        )
        conn.commit()
    return k_app


def load_wrapper_for_user(user_id: int) -> Optional[KeyWrapperRecord]:
    with get_auth_connection() as conn:
        cur = conn.execute(
            "SELECT id, user_id, alg, salt, nonce, tag, wrapped_key FROM key_wrappers WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return KeyWrapperRecord(
            id=row[0], user_id=row[1], alg=row[2], salt=row[3], nonce=row[4], tag=row[5], wrapped_key=row[6]
        )


def unwrap_k_app(user_password: str, rec: KeyWrapperRecord) -> bytes:
    if rec.alg != 'AES-EAX-PBKDF2':
        raise RuntimeError('Unsupported key wrapper algorithm: ' + rec.alg)
    key = _derive(user_password, rec.salt)
    cipher = AES.new(key, AES.MODE_EAX, nonce=rec.nonce)
    try:
        k_app = cipher.decrypt_and_verify(rec.wrapped_key, rec.tag)
    except Exception as e:  # wrong password or corruption
        raise RuntimeError('Failed to unlock master key (wrong password or data corrupted).') from e
    return k_app

__all__ = [
    'create_and_store_wrapper', 'load_wrapper_for_user', 'unwrap_k_app'
]
