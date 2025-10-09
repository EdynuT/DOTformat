"""Automatic backup and basic restore for SQLite databases.

Backups are stored outside the main DOTformat data directory to avoid coupling.
On Windows: %LOCALAPPDATA%/DOTformatBackups/YYYYmmdd_HHMMSS/{auth.db,dotformat.db,dotformat.db.dotf}
"""
from __future__ import annotations
from pathlib import Path
import os
import shutil
from datetime import datetime
import sqlite3

try:
    from platformdirs import user_data_dir  # type: ignore
except Exception:  # pragma: no cover
    user_data_dir = None  # type: ignore

from .app_paths import get_db_file, get_auth_db_file, get_encrypted_db_file

def _backup_base_dir() -> Path:
    # Prefer a sibling app-data-like folder named DOTformatBackups
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
        return (base / 'DOTformatBackups')
    # Other OSes: use platformdirs with a distinct app name
    if user_data_dir:
        return Path(user_data_dir('DOTformatBackups', 'DOTformat'))
    return Path.home() / '.local' / 'share' / 'DOTformatBackups'

def backup_databases() -> None:
    base = _backup_base_dir()
    dst_root = base / datetime.now().strftime('%Y%m%d_%H%M%S')
    dst_root.mkdir(parents=True, exist_ok=True)
    for p in (get_auth_db_file(), get_db_file(), get_encrypted_db_file()):
        try:
            if p.exists():
                shutil.copy2(p, dst_root / p.name)
        except Exception:
            # Best-effort backup; ignore failures
            pass
    # Retention: keep only the latest 2 backups (delete older ones)
    try:
        folders = []
        if base.exists():
            for child in base.iterdir():
                if child.is_dir():
                    try:
                        ts = datetime.strptime(child.name, '%Y%m%d_%H%M%S')
                        folders.append((ts, child))
                    except Exception:
                        continue
        folders.sort(key=lambda t: t[0], reverse=True)
        for _, old in folders[2:]:
            try:
                shutil.rmtree(old, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass

def _is_sqlite_ok(p: Path) -> bool:
    try:
        if not p.exists():
            return False
        conn = sqlite3.connect(p)
        try:
            cur = conn.execute('PRAGMA quick_check;')
            row = cur.fetchone()
            return bool(row and row[0] == 'ok')
        finally:
            conn.close()
    except Exception:
        return False

def _latest_backup_for(name: str) -> Path | None:
    root = _backup_base_dir()
    if not root.exists():
        return None
    candidates: list[tuple[datetime, Path]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            # Expect timestamp-named directories
            datetime.strptime(child.name, '%Y%m%d_%H%M%S')
            candidate = child / name
            if candidate.exists():
                # Use dir mtime as proxy for recency
                candidates.append((datetime.fromtimestamp(child.stat().st_mtime), candidate))
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]

def try_restore_if_missing_or_corrupt() -> None:
    # Restore auth.db if missing or corrupt
    for target in (get_auth_db_file(), get_db_file()):
        try:
            ok = _is_sqlite_ok(target)
        except Exception:
            ok = False
        if ok:
            continue
        # Attempt restore from latest backup for this filename
        src = _latest_backup_for(target.name)
        if src and src.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
            except Exception:
                # If restore fails, we leave creation to init_schema/init_auth_schema
                pass

__all__ = ['backup_databases', 'try_restore_if_missing_or_corrupt']
