"""Options menu: admin user-management dialogs, password change, log out, privacy, history."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable

from ..context import AppContext
from ..dialogs.history_dialog import HistoryDialog
from . import help_view
from ...services.user_service import UserService


def _prompt_admin_password(parent) -> str | None:
    pwd = simpledialog.askstring("Admin Password", "Enter admin password:", show='*', parent=parent)
    return pwd or None


def _show_add_user_dialog(ctx: AppContext, service: UserService) -> None:
    win = tk.Toplevel(ctx.root)
    win.title("Create User")
    win.geometry("300x300")
    win.resizable(False, True)
    win.grab_set()
    ttk.Label(win, text="Username:").pack(pady=4)
    ent_u = ttk.Entry(win)
    ent_u.pack(pady=2)
    ttk.Label(win, text="Password:").pack(pady=4)
    ent_p = ttk.Entry(win, show='*')
    ent_p.pack(pady=2)
    ttk.Label(win, text="Confirm:").pack(pady=4)
    ent_c = ttk.Entry(win, show='*')
    ent_c.pack(pady=2)

    def do_create():
        try:
            user_id = service.create_user_by_admin(ent_u.get(), ent_p.get(), ent_c.get(), k_app=ctx.session.k_app)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=win)
            return
        try:
            detail = f"{ctx.current_user} created user {ent_u.get().strip()} (ID: {user_id})"
            ctx.conversion_service.log_success("user_create", None, None, username=ctx.current_user, detail=detail[:500])
        except Exception:
            pass
        messagebox.showinfo("Success", "User added.", parent=win)
        win.destroy()

    ttk.Button(win, text="Create", command=do_create).pack(pady=10)
    ttk.Button(win, text="Close", command=win.destroy).pack()


def _refresh_users_tree(tree: ttk.Treeview, service: UserService) -> None:
    for r in tree.get_children():
        tree.delete(r)
    for r in service.list_users():
        tree.insert('', 'end', values=r)


def _change_role(ctx: AppContext, tree: ttk.Treeview, parent, service: UserService) -> None:
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Warn", "Select a user", parent=parent)
        return
    uid = tree.item(sel[0])['values'][0]
    pwd = _prompt_admin_password(parent)
    if not pwd:
        messagebox.showerror("Error", "Password incorrect", parent=parent)
        return
    try:
        new_role = service.change_role(ctx.current_user, uid, pwd)
    except (ValueError, PermissionError) as e:
        messagebox.showerror("Error", str(e), parent=parent)
        return
    try:
        detail = f"{ctx.current_user} changed role of user ID {uid} to {new_role}"
        ctx.conversion_service.log_success("user_role_change", None, None, username=ctx.current_user, detail=detail[:500])
    except Exception:
        pass
    messagebox.showinfo("Success", f"Role updated to {new_role}", parent=parent)
    _refresh_users_tree(tree, service)


def _delete_user(ctx: AppContext, tree: ttk.Treeview, parent, service: UserService) -> None:
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Warn", "Select a user", parent=parent)
        return
    item = tree.item(sel[0])
    uid, uname = item['values'][0], item['values'][1]
    if not messagebox.askyesno("Confirm", f"Delete user '{uname}'?", parent=parent):
        return
    pwd = _prompt_admin_password(parent)
    if not pwd:
        messagebox.showerror("Error", "Password incorrect", parent=parent)
        return
    try:
        service.delete_user(ctx.current_user, uid, pwd)
    except (ValueError, PermissionError) as e:
        messagebox.showerror("Error", str(e), parent=parent)
        return
    try:
        detail = f"{ctx.current_user} deleted user {uname} (ID: {uid})"
        ctx.conversion_service.log_success("user_delete", None, None, username=ctx.current_user, detail=detail[:500])
    except Exception:
        pass
    messagebox.showinfo("Success", "User deleted", parent=parent)
    _refresh_users_tree(tree, service)


def _view_users_dialog(ctx: AppContext, service: UserService) -> None:
    if ctx.current_role != 'admin':
        return
    vu = tk.Toplevel(ctx.root)
    vu.title("Users")
    vu.geometry("500x320")
    vu.resizable(False, False)
    frm = ttk.Frame(vu, padding=8)
    frm.pack(fill=tk.BOTH, expand=True)
    cols = ("id", "username", "role", "created")
    tree = ttk.Treeview(frm, columns=cols, show='headings', height=11)
    meta = {"id": "ID", "username": "Name", "role": "Role", "created": "Created"}
    for c, t in meta.items():
        tree.heading(c, text=t)
        w = 50 if c == 'id' else 130 if c != 'created' else 150
        tree.column(c, width=w, anchor='w')
    tree.pack(fill=tk.BOTH, expand=True)

    btns = ttk.Frame(frm)
    btns.pack(fill=tk.X, pady=(6, 0))
    ttk.Button(btns, text="Change Role", command=lambda: _change_role(ctx, tree, vu, service)).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text="Delete User", command=lambda: _delete_user(ctx, tree, vu, service)).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text="Close", command=vu.destroy).pack(side=tk.RIGHT, padx=4)

    _refresh_users_tree(tree, service)


def _change_password_dialog(ctx: AppContext, service: UserService) -> None:
    cp = tk.Toplevel(ctx.root)
    cp.title("Change Password")
    cp.geometry("300x220")
    cp.resizable(False, False)
    cp.grab_set()
    f = ttk.Frame(cp, padding=10)
    f.pack(fill=tk.BOTH, expand=True)
    ttk.Label(f, text="Current:").grid(row=0, column=0, sticky='w')
    cur_e = ttk.Entry(f, show='*')
    cur_e.grid(row=0, column=1, pady=4)
    ttk.Label(f, text="New:").grid(row=1, column=0, sticky='w')
    new_e = ttk.Entry(f, show='*')
    new_e.grid(row=1, column=1, pady=4)
    ttk.Label(f, text="Confirm:").grid(row=2, column=0, sticky='w')
    conf_e = ttk.Entry(f, show='*')
    conf_e.grid(row=2, column=1, pady=4)

    def do_change():
        try:
            service.change_own_password(ctx.current_user, cur_e.get(), new_e.get(), conf_e.get(), k_app=ctx.session.k_app)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=cp)
            return
        try:
            detail = f"{ctx.current_user} changed own password"
            ctx.conversion_service.log_success("user_password_change", None, None, username=ctx.current_user, detail=detail[:500])
        except Exception:
            pass
        messagebox.showinfo("Success", "Password updated", parent=cp)
        cp.destroy()

    ttk.Button(f, text="Change", command=do_change).grid(row=3, column=0, pady=10)
    ttk.Button(f, text="Close", command=cp.destroy).grid(row=3, column=1, pady=10)


def open_options(ctx: AppContext, on_logout: Callable[[], None]) -> None:
    role = ctx.current_role
    service = UserService()
    opt = tk.Toplevel(ctx.root)
    opt.title("Options")
    opt.geometry("290x340") if role == 'admin' else opt.geometry("260x300")
    opt.resizable(False, False)

    frm = ttk.Frame(opt, padding=10)
    frm.pack(fill=tk.BOTH, expand=True)

    def act_logout():
        try:
            ctx.conversion_service.log_success("logout", None, None, username=ctx.current_user)
        except Exception:
            pass
        opt.destroy()
        on_logout()

    def act_log():
        if role != 'admin':
            messagebox.showerror("Permission Denied", "Only admin can view history.")
            return
        HistoryDialog().open_window(ctx.root)

    if role == 'admin':
        ttk.Button(frm, text="Create User", command=lambda: (opt.destroy(), _show_add_user_dialog(ctx, service))).pack(fill='x', pady=4)
        ttk.Button(frm, text="View Users", command=lambda: (opt.destroy(), _view_users_dialog(ctx, service))).pack(fill='x', pady=4)
        ttk.Button(frm, text="Log", command=lambda: (opt.destroy(), act_log())).pack(fill='x', pady=4)
        ttk.Separator(frm).pack(fill='x', pady=6)
    ttk.Button(frm, text="Privacy & Terms", command=lambda: (opt.destroy(), help_view.open_privacy_dialog(ctx))).pack(fill='x', pady=4)
    ttk.Button(frm, text="Change Password", command=lambda: (opt.destroy(), _change_password_dialog(ctx, service))).pack(fill='x', pady=4)
    ttk.Button(frm, text="Log Out", command=act_logout).pack(fill='x', pady=8)
    ttk.Button(frm, text="Close", command=opt.destroy).pack(fill='x', pady=4)


__all__ = ["open_options"]
