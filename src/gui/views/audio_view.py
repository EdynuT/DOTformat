"""Audio-to-text transcription view."""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..context import AppContext
from ..widgets.progress import run_with_progress
from ...models.audio_to_text import convert_audio_to_text, SUPPORTED_EXTENSIONS
from ...utils.user_settings import get_setting, set_setting


def _ask_language(parent) -> str | None:
    win = tk.Toplevel(parent)
    win.title("Select the audio language")
    win.geometry("340x150")
    win.resizable(False, False)
    win.grab_set()
    ttk.Label(win, text="Select the audio language").pack(pady=(12, 6))
    frm = ttk.Frame(win)
    frm.pack(pady=4)
    # Common languages; codes must be BCP-47
    langs = [
        'de-DE', 'en-GB', 'en-US', 'es-ES', 'es-MX',
        'fr-FR', 'it-IT', 'ja-JP', 'ko-KR', 'pt-BR', 'pt-PT', 'ru-RU'
    ]
    saved = get_setting("stt_lang") or 'pt-BR'
    var = tk.StringVar(value=saved if saved in langs else 'pt-BR')
    cb = ttk.Combobox(frm, textvariable=var, values=langs, state='readonly', width=24)
    cb.grid(row=0, column=0, padx=6)
    btns = ttk.Frame(win)
    btns.pack(pady=10)
    sel = {"val": None}

    def ok():
        sel["val"] = var.get()
        try:
            set_setting("stt_lang", sel["val"])
        except Exception:
            pass
        win.destroy()

    def cancel():
        win.destroy()

    ttk.Button(btns, text="OK", command=ok).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=6)
    win.wait_window()
    return sel["val"]


def audio_to_text_action(ctx: AppContext) -> None:
    """Transcribe selected audio file to text file."""
    root = ctx.root
    conversion_service = ctx.conversion_service

    lang = _ask_language(root)
    if not lang:
        return

    # Build a filter string from SUPPORTED_EXTENSIONS to keep GUI and backend in sync
    patterns = ";".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
    audio_file = filedialog.askopenfilename(
        title="Select the audio file",
        initialdir=(get_setting("last_dir_audio") or ""),
        filetypes=[("Audio Files", patterns), ("All Files", "*.*")]
    )
    if not audio_file:
        return
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    default_text_name = f"{base_name}.txt"
    set_setting("last_dir_audio", os.path.dirname(audio_file))
    text_file = filedialog.asksaveasfilename(title="Save transcription as", defaultextension=".txt", initialfile=default_text_name, initialdir=(get_setting("last_dir_audio") or ""), filetypes=[("Text File", "*.txt")])
    if not text_file:
        return
    try:
        success, msg = run_with_progress(
            root,
            "Transcribing audio",
            lambda report: convert_audio_to_text(audio_file, text_file, lang, progress=report),
            auto=False
        )
        if success:
            conversion_service.log_success("audio_to_text", audio_file, text_file, username=ctx.current_user)
            messagebox.showinfo("Success", msg)
        else:
            conversion_service.log_error("audio_to_text", audio_file, msg, username=ctx.current_user)
            messagebox.showerror("Error", msg)
    except Exception as e:
        conversion_service.log_error("audio_to_text", audio_file, str(e), username=ctx.current_user)
        messagebox.showerror("Error", f"Unexpected error: {e}")


__all__ = ["audio_to_text_action"]
