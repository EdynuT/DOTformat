"""Database connection and schema initialization for DOTformat.

Uses SQLite (file-based) for simplicity. All foreign keys enabled.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from ..utils.app_paths import get_db_file
from contextlib import contextmanager

# Data file now lives in user data directory (supports packaged executable updates)
DB_FILE = get_db_file()

# Legacy location (previous versions placed DB next to package)
_LEGACY_DB = Path(__file__).resolve().parent / "dotformat.db"
if _LEGACY_DB.exists() and not DB_FILE.exists():  # one-time migration
    try:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LEGACY_DB.replace(DB_FILE)
    except Exception:
        # Best effort; if it fails we continue with new DB_FILE
        pass

SCHEMA_STATEMENTS = [
    # Logs for any feature invocation
    """
    CREATE TABLE IF NOT EXISTS conversion_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feature TEXT NOT NULL,
        input_path TEXT,
        output_path TEXT,
        status TEXT NOT NULL,
        detail TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
]

def init_schema() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
        cur = conn.cursor()
        for stmt in SCHEMA_STATEMENTS:
            cur.execute(stmt)
        # Migration: add username column to conversion_log if not present
        cur.execute("PRAGMA table_info(conversion_log);")
        cols = [row[1] for row in cur.fetchall()]
        if "username" not in cols:
            cur.execute("ALTER TABLE conversion_log ADD COLUMN username TEXT;")
        conn.commit()

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        # Avoid long hard locks by waiting a bit when the DB is busy (helps during table swap)
        conn.execute("PRAGMA busy_timeout = 5000;")
        yield conn
    finally:
        conn.close()
