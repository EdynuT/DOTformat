"""Repository for local users stored in auth.db (separate from main data)."""
from __future__ import annotations
from typing import Optional
from ..db.auth_connection import get_auth_connection

class UserRepository:
    def create(self, username: str, password_hash: str, role: str = 'user') -> bool:
        with get_auth_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, password_hash, role)
                )
                conn.commit()
                return True
            except Exception:
                return False

    def find_by_username(self, username: str) -> Optional[tuple]:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?", (username,))
            return cur.fetchone()

    def count_users(self) -> int:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT COUNT(1) FROM users")
            (cnt,) = cur.fetchone()
            return int(cnt)

    def is_first_user(self) -> bool:
        return self.count_users() == 0

    def get_role(self, username: str) -> Optional[str]:
        rec = self.find_by_username(username)
        if rec:
            # rec = (id, username, password_hash, role, created_at)
            return rec[3]
        return None

__all__ = ["UserRepository"]
