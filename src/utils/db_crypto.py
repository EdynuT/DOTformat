"""Database file encryption/decryption utilities.

Encrypts the SQLite database file (dotformat.db) into dotformat.db.dotf using
AES (EAX mode) with a key derived from a user password via PBKDF2-HMAC-SHA256.

File format (binary):
    0-6   bytes : ASCII magic header b'DOTFDB' (version marker)
    7     byte  : version (0x01)
    8-9   bytes : salt length (uint16 big-endian)
    10..  salt  : variable
    next 16     : nonce
    next 16     : auth tag
    rest        : ciphertext

Rationale:
- EAX provides confidentiality + integrity without needing separate HMAC.
- PBKDF2 keeps dependency surface minimal beyond PyCryptodome.
- We store salt openly; password is never stored.

NOTE: We DO NOT encrypt while the application is running; encryption happens
on user-confirmed exit only, and decryption is prompted at startup if an
encrypted file exists.
"""
from __future__ import annotations
from pathlib import Path
import os
import struct
import hashlib
from typing import Tuple

try:
    from Crypto.Cipher import AES  # type: ignore
except ImportError:  # pragma: no cover - dependency missing
    AES = None  # type: ignore

MAGIC = b'DOTFDB'  # 6 bytes
VERSION = 1
PBKDF2_ITERATIONS = 160_000  # Slightly higher than auth hash
KEY_LEN = 32
SALT_LEN = 16

class CryptoError(RuntimeError):
    pass

def derive_key(password: str, salt: bytes) -> bytes:
    """Derive 32-byte key from password & salt via PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS, dklen=KEY_LEN)

def encrypt_file(src: Path, password: str, dest: Path | None = None, overwrite: bool = True) -> Path:
    if AES is None:
        raise CryptoError("PyCryptodome not installed (Crypto.Cipher.AES unavailable)")
    if not src.exists():
        raise CryptoError(f"Source file not found: {src}")
    if dest is None:
        dest = src.with_suffix(src.suffix + '.dotf')
    if dest.exists() and not overwrite:
        raise CryptoError(f"Destination exists: {dest}")
    salt = os.urandom(SALT_LEN)
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_EAX)
    nonce = cipher.nonce
    with open(src, 'rb') as f:
        plaintext = f.read()
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    with open(dest, 'wb') as f:
        f.write(MAGIC)
        f.write(bytes([VERSION]))
        f.write(struct.pack('>H', len(salt)))
        f.write(salt)
        f.write(nonce)
        f.write(tag)
        f.write(ciphertext)
    return dest

def decrypt_file(enc_file: Path, password: str, dest: Path | None = None, overwrite: bool = True) -> Path:
    if AES is None:
        raise CryptoError("PyCryptodome not installed (Crypto.Cipher.AES unavailable)")
    if not enc_file.exists():
        raise CryptoError(f"Encrypted file not found: {enc_file}")
    with open(enc_file, 'rb') as f:
        header = f.read(6)
        if header != MAGIC:
            raise CryptoError("Invalid file magic; not a DOTformat encrypted DB")
        ver = f.read(1)
        if not ver or ver[0] != VERSION:
            raise CryptoError("Unsupported encrypted file version")
        salt_len_bytes = f.read(2)
        if len(salt_len_bytes) != 2:
            raise CryptoError("Corrupt header (salt length)")
        salt_len = struct.unpack('>H', salt_len_bytes)[0]
        salt = f.read(salt_len)
        if len(salt) != salt_len:
            raise CryptoError("Corrupt file (salt truncated)")
        nonce = f.read(16)
        if len(nonce) != 16:
            raise CryptoError("Corrupt file (nonce)")
        tag = f.read(16)
        if len(tag) != 16:
            raise CryptoError("Corrupt file (tag)")
        ciphertext = f.read()
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    except Exception as e:  # pragma: no cover - auth failure
        raise CryptoError("Decryption failed (wrong password or corrupted file)") from e
    if dest is None:
        # remove trailing .dotf
        if enc_file.suffix == '.dotf':
            dest = enc_file.with_suffix('')
        else:
            dest = enc_file.parent / 'dotformat.db'
    if dest.exists() and not overwrite:
        raise CryptoError(f"Destination exists: {dest}")
    with open(dest, 'wb') as f:
        f.write(plaintext)
    return dest

__all__ = [
    'CryptoError', 'derive_key', 'encrypt_file', 'decrypt_file'
]
