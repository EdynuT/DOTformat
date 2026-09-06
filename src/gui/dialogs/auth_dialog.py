"""Tkinter authentication dialog (login / first-time registration).

Business rules (lockout policy, last-user persistence) live in
`services.auth_service.AuthService`; this module only renders the dialog.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from ...services.auth_service import AuthService, LOCKOUT_DURATION_SECONDS
from ...services.user_service import UserService


class AuthDialog:
    def __init__(self) -> None:
        self.service = UserService()
        self.auth_service = AuthService()
        self.username: str | None = None

    def prompt(self, parent: tk.Tk) -> tuple[str, str, str] | None:
        """Open modal dialog. Returns (username, raw_password, role) if authenticated."""
        win = tk.Toplevel(parent)
        win.title("Authentication")
        win.geometry("330x200")
        win.resizable(False, True)
        win.transient(parent)
        win.grab_set()

        mode_var = tk.StringVar(value="login")
        last_user = self.auth_service.get_last_user()
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
                lbl_confirm.grid_remove()
                ent_confirm.grid_remove()
        render_confirm()

        ttk.Label(frm, text=("Register" if first_time else "Login"),
                  font=("Segoe UI", 11, "bold"), foreground="#1a4c7a").grid(row=3, column=0, columnspan=2, pady=(8, 4))

        def submit():
            username = ent_user.get().strip()
            password = ent_pwd.get()
            if not username or not password:
                messagebox.showwarning("Warning", "Fill all fields", parent=win)
                return
            if mode_var.get() == "register":
                # Prevent registering a new user while the main DB is still encrypted (no plaintext open yet)
                # because we cannot generate a wrapper for this new user without first unwrapping K_APP.
                if self.auth_service.encrypted_db_present_without_plain():
                    messagebox.showerror(
                        "Error",
                        "The encrypted database already exists.\n"
                        "First, log in with an existing user to unlock it.\n"
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
                    self.auth_service.set_last_user(username)
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Registration failed (user exists?)", parent=win)
            else:
                # Check lockout before authenticating
                locked, remain = self.auth_service.check_lockout(username)
                if locked:
                    messagebox.showerror("Locked Out", f"Too many failed attempts. Try again in {remain} seconds.", parent=win)
                    return
                if self.service.authenticate(username, password):
                    self.username = username
                    self._password_plain = password  # store raw temporarily for encryption use
                    self._role = self.service.get_role(username) or 'user'
                    self.auth_service.set_last_user(username)
                    self.auth_service.clear_fail(username)
                    win.destroy()
                else:
                    just_locked, attempts_left = self.auth_service.register_fail(username)
                    if just_locked:
                        messagebox.showerror("Locked Out", f"Too many failed attempts. Try again in {LOCKOUT_DURATION_SECONDS} seconds.", parent=win)
                    else:
                        messagebox.showerror("Error", f"Invalid credentials. Attempts left: {attempts_left}", parent=win)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=4, column=0, columnspan=2, pady=8, sticky="ew")
        ttk.Button(btn_row, text="Submit", command=submit).pack(side=tk.BOTTOM, fill=tk.X, expand=True)
        win.bind("<Return>", lambda e: submit())
        win.bind("<KP_Enter>", lambda e: submit())

        parent.wait_window(win)
        if self.username:
            return self.username, getattr(self, '_password_plain', ''), getattr(self, '_role', 'user')
        return None


__all__ = ["AuthDialog"]
