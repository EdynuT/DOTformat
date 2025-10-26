"""Repository layer for conversion logs."""
from __future__ import annotations
from typing import List, Tuple, Optional
from ..db.connection import get_connection

Row = Tuple[int, str, Optional[str], Optional[str], str, Optional[str], Optional[str], str]

class ConversionRepository:
    def add(self, feature: str, input_path: str | None, output_path: str | None, status: str, detail: str | None = None, username: str | None = None) -> None:
        with get_connection() as conn:
            if username is None:
                conn.execute(
                    "INSERT INTO conversion_log (feature, input_path, output_path, status, detail) VALUES (?,?,?,?,?)",
                    (feature, input_path, output_path, status, detail)
                )
            else:
                conn.execute(
                    "INSERT INTO conversion_log (feature, input_path, output_path, status, detail, username) VALUES (?,?,?,?,?,?)",
                    (feature, input_path, output_path, status, detail, username)
                )
            conn.commit()

    def list_last(self, limit: int = 50) -> List[Row]:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT id, feature, input_path, output_path, status, detail, username, created_at FROM conversion_log ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return list(cur.fetchall())

    def list_all(self) -> List[Row]:
        """Return all conversion log rows (ordered by id ascending)."""
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT id, feature, input_path, output_path, status, detail, username, created_at FROM conversion_log ORDER BY id ASC"
            )
            return list(cur.fetchall())

    def list_by_username(self, username: str) -> List[Row]:
        """Return all log rows for a specific username."""
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT id, feature, input_path, output_path, status, detail, username, created_at FROM conversion_log WHERE username=? ORDER BY id ASC",
                (username,)
            )
            return list(cur.fetchall())

    def delete_by_username(self, username: str) -> int:
        """Delete all log rows for a specific username. Returns number of rows deleted."""
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM conversion_log WHERE username=?", (username,))
            conn.commit()
            try:
                return cur.rowcount or 0
            except Exception:
                return 0
