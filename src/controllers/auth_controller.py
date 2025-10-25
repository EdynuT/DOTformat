"""Tkinter-based authentication dialog (login / first-time registration)."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from ..db.auth_connection import get_auth_connection
from ..services.user_service import UserService
from pathlib import Path
from ..db.connection import DB_FILE
import time

# Login lockout policy (edit these values as needed)
# After LOCKOUT_MAX_ATTEMPTS failed logins, the username is locked out for LOCKOUT_DURATION_SECONDS.
LOCKOUT_MAX_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes


def _encrypted_db_present_without_plain() -> bool:
    enc = Path(str(DB_FILE) + '.dotf')
    return enc.exists() and not DB_FILE.exists()

class AuthController:
    def __init__(self) -> None:
        self.service = UserService()
        self.username: str | None = None

    def _get_last_user(self) -> str | None:
        try:
            with get_auth_connection() as conn:
                cur = conn.execute("SELECT value FROM user_settings WHERE key='last_user' LIMIT 1")
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception:
            return None
        return None

    def _set_last_user(self, username: str) -> None:
        try:
            with get_auth_connection() as conn:
                conn.execute("INSERT INTO user_settings(key,value) VALUES('last_user',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (username,))
                conn.commit()
        except Exception:
            pass

    def prompt(self, parent: tk.Tk) -> tuple[str, str, str] | None:
        """Open modal dialog. Returns (username, raw_password, role) if authenticated.

        UI improvements:
        - Prefill username with last logged-in user on login mode.
        - Switch button text shows the target mode ("Register" when in login, "Login" when in register).
        - Clear heading label color differences.
        """
        win = tk.Toplevel(parent)
        win.title("Authentication")
        win.geometry("260x150")
        win.resizable(False, False)
        win.transient(parent)
        win.grab_set()

        mode_var = tk.StringVar(value="login")
        last_user = self._get_last_user()
        first_time = not self.service.has_users()
        if first_time:
            mode_var.set("register")  # Only first run permits registration

        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="w")
        ent_user = ttk.Entry(frm, width=28)
        ent_user.grid(row=0, column=1, pady=4)
        if not first_time and last_user and mode_var.get() == 'login':
            ent_user.insert(0, last_user)

        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="w")
        ent_pwd = ttk.Entry(frm, width=28, show="*")
        ent_pwd.grid(row=1, column=1, pady=4)
        # Focus convenience: if username prefilled, focus password; else focus username
        try:
            if ent_user.get().strip():
                ent_pwd.focus_set()
            else:
                ent_user.focus_set()
        except Exception:
            pass

        lbl_confirm = ttk.Label(frm, text="Confirm:")
        ent_confirm = ttk.Entry(frm, width=28, show="*")
        def render_confirm():
            if mode_var.get() == "register":
                lbl_confirm.grid(row=2, column=0, sticky="w")
                ent_confirm.grid(row=2, column=1, pady=4)
            else:
                # remove if present
                lbl_confirm.grid_remove()
                ent_confirm.grid_remove()
        # initial state
        render_confirm()

        lbl_mode = ttk.Label(frm, text=("Register" if first_time else "Login"), font=("Segoe UI", 11, "bold"), foreground="#1a4c7a")
        lbl_mode.grid(row=3, column=0, columnspan=2, pady=(8,4))

        def _get_kv(key: str) -> str | None:
            try:
                with get_auth_connection() as conn:
                    row = conn.execute("SELECT value FROM user_settings WHERE key=?", (key,)).fetchone()
                    return row[0] if row else None
            except Exception:
                return None

        def _set_kv(key: str, value: str) -> None:
            try:
                with get_auth_connection() as conn:
                    conn.execute(
                        "INSERT INTO user_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, value)
                    )
                    conn.commit()
            except Exception:
                pass

        def _clear_kv(key: str) -> None:
            try:
                with get_auth_connection() as conn:
                    conn.execute("DELETE FROM user_settings WHERE key=?", (key,))
                    conn.commit()
            except Exception:
                pass

        def _check_lockout(u: str) -> tuple[bool, int]:
            """Return (locked, seconds_remaining)."""
            until_s = _get_kv(f"lockout_until:{u}")
            if not until_s:
                return False, 0
            try:
                until = float(until_s)
            except Exception:
                return False, 0
            now = time.time()
            if now < until:
                return True, int(max(1, round(until - now)))
            # Expired; clear
            _clear_kv(f"lockout_until:{u}")
            return False, 0

        def _register_fail(u: str) -> None:
            key = f"login_fail:{u}"
            try:
                n_raw = _get_kv(key)
                n = int(n_raw) if n_raw is not None else 0
            except Exception:
                n = 0
            n += 1
            if n >= LOCKOUT_MAX_ATTEMPTS:
                # Lock the account for configured duration
                _set_kv(f"lockout_until:{u}", str(time.time() + LOCKOUT_DURATION_SECONDS))
                _clear_kv(key)  # reset counter after lockout starts
            else:
                _set_kv(key, str(n))

        def _clear_fail(u: str) -> None:
            _clear_kv(f"login_fail:{u}")
            _clear_kv(f"lockout_until:{u}")

        def submit():
            username = ent_user.get().strip()
            password = ent_pwd.get()
            if not username or not password:
                messagebox.showwarning("Warning", "Fill all fields", parent=win)
                return
            if mode_var.get() == "register":
                # Prevent registering a new user while the main DB is still encrypted (no plaintext open yet)
                # because we cannot generate a wrapper for this new user without first unwrapping K_APP.
                if _encrypted_db_present_without_plain():
                    messagebox.showerror(
                        "Error",
                        "The encrypted database already exists.\n" \
                        "First, log in with an existing user to unlock it.\n" \
                        "Then, within the app, use 'Add User' to create new users.",
                        parent=win
                    )
                    return
                confirm = ent_confirm.get() if ent_confirm else ""
                if len(password) < 6:
                    messagebox.showerror("Error", "Password must be at least 6 characters", parent=win)
                    return
                if password != confirm:
                    messagebox.showerror("Error", "Passwords do not match", parent=win)
                    return
                if self.service.register(username, password):
                    messagebox.showinfo("Success", "User registered. You can use the app now.", parent=win)
                    self.username = username
                    self._password_plain = password  # store raw temporarily for encryption use
                    self._role = self.service.get_role(username) or 'user'
                    self._set_last_user(username)
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Registration failed (user exists?)", parent=win)
            else:
                # Check lockout before authenticating
                locked, remain = _check_lockout(username)
                if locked:
                    messagebox.showerror("Locked Out", f"Too many failed attempts. Try again in {remain} seconds.", parent=win)
                    return
                if self.service.authenticate(username, password):
                    self.username = username
                    self._password_plain = password  # store raw temporarily for encryption use
                    self._role = self.service.get_role(username) or 'user'
                    self._set_last_user(username)
                    _clear_fail(username)
                    win.destroy()
                else:
                    _register_fail(username)
                    # Show feedback and remaining attempts if not yet locked
                    n_raw = _get_kv(f"login_fail:{username}")
                    try:
                        n = int(n_raw) if n_raw is not None else 0
                    except Exception:
                        n = 0
                    if n == 0:  # means lockout just triggered
                        messagebox.showerror("Locked Out", f"Too many failed attempts. Try again in {LOCKOUT_DURATION_SECONDS} seconds.", parent=win)
                    else:
                        left = max(0, LOCKOUT_MAX_ATTEMPTS - n)
                        messagebox.showerror("Error", f"Invalid credentials. Attempts left: {left}", parent=win)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=4, column=0, columnspan=2, pady=8, sticky="ew")
        submit_btn = ttk.Button(btn_row, text="Submit", command=submit)
        submit_btn.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
        # Allow pressing Enter to submit on both login and register screens
        win.bind("<Return>", lambda e: submit())
        win.bind("<KP_Enter>", lambda e: submit())
        if first_time:
            # Only show a disabled-looking hint label or skip toggle entirely; simpler: skip toggle.
            pass

        parent.wait_window(win)
        if self.username:
            return self.username, getattr(self, '_password_plain', ''), getattr(self, '_role', 'user')
        return None

__all__ = ["AuthController"]
