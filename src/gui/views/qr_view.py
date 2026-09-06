"""QR code generation view."""
from __future__ import annotations
from os.path import dirname
from tkinter import filedialog, messagebox, simpledialog

from ..context import AppContext
from ..widgets.progress import run_with_progress
from ...models.qrcode_generator import generate_qr_code
from ...utils.user_settings import get_setting, set_setting


def qr_code_action(ctx: AppContext) -> None:
    """Generate QR code from text or URL."""
    root = ctx.root
    conversion_service = ctx.conversion_service

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
        success, msg = run_with_progress(root, "Generating QR Code", lambda _: generate_qr_code(text, save_path), auto=True)
        if success:
            conversion_service.log_success("qr_code", None, save_path, username=ctx.current_user)
            messagebox.showinfo("Success", msg)
        else:
            conversion_service.log_error("qr_code", None, msg, username=ctx.current_user)
            messagebox.showerror("Error", msg)
    except Exception as e:
        conversion_service.log_error("qr_code", None, str(e), username=ctx.current_user)
        messagebox.showerror("Error", f"Unexpected error: {e}")


__all__ = ["qr_code_action"]
