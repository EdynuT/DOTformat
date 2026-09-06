"""Main window composition root: wires the feature views together and owns the app lifecycle."""
from __future__ import annotations
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from .context import AppContext
from .dialogs.auth_dialog import AuthDialog
from .views import help_view, options_view
from .views.image_view import convert_image_action
from .views.background_view import remove_background_action
from .views.pdf_view import pdf_manager_action
from .views.audio_view import audio_to_text_action
from .views.qr_view import qr_code_action
from .views.video_view import video_conversion_action
from ..db.auth_connection import init_auth_schema
from ..db.connection import DB_FILE
from ..services.session_service import DatabasePrepareError
from ..utils.app_paths import get_encrypted_db_file
from ..utils.backup import backup_databases, try_restore_if_missing_or_corrupt

DEV_FRESH_START = False  # False: preserve DB between runs (enable real login flow)


def resource_path(relative_path: str) -> str:
    """Get absolute path to a resource: works for dev, PyInstaller, and Nuitka standalone builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # PyInstaller onefile
    elif globals().get("__compiled__"):
        base_path = os.path.dirname(sys.executable)  # Nuitka standalone/onefile
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # src/
    return os.path.join(base_path, relative_path)


def _prepare_database_or_none(ctx: AppContext, username: str, raw_password: str) -> int | None:
    try:
        return ctx.session.prepare_database(username, raw_password)
    except DatabasePrepareError as e:
        messagebox.showerror("Error", str(e))
        return None


def _on_close(ctx: AppContext) -> None:
    try:
        backup_databases()
    except Exception:
        pass
    ctx.session.atomic_encrypt_plaintext_db()
    ctx.root.destroy()


def _perform_logout(ctx: AppContext) -> None:
    """In-memory logout: encrypt DB, clear UI, prompt login again and rebuild."""
    warning = ctx.session.atomic_encrypt_plaintext_db()
    if warning:
        messagebox.showwarning("Warning", warning)
    ctx.session.logout()
    for w in list(ctx.root.winfo_children()):
        try:
            w.destroy()
        except Exception:
            pass
    login_result = AuthDialog().prompt(ctx.root)
    if not login_result:
        ctx.root.destroy()
        return
    username, raw_password, role = login_result
    ctx.session.login(username, role, raw_password)
    if _prepare_database_or_none(ctx, username, raw_password) is None:
        ctx.root.destroy()
        return
    build_app_ui(ctx)


def build_app_ui(ctx: AppContext) -> None:
    """Builds the main application UI for the currently logged-in user."""
    root = ctx.root
    role = ctx.current_role
    root.title("DOTformat")
    root.resizable(False, False)

    style = ttk.Style()
    style.theme_use('clam')

    image_path = resource_path('images/image.png')
    if not os.path.exists(image_path):
        messagebox.showerror("Error", f"Image not found: {image_path}")
        return

    image = Image.open(image_path)
    photo = ImageTk.PhotoImage(image)

    header_frame = ttk.Frame(root)
    header_frame.pack(pady=10)
    image_label = ttk.Label(header_frame, image=photo)
    image_label.image = photo  # Retain a reference to the image to avoid garbage collection
    image_label.pack()

    mainframe = ttk.Frame(root, padding="10 10 10 10")
    mainframe.pack(fill=tk.BOTH, expand=True)

    ttk.Button(mainframe, text="Convert Images", command=lambda: convert_image_action(ctx)).grid(column=0, row=0, pady=5, padx=5, sticky='EW')
    ttk.Button(mainframe, text="Remove Image Background", command=lambda: remove_background_action(ctx)).grid(column=0, row=1, pady=5, padx=5, sticky='EW')
    ttk.Button(mainframe, text="PDF Manager", command=lambda: pdf_manager_action(ctx)).grid(column=0, row=2, pady=5, padx=5, sticky='EW')
    ttk.Button(mainframe, text="Audio to Text", command=lambda: audio_to_text_action(ctx)).grid(column=0, row=3, pady=5, padx=5, sticky='EW')
    ttk.Button(mainframe, text="Generate QR Code", command=lambda: qr_code_action(ctx)).grid(column=0, row=4, pady=5, padx=5, sticky='EW')
    ttk.Button(mainframe, text="Convert Videos", command=lambda: video_conversion_action(ctx)).grid(column=0, row=5, pady=5, padx=5, sticky='EW')

    if role == 'admin':
        badge = ttk.Label(header_frame, text='ADMIN', foreground='white', background='#000000', padding=(6, 2))
        badge.place(relx=1.0, rely=0.0, anchor='ne')

    mainframe.columnconfigure(0, weight=1)

    root.protocol("WM_DELETE_WINDOW", lambda: _on_close(ctx))

    options_btn = ttk.Button(root, text='☰', command=lambda: options_view.open_options(ctx, on_logout=lambda: _perform_logout(ctx)))
    options_btn.place(x=4, y=4)

    help_btn = ttk.Button(root, text='?', width=3, command=lambda: help_view.open_help(ctx))
    help_btn.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor='se')

    # Quick startup log check to ensure conversion_log table exists (early surface of issues)
    try:
        ctx.conversion_service.log_success("_startup_check", None, None, username=ctx.current_user)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to validate conversion_log table: {e}\nCheck if the file is corrupted.")
    # Ensure first-run consent
    try:
        help_view.ensure_privacy_consent_once(ctx)
    except Exception:
        pass


def run() -> None:
    """Main GUI entry point (initial launch)."""
    root = tk.Tk()
    ctx = AppContext(root=root)
    # Attempt to restore databases if missing/corrupted
    try:
        try_restore_if_missing_or_corrupt()
    except Exception:
        pass
    if DEV_FRESH_START:
        try:
            if DB_FILE.exists():
                DB_FILE.unlink()
            enc_candidate = get_encrypted_db_file()
            if enc_candidate.exists():
                enc_candidate.unlink()
        except Exception:
            pass
    init_auth_schema()
    login_result = AuthDialog().prompt(root)
    if not login_result:
        root.destroy()
        return
    username, raw_password, role = login_result
    ctx.session.login(username, role, raw_password)
    if _prepare_database_or_none(ctx, username, raw_password) is None:
        root.destroy()
        return
    build_app_ui(ctx)
    root.mainloop()


__all__ = ["run", "build_app_ui", "resource_path"]
