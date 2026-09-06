"""Session/master-key lifecycle: current user state and DB encryption at rest.

Extracted from the old gui.py globals so this business logic no longer lives in the UI layer.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from ..db.auth_connection import get_auth_connection
from ..db.connection import init_schema, DB_FILE
from ..utils.db_crypto import decrypt_file, encrypt_file
from ..utils.app_paths import get_encrypted_db_file
from ..utils.envelope_key import load_wrapper_for_user, create_and_store_wrapper, unwrap_k_app


class DatabasePrepareError(Exception):
    """Raised when the encrypted/plaintext database cannot be prepared for a user."""


class SessionService:
    """Holds the logged-in session state and the master-key (K_APP) / DB-encryption lifecycle."""

    #: Toggle automatic at-rest encryption of the main DB when the session ends.
    ENABLE_DB_ENCRYPTION = True

    def __init__(self) -> None:
        self.current_user: Optional[str] = None
        self.current_role: Optional[str] = None
        self._k_app: Optional[bytes] = None
        self._user_plain_password: Optional[str] = None
        self._legacy_decrypted_with_raw: bool = False

    @property
    def k_app(self) -> Optional[bytes]:
        return self._k_app

    def login(self, username: str, role: str, raw_password: str) -> None:
        self.current_user = username
        self.current_role = role
        self._user_plain_password = raw_password

    def logout(self) -> None:
        self.current_user = None
        self.current_role = None
        self._user_plain_password = None
        self._k_app = None
        self._legacy_decrypted_with_raw = False

    def prepare_database(self, username: str, raw_password: str) -> Optional[int]:
        """Prepare auth + main DB decryption/initialization.

        Returns the user id, or raises DatabasePrepareError on failure.
        """
        user_id = None
        try:
            with get_auth_connection() as conn:
                row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
                if row:
                    user_id = row[0]
        except Exception:
            user_id = None
        if user_id is None:
            raise DatabasePrepareError("User not found after login.")

        if self.ENABLE_DB_ENCRYPTION:
            rec = load_wrapper_for_user(user_id)
            if rec:
                try:
                    self._k_app = unwrap_k_app(raw_password, rec)
                except Exception as e:
                    raise DatabasePrepareError(f"Failed to unlock key: {e}") from e
            else:
                self._k_app = None

        try:
            enc_path = get_encrypted_db_file()
            if self.ENABLE_DB_ENCRYPTION:
                if enc_path.exists() and not DB_FILE.exists():
                    decrypt_ok = False
                    errors: list[str] = []
                    if self._k_app is not None:
                        try:
                            decrypt_file(enc_path, self._k_app.hex(), dest=DB_FILE)
                            decrypt_ok = True
                        except Exception as e:
                            errors.append(f"Master key failed: {e}")
                    if not decrypt_ok:
                        try:
                            decrypt_file(enc_path, raw_password, dest=DB_FILE)
                            decrypt_ok = True
                            self._legacy_decrypted_with_raw = True
                        except Exception as e:
                            errors.append(f"Legacy password failed: {e}")
                    if not decrypt_ok:
                        raise DatabasePrepareError("Failed to decrypt database.\n" + "\n".join(errors))
                    if self._k_app is None:
                        try:
                            self._k_app = create_and_store_wrapper(user_id, raw_password)
                        except Exception as e:
                            raise DatabasePrepareError(f"Could not create key wrapper: {e}") from e
                    try:
                        init_schema()
                    except Exception as e:
                        raise DatabasePrepareError(f"Failed migrations: {e}") from e
                elif not enc_path.exists() and not DB_FILE.exists():
                    init_schema()
                    if self._k_app is None:
                        try:
                            self._k_app = create_and_store_wrapper(user_id, raw_password)
                        except Exception:
                            pass
                else:
                    try:
                        init_schema()
                    except Exception as e:
                        raise DatabasePrepareError(f"Failed migrations: {e}") from e
            else:
                init_schema()
        except DatabasePrepareError:
            raise
        except Exception as e:
            raise DatabasePrepareError(f"Failed to prepare database: {e}") from e
        return user_id

    def atomic_encrypt_plaintext_db(self) -> Optional[str]:
        """Encrypt the plaintext DB to the encrypted file atomically.

        Returns a warning message on failure, otherwise None.
        """
        if not (self.ENABLE_DB_ENCRYPTION and DB_FILE.exists()):
            return None
        key_pwd = self._k_app.hex() if self._k_app is not None else self._user_plain_password
        if not key_pwd:
            return None
        enc_target = get_encrypted_db_file()
        tmp_path = enc_target.with_suffix(enc_target.suffix + ".tmp")
        try:
            encrypt_file(Path(DB_FILE), key_pwd, dest=tmp_path, overwrite=True)
            if enc_target.exists():
                try:
                    enc_target.unlink()
                except Exception:
                    pass
            tmp_path.replace(enc_target)
            # Wipe plaintext securely-ish
            try:
                with open(DB_FILE, 'rb+') as f:
                    data = f.read()
                    f.seek(0)
                    f.write(b'\x00' * len(data))
                    f.truncate()
            except Exception:
                pass
            try:
                os.remove(DB_FILE)
            except Exception:
                pass
            return None
        except Exception as e:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            return f"DB encryption failed: {e}. Keeping plaintext for safety."


__all__ = ["SessionService", "DatabasePrepareError"]
