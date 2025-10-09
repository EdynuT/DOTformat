"""Lightweight user settings using auth.db's user_settings table.

Provides simple get/set helpers to store small preferences like last used folders.
"""
from __future__ import annotations
from typing import Optional
from ..db.auth_connection import get_auth_connection

def get_setting(key: str) -> Optional[str]:
    try:
        with get_auth_connection() as conn:
            row = conn.execute("SELECT value FROM user_settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
    except Exception:
        return None

def set_setting(key: str, value: str) -> None:
    try:
        with get_auth_connection() as conn:
            conn.execute(
                "INSERT INTO user_settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            conn.commit()
    except Exception:
        pass

__all__ = ["get_setting", "set_setting"]
