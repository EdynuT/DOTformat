"""Database maintenance utilities.

Includes a safe renumbering routine for conversion_log IDs so that the
oldest entry becomes ID=1 and newer entries increase sequentially.
"""
from __future__ import annotations
from typing import Callable, Optional
from .connection import get_connection

ProgressCb = Optional[Callable[[float], None]]
StatusCb = Optional[Callable[[str], None]]


def needs_log_normalization() -> bool:
    """Quick check to decide if normalization is needed.

    Returns True if:
    - There are rows and the first chronological row does not have id=1; or
    - There are gaps (MAX(id) != COUNT(*)), indicating non-sequential IDs.

    Returns False when there are no rows or the IDs already look normalized.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        # Count rows
        cur.execute("SELECT COUNT(*) FROM conversion_log")
        total = cur.fetchone()[0]
        if total == 0:
            return False
        # First chronological id
        cur.execute("SELECT id FROM conversion_log ORDER BY datetime(created_at) ASC, id ASC LIMIT 1")
        first_id = cur.fetchone()[0]
        if first_id != 1:
            return True
        # Check for gaps (rough but effective)
        cur.execute("SELECT MAX(id) FROM conversion_log")
        max_id = cur.fetchone()[0] or 0
        return max_id != total


def _table_exists(cur, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def normalize_conversion_log_ids(progress: ProgressCb = None, status: StatusCb = None) -> tuple[bool, str, int]:
    """Renumber conversion_log IDs in chronological order.

    - Preserves all columns and their values, including created_at and username.
    - Rebuilds the table so IDs are assigned 1..N in ascending chronological order.
    - Returns (success, message, rows_migrated).
    """
    def report(v: float):
        if progress:
            try:
                progress(max(0.0, min(100.0, float(v))))
            except Exception:
                pass
    def set_status(msg: str):
        if status:
            try:
                status(str(msg))
            except Exception:
                pass

    with get_connection() as conn:
        cur = conn.cursor()
        # Count rows
        cur.execute("SELECT COUNT(*) FROM conversion_log")
        total = cur.fetchone()[0]
        if total == 0:
            return True, "No rows to normalize.", 0

        set_status("Verificando registros…")
        # Quick check: if first chronological row already has id=1 and ids are monotonic, skip
        cur.execute("SELECT id FROM conversion_log ORDER BY datetime(created_at) ASC, id ASC LIMIT 1")
        first_id = cur.fetchone()[0]
        if first_id == 1:
            # Also check that max(id) == total (rough sanity)
            cur.execute("SELECT MAX(id) FROM conversion_log")
            max_id = cur.fetchone()[0] or 0
            if max_id == total:
                return True, "Log IDs already normalized.", 0

        report(2.0)
        set_status("Lendo registros em ordem cronológica…")
        # Read all rows in chronological order
        cur.execute("""
            SELECT feature, input_path, output_path, status, detail, username, created_at
            FROM conversion_log
            ORDER BY datetime(created_at) ASC, id ASC
        """)
        rows = cur.fetchall()

        report(6.0)
        set_status("Preparando tabela temporária…")
        # Build new table (fresh)
        cur.execute("DROP TABLE IF EXISTS conversion_log_new")
        cur.execute(
            """
            CREATE TABLE conversion_log_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature TEXT NOT NULL,
                input_path TEXT,
                output_path TEXT,
                status TEXT NOT NULL,
                detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username TEXT
            );
            """
        )

        report(8.0)
        set_status("Inserindo registros…")
        # Insert sequentially to let AUTOINCREMENT assign 1..N
        ins = """
            INSERT INTO conversion_log_new (feature, input_path, output_path, status, detail, username, created_at)
            VALUES (?,?,?,?,?,?,?)
        """
        # Choose update cadence: every row if small, else around 1% steps
        step = 1 if total <= 200 else max(1, total // 100)
        for i, r in enumerate(rows, start=1):
            cur.execute(ins, r)
            if i % step == 0 or i == total:
                report(8.0 + (i / total) * 90.0)
                if total <= 50:
                    set_status(f"Inserindo {i}/{total}…")

        set_status("Trocando tabela…")
        # Safer swap: keep a backup table until success.
        # 1) Drop previous leftover backup if exists (optional cleanup)
        if _table_exists(cur, 'conversion_log_old'):
            try:
                cur.execute("DROP TABLE conversion_log_old")
            except Exception:
                pass
        # 2) Rename current to backup
        cur.execute("ALTER TABLE conversion_log RENAME TO conversion_log_old")
        # 3) Promote new table
        cur.execute("ALTER TABLE conversion_log_new RENAME TO conversion_log")
        conn.commit()
        # Keep conversion_log_old as a safety net for manual recovery.
        # We won't drop it automatically to avoid data loss on unforeseen issues.

        set_status("Finalizando…")
        report(100.0)
        return True, f"Renumbered {total} log rows.", total


def restore_log_from_backup() -> tuple[bool, str]:
    """Restore conversion_log from conversion_log_old if present.

    Returns (success, message).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        # Ensure backup exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversion_log_old'")
        if not cur.fetchone():
            return False, "No backup table (conversion_log_old) found."
        # Rename current log out of the way and restore backup
        try:
            if _table_exists(cur, 'conversion_log'):
                cur.execute("ALTER TABLE conversion_log RENAME TO conversion_log_new_tmp")
        except Exception:
            # If rename fails, try dropping, but prefer not to drop blindly
            pass
        cur.execute("ALTER TABLE conversion_log_old RENAME TO conversion_log")
        conn.commit()
        return True, "Restored conversion_log from backup."
