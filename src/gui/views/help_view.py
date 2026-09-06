"""Help and Privacy/Terms dialogs."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from datetime import datetime

from ..context import AppContext
from ...utils.user_settings import get_setting, set_setting

PRIVACY_POLICY_URL = "https://github.com/EdynuT/DOTformat/blob/main/PRIVACY_POLICY.md"
TERMS_URL = "https://github.com/EdynuT/DOTformat/blob/main/TERMS.md"


def _open_url(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        try:
            messagebox.showinfo("Info", f"Open this link in your browser:\n{url}")
        except Exception:
            pass


def open_privacy_dialog(ctx: AppContext) -> None:
    win = tk.Toplevel(ctx.root)
    win.title("Privacy & Terms")
    win.geometry("520x500")
    win.resizable(False, False)
    txt = tk.Text(win, wrap='word', height=14, width=64)
    txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))
    summary = (
        "Transparency\n"
        "- Logs are stored locally and can include file paths, feature name, and status.\n"
        "- Audio → Text uses Google Web Speech API; audio chunks are sent to Google only while transcribing.\n"
        "- FFmpeg may be downloaded on demand from a trusted source with your consent.\n\n"
        "Privacy\n"
        "- No telemetry is sent by default.\n"
        "- You can export or delete your logs at any time.\n"
        "- Optional encryption-at-exit can protect the local database.\n\n"
        "Docs\n"
        "- Read the full Privacy Policy and Terms for details."
    )
    txt.insert('1.0', summary)
    txt.config(state='disabled')
    btns = ttk.Frame(win)
    btns.pack(pady=6)
    ttk.Button(btns, text="Open Privacy Policy", command=lambda: _open_url(PRIVACY_POLICY_URL)).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="Open Terms", command=lambda: _open_url(TERMS_URL)).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="Close", command=win.destroy).pack(side=tk.RIGHT, padx=6)


def ensure_privacy_consent_once(ctx: AppContext) -> None:
    """Show the privacy/terms consent dialog once per profile."""
    key = "privacy_consent_v1"
    try:
        ok = get_setting(key)
    except Exception:
        ok = None
    if ok:
        return
    win = tk.Toplevel(ctx.root)
    win.title("Privacy & Terms")
    win.geometry("540x480")
    win.resizable(False, False)
    ttk.Label(win, text="Please review and accept to continue.", font=("Segoe UI", 11, "bold")).pack(pady=(8, 4))
    box = tk.Text(win, wrap='word', height=14, width=66)
    box.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
    box.insert('1.0', (
        "Key points:\n"
        "• Logs are local and may include file paths and status.\n"
        "• Audio → Text sends audio chunks to Google during transcription.\n"
        "• Optional FFmpeg download may occur with your consent.\n"
        "• No telemetry by default; you can export or delete your logs.\n"
    ))
    box.config(state='disabled')
    link_row = ttk.Frame(win)
    link_row.pack(pady=(0, 6))
    ttk.Button(link_row, text="Open Privacy Policy", command=lambda: _open_url(PRIVACY_POLICY_URL)).pack(side=tk.LEFT, padx=6)
    ttk.Button(link_row, text="Open Terms", command=lambda: _open_url(TERMS_URL)).pack(side=tk.LEFT, padx=6)
    btn_row = ttk.Frame(win)
    btn_row.pack(pady=(6, 14))

    def accept():
        try:
            set_setting(key, datetime.now().isoformat())
        except Exception:
            pass
        win.destroy()

    def decline():
        try:
            messagebox.showinfo("Info", "You can close the app if you prefer not to accept.", parent=win)
        except Exception:
            pass

    ttk.Button(btn_row, text="Accept", command=accept, width=14).pack(side=tk.LEFT, padx=10, ipady=4)
    ttk.Button(btn_row, text="Cancel", command=decline, width=14).pack(side=tk.LEFT, padx=10, ipady=4)


def open_help(ctx: AppContext) -> None:
    help_win = tk.Toplevel(ctx.root)
    help_win.title("Help")
    help_win.geometry("420x320")
    help_win.resizable(False, False)
    txt = tk.Text(help_win, wrap='word', height=16, width=56)
    txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    txt.insert('1.0', (
        "DOTformat features:\n"
        "- Convert Images: Change image formats or combine into a PDF.\n\n"
        "- Remove Image Background: Remove background and optionally refine with manual eraser.\n"
        "- PDF Manager: Convert PDF to DOCX/PNG, or add password to a PDF.\n\n"
        "- Audio to Text: Transcribe audio into a .txt file (requires internet for Google).\n\n"
        "- Generate QR Code: Create a QR code image from text/URL.\n\n"
        "- Convert Videos: Convert a video to another format with progress bar.\n\n"
        "Tips:\n"
        "- File dialogs remember your last used folder per feature.\n\n"
        "- Admin can manage users and view logs via Options (☰).\n"
    ))
    txt.config(state='disabled')
    ttk.Button(help_win, text="Close", command=help_win.destroy).pack(pady=(0, 8))


__all__ = ["open_privacy_dialog", "ensure_privacy_consent_once", "open_help"]
