"""Repository for local users stored in auth.db (separate from main data)."""
from __future__ import annotations
from typing import List, Optional
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

    def find_by_id(self, user_id: int) -> Optional[tuple]:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?", (user_id,))
            return cur.fetchone()

    def list_all(self) -> List[tuple]:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id ASC")
            return list(cur.fetchall())

    def count_users(self) -> int:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT COUNT(1) FROM users")
            (cnt,) = cur.fetchone()
            return int(cnt)

    def count_admins(self) -> int:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT COUNT(1) FROM users WHERE role='admin'")
            (cnt,) = cur.fetchone()
            return int(cnt)

    def first_user_id(self) -> Optional[int]:
        with get_auth_connection() as conn:
            row = conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
            return row[0] if row else None

    def is_first_user(self) -> bool:
        return self.count_users() == 0

    def get_role(self, username: str) -> Optional[str]:
        rec = self.find_by_username(username)
        if rec:
            # rec = (id, username, password_hash, role, created_at)
            return rec[3]
        return None

    def update_role(self, user_id: int, role: str) -> None:
        with get_auth_connection() as conn:
            conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
            conn.commit()

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        with get_auth_connection() as conn:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))
            conn.commit()

    def delete(self, user_id: int) -> None:
        with get_auth_connection() as conn:
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.execute("DELETE FROM key_wrappers WHERE user_id=?", (user_id,))
            conn.commit()

__all__ = ["UserRepository"]
