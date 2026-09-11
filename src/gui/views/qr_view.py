"""QR code generation view: owns the dialogs; all business logic lives in
``services.qr_service.QrService`` (reached via ``ctx.qr_service``).
"""
from __future__ import annotations
from os.path import dirname
from tkinter import filedialog, messagebox, simpledialog

from ..context import AppContext
from ..widgets.progress import run_with_progress
from ...utils.user_settings import get_setting, set_setting


def qr_code_action(ctx: AppContext) -> None:
    """Generate QR code from text or URL."""
    service = ctx.qr_service

    text = simpledialog.askstring("Input Text", "Enter text or URL to generate a QR Code:")
    if text is None:
        return
    if not text.strip():
        messagebox.showwarning("Warning", "No text or URL provided.")
        return
    save_path = filedialog.asksaveasfilename(title="Save QR Code as", defaultextension=".png", initialdir=(get_setting("last_dir_qr") or ""), filetypes=[["PNG Image", "*.png"]])
    if not save_path:
        return
    try:
        set_setting("last_dir_qr", dirname(save_path))
    except Exception:
        pass

    try:
        msg = run_with_progress(
            ctx.root, "Generating QR Code",
            lambda _report: service.generate(text, save_path, username=ctx.current_user),
            auto=True,
        )
        messagebox.showinfo("Success", msg)
    except Exception as e:
        messagebox.showerror("Error", str(e))


__all__ = ["qr_code_action"]
