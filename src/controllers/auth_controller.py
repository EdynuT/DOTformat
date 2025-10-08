"""Tkinter-based authentication dialog (login / first-time registration)."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from ..db.auth_connection import get_auth_connection
from ..services.user_service import UserService
from pathlib import Path
from ..db.connection import DB_FILE


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
        win.geometry("340x235")
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

        def switch_mode():
            # After first user exists, no register mode
            if not first_time:
                return
            # Only one possible transition: register -> (unused) login (should not happen before submit)
            # Keep for completeness but effectively disabled by not exposing button.
            if mode_var.get() == "login":
                mode_var.set("register")
            else:
                mode_var.set("login")
            lbl_mode.config(text=("Register" if mode_var.get()=="register" else "Login"))
            render_confirm()

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
                if self.service.authenticate(username, password):
                    self.username = username
                    self._password_plain = password  # store raw temporarily for encryption use
                    self._role = self.service.get_role(username) or 'user'
                    self._set_last_user(username)
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Invalid credentials", parent=win)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=4, column=0, columnspan=2, pady=8, sticky="ew")
        ttk.Button(btn_row, text="Submit", command=submit).pack(side=tk.LEFT)
        if first_time:
            # Only show a disabled-looking hint label or skip toggle entirely; simpler: skip toggle.
            pass

        parent.wait_window(win)
        if self.username:
            return self.username, getattr(self, '_password_plain', ''), getattr(self, '_role', 'user')
        return None

__all__ = ["AuthController"]
