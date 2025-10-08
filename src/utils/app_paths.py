"""Centralized application path resolution.

When packaged as a PyInstaller onefile executable, the working directory is
usually a temp folder, so we store persistent data (SQLite DBs, encrypted
variants) under a per-user application data directory.

On Windows: %LOCALAPPDATA%/DOTformat
On macOS:   ~/Library/Application Support/DOTformat
On Linux:   ~/.local/share/DOTformat

Falls back to the current script directory if platformdirs is unavailable.
"""
from __future__ import annotations
from pathlib import Path
import os

try:
    from platformdirs import user_data_dir  # type: ignore
except Exception:  # pragma: no cover
    user_data_dir = None  # type: ignore

APP_NAME = "DOTformat"
APP_AUTHOR = "DOTformat"  # keep same for simplicity

_CACHE: dict[str, Path] = {}

def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_base_data_dir() -> Path:
    if 'base' in _CACHE:
        return _CACHE['base']
    # Portable override: store beside executable (current working directory) if env set
    if os.environ.get('DOTFORMAT_PORTABLE') == '1':
        base = Path(os.getcwd()) / 'data'
    elif user_data_dir:
        base = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    else:
        # Fallback: alongside running script
        base = Path(os.path.abspath(os.path.dirname(__file__))) / '..' / '..' / 'data'
        base = base.resolve()
    base = _ensure_dir(base)
    _CACHE['base'] = base
    return base

def get_db_file() -> Path:
    return get_base_data_dir() / 'dotformat.db'

def get_auth_db_file() -> Path:
    return get_base_data_dir() / 'auth.db'

def get_encrypted_db_file() -> Path:
    return Path(str(get_db_file()) + '.dotf')

__all__ = [
    'get_base_data_dir', 'get_db_file', 'get_auth_db_file', 'get_encrypted_db_file'
]