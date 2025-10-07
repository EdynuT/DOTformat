"""Authentication database (auth.db) for users and key wrapper storage.

Contains:
- users (id, username, password_hash, created_at)
- key_wrappers (id, user_id, alg, salt, nonce, tag, wrapped_key, created_at)

Only users + encrypted application master key metadata live here (never the plaintext app key).
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from ..utils.app_paths import get_auth_db_file
from contextlib import contextmanager

# Auth DB relocated to user data directory
AUTH_DB_FILE = get_auth_db_file()
_LEGACY_AUTH_DB = Path(__file__).resolve().parent / "auth.db"
if _LEGACY_AUTH_DB.exists() and not AUTH_DB_FILE.exists():
    try:
        AUTH_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LEGACY_AUTH_DB.replace(AUTH_DB_FILE)
    except Exception:
        pass

AUTH_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS key_wrappers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        alg TEXT NOT NULL,
        salt BLOB NOT NULL,
        nonce BLOB NOT NULL,
        tag BLOB NOT NULL,
        wrapped_key BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    # user_settings migrado para o auth.db para evitar criação do data DB antes do login
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """
]

def init_auth_schema() -> None:
    with get_auth_connection() as conn:
        cur = conn.cursor()
        for stmt in AUTH_SCHEMA:
            cur.execute(stmt)
        conn.commit()

@contextmanager
def get_auth_connection():
    conn = sqlite3.connect(AUTH_DB_FILE)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        conn.close()

__all__ = ["AUTH_DB_FILE", "get_auth_connection", "init_auth_schema"]
