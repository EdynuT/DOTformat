"""Authentication support: login lockout policy and last-user persistence.

Pure business rules with no UI dependencies (moved out of the old auth controller).
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Optional

from ..db.auth_connection import get_auth_connection
from ..db.connection import DB_FILE

# Login lockout policy: after LOCKOUT_MAX_ATTEMPTS failed logins, the username is
# locked out for LOCKOUT_DURATION_SECONDS.
LOCKOUT_MAX_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes


class AuthService:
    def encrypted_db_present_without_plain(self) -> bool:
        from ..utils.app_paths import get_encrypted_db_file
        enc = Path(str(get_encrypted_db_file()))
        return enc.exists() and not DB_FILE.exists()

    def get_last_user(self) -> Optional[str]:
        try:
            with get_auth_connection() as conn:
                row = conn.execute("SELECT value FROM user_settings WHERE key='last_user' LIMIT 1").fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def set_last_user(self, username: str) -> None:
        try:
            with get_auth_connection() as conn:
                conn.execute(
                    "INSERT INTO user_settings(key,value) VALUES('last_user',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (username,)
                )
                conn.commit()
        except Exception:
            pass

    def _get_kv(self, key: str) -> Optional[str]:
        try:
            with get_auth_connection() as conn:
                row = conn.execute("SELECT value FROM user_settings WHERE key=?", (key,)).fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def _set_kv(self, key: str, value: str) -> None:
        try:
            with get_auth_connection() as conn:
                conn.execute(
                    "INSERT INTO user_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value)
                )
                conn.commit()
        except Exception:
            pass

    def _clear_kv(self, key: str) -> None:
        try:
            with get_auth_connection() as conn:
                conn.execute("DELETE FROM user_settings WHERE key=?", (key,))
                conn.commit()
        except Exception:
            pass

    def check_lockout(self, username: str) -> tuple[bool, int]:
        """Return (locked, seconds_remaining)."""
        until_s = self._get_kv(f"lockout_until:{username}")
        if not until_s:
            return False, 0
        try:
            until = float(until_s)
        except Exception:
            return False, 0
        now = time.time()
        if now < until:
            return True, int(max(1, round(until - now)))
        self._clear_kv(f"lockout_until:{username}")
        return False, 0

    def register_fail(self, username: str) -> tuple[bool, int]:
        """Register a failed login attempt. Returns (just_locked, attempts_left)."""
        key = f"login_fail:{username}"
        try:
            n_raw = self._get_kv(key)
            n = int(n_raw) if n_raw is not None else 0
        except Exception:
            n = 0
        n += 1
        if n >= LOCKOUT_MAX_ATTEMPTS:
            self._set_kv(f"lockout_until:{username}", str(time.time() + LOCKOUT_DURATION_SECONDS))
            self._clear_kv(key)
            return True, 0
        self._set_kv(key, str(n))
        return False, max(0, LOCKOUT_MAX_ATTEMPTS - n)

    def clear_fail(self, username: str) -> None:
        self._clear_kv(f"login_fail:{username}")
        self._clear_kv(f"lockout_until:{username}")


__all__ = ["AuthService", "LOCKOUT_MAX_ATTEMPTS", "LOCKOUT_DURATION_SECONDS"]
