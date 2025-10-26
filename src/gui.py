import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from PIL import ImageTk
import os
import sys
import traceback
from pathlib import Path
from src.models.convert_image import ImageConverter
from src.models.pdf_manager import pdf_to_docx, pdf_to_png, protect_pdf
from src.models.audio_to_text import convert_audio_to_text, SUPPORTED_EXTENSIONS
from src.models.qrcode_generator import generate_qr_code
from src.models.convert_video import convert_video_choice
from src.models.remove_background import remove_background
from src.db.auth_connection import init_auth_schema, get_auth_connection
from src.db.connection import init_schema, DB_FILE
from src.controllers.log_controller import LogController
from src.controllers.auth_controller import AuthController
from src.utils.db_crypto import decrypt_file, encrypt_file, CryptoError
from src.utils.app_paths import get_encrypted_db_file
from src.utils.user_settings import get_setting, set_setting
from src.utils.backup import backup_databases, try_restore_if_missing_or_corrupt
from src.utils.envelope_key import load_wrapper_for_user, create_and_store_wrapper, unwrap_k_app
from src.utils.security import hash_password, verify_password
from src.services.conversion_service import ConversionService
from src.services.user_service import UserService
from src.repositories.user_repository import UserRepository

# Single global service instance for logging
_conversion_service: ConversionService | None = None
current_user: str | None = None
current_role: str | None = None

# Progress runner with a 0–100 determinate bar.
# If auto=True and the worker does not report progress, a gentle auto-increment simulates activity up to ~92%.
def run_with_progress(title: str, work_fn, *, auto: bool = False):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("380x110")
    win.resizable(False, False)
    win.grab_set()
    # Keep the window on top and associated with root so the user always sees it
    try:
        win.transient(root)
        win.lift()
        win.attributes("-topmost", True)
        # Allow the OS to process the raise
        win.update_idletasks()
    except Exception:
        pass
    # Prevent user from closing the window mid-task (avoids returning None)
    win.protocol("WM_DELETE_WINDOW", lambda: None)
    lbl = ttk.Label(win, text=title)
    lbl.pack(pady=(12, 4))
    var = tk.DoubleVar(value=0.0)
    bar = ttk.Progressbar(win, mode='determinate', variable=var, maximum=100, length=320)
    bar.pack(pady=8)

    # Thread-safe reporter
    def report(value: float):
        # Clamp and set 0..100
        v = max(0.0, min(100.0, float(value)))
        try:
            win.after(0, lambda: (var.set(v), bar.update_idletasks()))
        except Exception:
            pass

    result = {'val': None, 'err': None}

    import threading

    # Gentle auto-increment only when auto=True
    auto_running = {'on': auto}
    def _tick():
        if not auto_running['on']:
            return
        try:
            current = var.get()
            if current < 92:
                step = 0.8 if current < 50 else 0.4
                var.set(min(92, current + step))
                bar.update_idletasks()
        except Exception:
            pass
        finally:
            if auto_running['on']:
                win.after(120, _tick)

    if auto:
        # Start ticking shortly after showing, to indicate activity immediately
        win.after(200, _tick)

    def _worker():
        try:
            result['val'] = work_fn(report)
        except Exception as e:
            result['err'] = e
        finally:
            try:
                auto_running['on'] = False
                # Snap to 100% before closing
                win.after(0, lambda: (var.set(100), bar.update_idletasks()))
                win.after(80, lambda: win.destroy())
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()
    # Block until window closes
    root.wait_window(win)
    if result['err']:
        raise result['err']
    return result['val']

# Progress runner (0–100) with an extra live status text line.
# work_fn receives two callbacks: (report_pct: float -> None, set_status: str -> None)
def run_with_progress_status(title: str, work_fn, *, auto: bool = False):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("420x140")
    win.resizable(False, False)
    win.grab_set()
    try:
        win.transient(root)
        win.lift()
        win.attributes("-topmost", True)
        win.update_idletasks()
    except Exception:
        pass

    lbl = ttk.Label(win, text=title)
    lbl.pack(pady=(10, 4))
    var = tk.DoubleVar(value=0.0)
    bar = ttk.Progressbar(win, mode='determinate', variable=var, maximum=100, length=360)
    bar.pack(pady=4)
    status_text = tk.StringVar(value="")
    status_lbl = ttk.Label(win, textvariable=status_text, foreground="#555")
    status_lbl.pack(pady=(2, 8))

    # Thread-safe updaters
    def report(value: float):
        v = max(0.0, min(100.0, float(value)))
        try:
            win.after(0, lambda: (var.set(v), bar.update_idletasks()))
        except Exception:
            pass

    def set_status(msg: str):
        try:
            win.after(0, lambda: (status_text.set(str(msg)), status_lbl.update_idletasks()))
        except Exception:
            pass

    result = {'val': None, 'err': None}
    import threading

    auto_running = {'on': auto}
    def _tick():
        if not auto_running['on']:
            return
        try:
            current = var.get()
            if current < 92:
                step = 0.8 if current < 50 else 0.4
                var.set(min(92, current + step))
                bar.update_idletasks()
        except Exception:
            pass
        finally:
            if auto_running['on']:
                win.after(200, _tick)

    if auto:
        win.after(200, _tick)

    def _worker():
        try:
            result['val'] = work_fn(report, set_status)
        except Exception as e:
            result['err'] = e
        finally:
            try:
                auto_running['on'] = False
                win.after(0, lambda: (var.set(100), bar.update_idletasks()))
                win.after(80, lambda: win.destroy())
            except Exception:
                pass

    # Prevent user from closing mid-task
    win.protocol("WM_DELETE_WINDOW", lambda: None)
    threading.Thread(target=_worker, daemon=True).start()
    root.wait_window(win)
    if result['err']:
        raise result['err']
    return result['val']

# Run a known number of steps (each step increments evenly to 100)
def run_steps(title: str, steps_total: int, work_fn):
    steps_total = max(1, int(steps_total))
    def _runner(report):
        done = {'n': 0}
        def inc(n: int = 1):
            done['n'] += n
            pct = (done['n'] / steps_total) * 100.0
            report(pct)
        return work_fn(inc)
    return run_with_progress(title, _runner, auto=False)

def pdf_manager_action():
    """
    Opens a window with options for PDF management: convert to DOCX, convert to PNG, or add password.
    This function is called when the user clicks the "PDF Manager" button in the main menu.
    """
    # Create a new modal window for PDF options
    pdf_win = tk.Toplevel(root)
    pdf_win.title("PDF Manager")
    pdf_win.geometry("320x240")
    pdf_win.resizable(False, False)
    pdf_win.grab_set()  # Makes this window modal (blocks interaction with the main window)

    def to_docx():
        pdf_win.lift()
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            # User cancelled; do nothing.
            return
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        default_docx_name = f"{base_name}.docx"
        if pdf_file:
            set_setting("last_dir_pdf", os.path.dirname(pdf_file))
        docx_file = filedialog.asksaveasfilename(title="Save DOCX as", defaultextension=".docx", initialfile=default_docx_name, initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("DOCX File", "*.docx")])
        if not docx_file:
            # User cancelled; do nothing.
            return
        try:
            success, msg = run_with_progress(
                "Converting PDF to DOCX",
                lambda _ : pdf_to_docx(pdf_file, docx_file),
                auto=True
            )
            if success:
                _conversion_service.log_success("pdf_to_docx", pdf_file, docx_file, username=current_user)
                messagebox.showinfo("Success", msg, parent=pdf_win)
            else:
                _conversion_service.log_error("pdf_to_docx", pdf_file, msg, username=current_user)
                messagebox.showerror("Error", msg, parent=pdf_win)
        except Exception as e:
            _conversion_service.log_error("pdf_to_docx", pdf_file, str(e), username=current_user)
            messagebox.showerror("Error", f"Unexpected error: {e}", parent=pdf_win)

    def to_png():
        pdf_win.lift()
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        if pdf_file:
            set_setting("last_dir_pdf", os.path.dirname(pdf_file))
        output_dir = filedialog.asksaveasfilename(title="Select the directory to save images", initialdir=(get_setting("last_dir_pdf") or ""))
        if not output_dir:
            return
        # Ask for image quality (DPI) before conversion
        def ask_dpi(parent) -> int | None:
            win = tk.Toplevel(parent)
            win.title("Select image quality")
            win.geometry("420x200")
            win.resizable(False, False)
            win.grab_set()

            ttk.Label(win, text="Select the image quality").pack(pady=(10, 6))

            frm = ttk.Frame(win)
            frm.pack(pady=4)

            initial = 0
            try:
                saved = int(get_setting("last_pdf_png_dpi") or 0)
                initial = saved if 100 <= saved <= 500 else 0
            except Exception:
                initial = 0
            if initial == 0:
                initial = 300  # recommended default

            allowed = [100, 200, 300, 400, 500]
            var = tk.IntVar(value=initial)
            state = {"up": False}
            scale_ref = {"w": None}

            def nearest_tick(x: float) -> int:
                return min(allowed, key=lambda a: abs(a - x))

            # Text variable for the label so we don't reference the label before it's created
            lbl_text = tk.StringVar(value=f"{initial} DPI")

            def set_value(v: int):
                v = nearest_tick(v)
                var.set(v)
                lbl_text.set(f"{v} DPI")
                # Update the slider position without causing recursive callbacks
                w = scale_ref["w"]
                if w is not None:
                    state["up"] = True
                    try:
                        w.set(v)
                    finally:
                        state["up"] = False

            def on_change(s: str):
                if state["up"]:
                    return
                try:
                    x = float(s)
                except Exception:
                    x = float(var.get())
                set_value(int(round(x)))

            def dec():
                idx = allowed.index(var.get())
                set_value(allowed[(idx - 1) % len(allowed)])

            def inc():
                idx = allowed.index(var.get())
                set_value(allowed[(idx + 1) % len(allowed)])

            ttk.Button(frm, text="-", width=3, command=dec).grid(row=0, column=0, padx=(0,6))
            scale = ttk.Scale(frm, from_=100, to=500, orient='horizontal', length=260,
                               command=on_change)
            scale_ref["w"] = scale
            set_value(initial)
            scale.grid(row=0, column=1)
            ttk.Button(frm, text="+", width=3, command=inc).grid(row=0, column=2, padx=(6,0))

            lbl_val = ttk.Label(win, textvariable=lbl_text)
            lbl_val.pack(pady=(6,2))
            ttk.Label(win, text="Recommended: 300 DPI", foreground="#008000").pack()

            selected = {"val": None}
            btns = ttk.Frame(win); btns.pack(pady=10)
            def ok():
                v = var.get()
                selected["val"] = v
                try:
                    set_setting("last_pdf_png_dpi", v)
                except Exception:
                    pass
                win.destroy()
            def cancel():
                win.destroy()
            ttk.Button(btns, text="OK", command=ok).pack(side=tk.LEFT, padx=6)
            ttk.Button(btns, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=6)

            win.wait_window()
            return selected["val"]

        dpi = ask_dpi(pdf_win)
        if dpi is None:
            return
        try:
            success, msg = run_with_progress(
                "Exporting pages as PNG",
                lambda _ : pdf_to_png(pdf_file, output_dir, dpi),
                auto=True
            )
            if success:
                _conversion_service.log_success("pdf_to_png", pdf_file, output_dir, username=current_user)
                messagebox.showinfo("Success", msg, parent=pdf_win)
            else:
                _conversion_service.log_error("pdf_to_png", pdf_file, msg, username=current_user)
                messagebox.showerror("Error", msg, parent=pdf_win)
        except Exception as e:
            _conversion_service.log_error("pdf_to_png", pdf_file, str(e), username=current_user)
            messagebox.showerror("Error", f"Unexpected error: {e}", parent=pdf_win)

    def add_password():
        pdf_win.lift()
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        password = simpledialog.askstring("PDF Password", "Enter a password for the PDF (leave blank for no password):", show='*', parent=pdf_win)
        if password is None:
            return
        if pdf_file:
            set_setting("last_dir_pdf", os.path.dirname(pdf_file))
        output_pdf = filedialog.asksaveasfilename(title="Save protected PDF as", defaultextension=".pdf", initialfile="protected.pdf", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf")])
        if not output_pdf:
            return
        if password == "":
            try:
                def _copy(_):
                    with open(pdf_file, "rb") as src, open(output_pdf, "wb") as dst:
                        dst.write(src.read())
                    return True, f"PDF saved without password at: {output_pdf}"
                success, msg = run_with_progress("Saving PDF", _copy, auto=True)
                if success:
                    _conversion_service.log_success("pdf_copy", pdf_file, output_pdf, username=current_user)
                    messagebox.showinfo("Success", msg, parent=pdf_win)
                else:
                    _conversion_service.log_error("pdf_copy", pdf_file, msg, username=current_user)
                    messagebox.showerror("Error", msg, parent=pdf_win)
            except Exception as e:
                _conversion_service.log_error("pdf_copy", pdf_file, str(e), username=current_user)
                messagebox.showerror("Error", f"Failed to save PDF: {e}", parent=pdf_win)
        else:
            try:
                def _prot(_):
                    protect_pdf(pdf_file, password, output_pdf)
                    return True, f"Protected PDF saved at: {output_pdf}"
                success, msg = run_with_progress("Protecting PDF", _prot, auto=True)
                if success:
                    _conversion_service.log_success("pdf_protect", pdf_file, output_pdf, username=current_user)
                    messagebox.showinfo("Success", msg, parent=pdf_win)
                else:
                    _conversion_service.log_error("pdf_protect", pdf_file, msg, username=current_user)
                    messagebox.showerror("Error", msg, parent=pdf_win)
            except Exception as e:
                _conversion_service.log_error("pdf_protect", pdf_file, str(e), username=current_user)
                messagebox.showerror("Error", f"Failed to protect PDF: {e}", parent=pdf_win)

    # Layout for the buttons in the PDF Manager window
    ttk.Label(pdf_win, text="Choose a PDF operation:").pack(pady=10)
    ttk.Button(pdf_win, text="Convert PDF to DOCX", command=to_docx).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Convert PDF to PNG", command=to_png).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Add Password to PDF", command=add_password).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Close", command=pdf_win.destroy).pack(fill="x", padx=30, pady=10)

def audio_to_text_action():
    """Transcribe selected audio file to text file."""
    # Ask for language first
    def ask_language(parent) -> str | None:
        win = tk.Toplevel(parent)
        win.title("Select the audio language")
        win.geometry("340x150")
        win.resizable(False, False)
        win.grab_set()
        ttk.Label(win, text="Select the audio language").pack(pady=(12, 6))
        frm = ttk.Frame(win); frm.pack(pady=4)
        # Common languages; codes must be BCP-47
        langs = [
            'de-DE','en-GB','en-US','es-ES','es-MX',
            'fr-FR','it-IT','ja-JP','ko-KR','pt-BR','pt-PT','ru-RU'
        ]
        saved = get_setting("stt_lang") or 'pt-BR'
        var = tk.StringVar(value=saved if saved in langs else 'pt-BR')
        cb = ttk.Combobox(frm, textvariable=var, values=langs, state='readonly', width=24)
        cb.grid(row=0, column=0, padx=6)
        # Buttons
        btns = ttk.Frame(win); btns.pack(pady=10)
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

    lang = ask_language(root)
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
        # User cancelled; do nothing.
        return
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    default_text_name = f"{base_name}.txt"
    if audio_file:
        set_setting("last_dir_audio", os.path.dirname(audio_file))
    text_file = filedialog.asksaveasfilename(title="Save transcription as", defaultextension=".txt", initialfile=default_text_name, initialdir=(get_setting("last_dir_audio") or ""), filetypes=[("Text File", "*.txt")])
    if not text_file:
        # User cancelled; do nothing.
        return
    try:
        # Use determinate progress driven by chunked transcription
        success, msg = run_with_progress(
            "Transcribing audio",
            lambda report: convert_audio_to_text(audio_file, text_file, lang, progress=report),
            auto=False
        )
        if success:
            _conversion_service.log_success("audio_to_text", audio_file, text_file, username=current_user)
            messagebox.showinfo("Success", msg)
        else:
            _conversion_service.log_error("audio_to_text", audio_file, msg, username=current_user)
            messagebox.showerror("Error", msg)
    except Exception as e:
        _conversion_service.log_error("audio_to_text", audio_file, str(e), username=current_user)
        messagebox.showerror("Error", f"Unexpected error: {e}")

def qr_code_action():
    """Generate QR code from text or URL."""
    text = simpledialog.askstring("Input Text", "Enter text or URL to generate a QR Code:")
    if text is None:
        # User cancelled; do nothing.
        return
    if not text.strip():
        messagebox.showwarning("Warning", "No text or URL provided.")
        return
    save_path = filedialog.asksaveasfilename(title="Save QR Code as", defaultextension=".png", initialdir=(get_setting("last_dir_qr") or ""), filetypes=[["PNG Image", "*.png"]])
    if not save_path:
        # User cancelled; do nothing.
        return
    try:
        # Remember folder for next time
        from os.path import dirname
        set_setting("last_dir_qr", dirname(save_path))
    except Exception:
        pass
    try:
        success, msg = run_with_progress(
            "Generating QR Code",
            lambda _ : generate_qr_code(text, save_path),
            auto=True
        )
        if success:
            _conversion_service.log_success("qr_code", None, save_path, username=current_user)
            messagebox.showinfo("Success", msg)
        else:
            _conversion_service.log_error("qr_code", None, msg, username=current_user)
            messagebox.showerror("Error", msg)
    except Exception as e:
        _conversion_service.log_error("qr_code", None, str(e), username=current_user)
        messagebox.showerror("Error", f"Unexpected error: {e}")

def batch_video_conversion(output_format):
    """Batch convert videos in a folder."""
    input_dir = filedialog.askdirectory(title="Select the folder with videos to convert", initialdir=(get_setting("last_dir_video") or ""))
    if not input_dir:
        # User cancelled; do nothing.
        return
    if input_dir:
        set_setting("last_dir_video", input_dir)
    output_dir = filedialog.askdirectory(title="Select the directory to save converted videos", initialdir=(get_setting("last_dir_video_out") or get_setting("last_dir_video") or ""))
    if not output_dir:
        # User cancelled; do nothing.
        return
    video_extensions = ('.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp4', '.mpeg', '.mpg', '.dav')
    if output_dir:
        set_setting("last_dir_video_out", output_dir)
    videos = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_extensions)]
    if not videos:
        messagebox.showwarning("Warning", "No videos found in the folder.")
        return
    # Run batch with step-based progress
    from src.models.convert_video import convert_video_file
    def _do_batch(step):
        results = []
        for video_file in videos:
            base_name = os.path.splitext(os.path.basename(video_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}_converted.{output_format}")
            try:
                ok, msg = convert_video_file(video_file, output_file, output_format)
                if ok:
                    _conversion_service.log_success("video_batch", video_file, output_file, username=current_user)
                    results.append(f"{os.path.basename(video_file)}: Success")
                else:
                    _conversion_service.log_error("video_batch", video_file, msg, username=current_user)
                    results.append(f"{os.path.basename(video_file)}: Error")
            except Exception as e:
                _conversion_service.log_error("video_batch", video_file, str(e), username=current_user)
                results.append(f"{os.path.basename(video_file)}: Exception")
            finally:
                step(1)
        return "\n".join(results)

    summary = run_steps("Batch video conversion", len(videos), _do_batch)
    messagebox.showinfo("Conversion Completed", summary)

def video_conversion_action():
    """
    Creates a pop-up window that lets the user choose between:
      - Single video conversion (which will lead to a format-choice dialog), or
      - Batch video conversion, where the user can select the desired output format (MP4, AVI, or MOV)
    """
    # Create a new window for the video conversion options
    conv_win = tk.Toplevel(root)
    conv_win.title("Select Video Conversion Type")
    conv_win.geometry("300x300")
    conv_win.resizable(False, False)
    conv_win.grab_set()  # Make the window modal

    # Label for conversion type
    lbl = ttk.Label(conv_win, text="Choose conversion type:")
    lbl.pack(pady=10)

    # Radio buttons for choosing conversion type: single or batch
    conv_type = tk.StringVar(value="single")
    rb_single = ttk.Radiobutton(conv_win, text="Single Video Conversion", variable=conv_type, value="single")
    rb_single.pack(anchor="w", padx=20)
    rb_batch = ttk.Radiobutton(conv_win, text="Batch Video Conversion", variable=conv_type, value="batch")
    rb_batch.pack(anchor="w", padx=20)

    # For batch conversion, allow the user to choose the output format
    format_var = tk.StringVar(value="mp4")
    lbl_format = ttk.Label(conv_win, text="Select output format for batch conversion:")
    lbl_format.pack(pady=10)
    rb_mp4 = ttk.Radiobutton(conv_win, text="MP4", variable=format_var, value="mp4")
    rb_mp4.pack(anchor="w", padx=40)
    rb_avi = ttk.Radiobutton(conv_win, text="AVI", variable=format_var, value="avi")
    rb_avi.pack(anchor="w", padx=40)
    rb_mov = ttk.Radiobutton(conv_win, text="MOV", variable=format_var, value="mov")
    rb_mov.pack(anchor="w", padx=40)

    def confirm():
        # Destroy the conversion window and proceed with the selected conversion type
        conv_win.destroy()
        if conv_type.get() == "single":
            # Pass the selected format to convert_video_choice
            convert_video_choice(root, format_var.get())
        else:
            batch_video_conversion(format_var.get())

    btn_confirm = ttk.Button(conv_win, text="Confirm", command=confirm)
    btn_confirm.pack(pady=10)
    
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

DEV_FRESH_START = False  # False: preserve DB between runs (enable real login flow)
# Toggle automatic encryption on exit. True: encrypt DB file when application closes.
ENABLE_DB_ENCRYPTION = True

# Holds the master key (K_APP) plaintext during the session (bytes) and user password for fallback wrappers
_k_app: bytes | None = None
_user_plain_password: str | None = None
_legacy_decrypted_with_raw: bool = False  # Force re-encryption with K_APP if legacy raw password used

def _prepare_database(username: str, raw_password: str) -> int | None:
    """Prepare auth + main DB decryption/initialization. Returns user_id or None on failure."""
    global _k_app, _legacy_decrypted_with_raw
    # Resolve user id
    user_id = None
    try:
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT id FROM users WHERE username=?", (username,))
            row = cur.fetchone()
            if row:
                user_id = row[0]
    except Exception:
        user_id = None
    if user_id is None:
        messagebox.showerror("Error", "User not found after login.")
        return None

    # Load / prepare wrapper first
    if ENABLE_DB_ENCRYPTION:
        rec = load_wrapper_for_user(user_id)
        if rec:
            try:
                _k_app = unwrap_k_app(raw_password, rec)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to unlock key: {e}")
                return None
        else:
            _k_app = None

    try:
        enc_path = get_encrypted_db_file()
        if ENABLE_DB_ENCRYPTION:
            if enc_path.exists() and not DB_FILE.exists():
                decrypt_ok = False; errors: list[str] = []
                if _k_app is not None:
                    try:
                        decrypt_file(enc_path, _k_app.hex(), dest=DB_FILE)
                        decrypt_ok = True
                    except Exception as e:
                        errors.append(f"Master key failed: {e}")
                if not decrypt_ok:
                    try:
                        decrypt_file(enc_path, raw_password, dest=DB_FILE)
                        decrypt_ok = True; _legacy_decrypted_with_raw = True
                    except Exception as e:
                        errors.append(f"Legacy password failed: {e}")
                if not decrypt_ok:
                    messagebox.showerror("Error", "Failed to decrypt database.\n" + "\n".join(errors))
                    return None
                if _k_app is None:
                    try:
                        _k_app = create_and_store_wrapper(user_id, raw_password)
                    except Exception as e:
                        messagebox.showwarning("Warning", f"Could not create key wrapper: {e}")
                try: init_schema()
                except Exception as e:
                    messagebox.showwarning("Warning", f"Failed migrations: {e}")
            elif not enc_path.exists() and not DB_FILE.exists():
                init_schema()
                if _k_app is None:
                    try: _k_app = create_and_store_wrapper(user_id, raw_password)
                    except Exception: pass
            else:
                try: init_schema()
                except Exception as e:
                    messagebox.showwarning("Warning", f"Failed migrations: {e}")
        else:
            init_schema()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to prepare database: {e}")
        return None
    return user_id

def _atomic_encrypt_plaintext_db():
    """Encrypt plaintext DB to encrypted file atomically; only delete plaintext after success."""
    if not (ENABLE_DB_ENCRYPTION and DB_FILE.exists()):
        return
    key_pwd = _k_app.hex() if _k_app is not None else _user_plain_password
    if not key_pwd:
        return
    enc_target = get_encrypted_db_file()
    tmp_path = enc_target.with_suffix(enc_target.suffix + ".tmp")
    try:
        encrypt_file(Path(DB_FILE), key_pwd, dest=tmp_path, overwrite=True)
        # Replace target
        if enc_target.exists():
            try: enc_target.unlink()
            except Exception: pass
        tmp_path.replace(enc_target)
        # Wipe plaintext securely-ish
        try:
            with open(DB_FILE, 'rb+') as f:
                data = f.read(); f.seek(0); f.write(b'\x00'*len(data)); f.truncate()
        except Exception: pass
        try: os.remove(DB_FILE)
        except Exception: pass
    except Exception as e:
        messagebox.showwarning("Warning", f"DB encryption failed: {e}. Keeping plaintext for safety.")
        try:
            if tmp_path.exists(): tmp_path.unlink()
        except Exception: pass

def perform_logout():
    """In-memory logout: encrypt DB, clear UI, prompt login again and rebuild."""
    global current_user, current_role, _user_plain_password
    _atomic_encrypt_plaintext_db()
    current_user = None; current_role = None; _user_plain_password = None
    # Destroy all children of root (except maybe hidden ones)
    for w in list(root.winfo_children()):
        try: w.destroy()
        except Exception: pass
    auth = AuthController()
    login_result = auth.prompt(root)
    if not login_result:
        root.destroy(); return
    username, raw_password, role = login_result
    _user_plain_password = raw_password
    uid = _prepare_database(username, raw_password)
    if uid is None:
        root.destroy(); return
    build_app_ui(username, role, raw_password, uid)

def build_app_ui(username: str, role: str, raw_password: str, user_id: int):
    """Builds the main application UI for a logged user."""
    global current_user, current_role
    current_user = username
    current_role = role
    log_controller = LogController()
    root.title("DOTformat")
    root.resizable(False, False)

    # Set up the style/theme of the application
    style = ttk.Style()
    style.theme_use('clam')

    # Use resource_path to locate the image
    image_path = resource_path('images/image.png')
    if not os.path.exists(image_path):
        messagebox.showerror("Error", f"Image not found: {image_path}")
        return

    from PIL import Image
    image = Image.open(image_path)
    photo = ImageTk.PhotoImage(image)

    # Header frame to display the image
    header_frame = ttk.Frame(root)
    header_frame.pack(pady=10)
    image_label = ttk.Label(header_frame, image=photo)
    image_label.image = photo  # Retain a reference to the image to avoid garbage collection
    image_label.pack()

    # Main frame for action buttons
    mainframe = ttk.Frame(root, padding="10 10 10 10")
    mainframe.pack(fill=tk.BOTH, expand=True)

    # Instantiate the ImageConverter class
    image_converter = ImageConverter(root)

    # Create and grid all buttons for the different conversion actions
    def wrap_image_convert():
        try:
            image_converter.convert_image()
            _conversion_service.log_success("image_convert", None, None, username=current_user)
        except Exception as e:
            _conversion_service.log_error("image_convert", None, str(e), username=current_user)
            traceback.print_exc()
    btn_convert_image = ttk.Button(mainframe, text="Convert Images", command=wrap_image_convert)
    btn_convert_image.grid(column=0, row=0, pady=5, padx=5, sticky='EW')

    def wrap_remove_bg():
        try:
            remove_background()
            _conversion_service.log_success("remove_background", None, None, username=current_user)
        except Exception as e:
            _conversion_service.log_error("remove_background", None, str(e), username=current_user)
            messagebox.showerror("Error", f"Background removal failed: {e}")
    btn_remove_bg = ttk.Button(mainframe, text="Remove Image Background", command=wrap_remove_bg)
    btn_remove_bg.grid(column=0, row=1, pady=5, padx=5, sticky='EW')

    btn_pdf_manager = ttk.Button(mainframe, text="PDF Manager", command=pdf_manager_action)
    btn_pdf_manager.grid(column=0, row=2, pady=5, padx=5, sticky='EW')

    btn_audio_to_text = ttk.Button(mainframe, text="Audio to Text", command=audio_to_text_action)
    btn_audio_to_text.grid(column=0, row=3, pady=5, padx=5, sticky='EW')

    btn_generate_qr_code = ttk.Button(mainframe, text="Generate QR Code", command=qr_code_action)
    btn_generate_qr_code.grid(column=0, row=4, pady=5, padx=5, sticky='EW')

    btn_video_conversion = ttk.Button(mainframe, text="Convert Videos", command=video_conversion_action)
    btn_video_conversion.grid(column=0, row=5, pady=5, padx=5, sticky='EW')

    # History will be accessible only via Options for admin
    def open_history():
        if role != 'admin':
            messagebox.showerror("Permission Denied", "Only admin can view history.")
            return
        log_controller.open_window(root)

    # ------------------------------
    # Privacy & Terms helpers
    # ------------------------------
    import webbrowser

    def _open_url(url: str):
        try:
            webbrowser.open(url)
        except Exception:
            try:
                messagebox.showinfo("Info", f"Open this link in your browser:\n{url}")
            except Exception:
                pass

    def open_privacy_dialog():
        win = tk.Toplevel(root)
        win.title("Privacy & Terms")
        win.geometry("520x360")
        win.resizable(False, False)
        txt = tk.Text(win, wrap='word', height=14, width=64)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8,4))
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
        btns = ttk.Frame(win); btns.pack(pady=6)
        ttk.Button(btns, text="Open Privacy Policy", command=lambda: _open_url("https://github.com/EdynuT/DOTformat/blob/main/PRIVACY_POLICY.md")).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Open Terms", command=lambda: _open_url("https://github.com/EdynuT/DOTformat/blob/main/TERMS.md")).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Close", command=win.destroy).pack(side=tk.RIGHT, padx=6)

    def _ensure_privacy_consent_once():
        # Show once per profile (persisted in auth user_settings)
        key = "privacy_consent_v1"
        try:
            ok = get_setting(key)
        except Exception:
            ok = None
        if ok:
            return
        win = tk.Toplevel(root)
        win.title("Privacy & Terms")
        win.geometry("560x380")
        win.resizable(False, False)
        ttk.Label(win, text="Please review and accept to continue.", font=("Segoe UI", 11, "bold")).pack(pady=(8,4))
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
        link_row = ttk.Frame(win); link_row.pack(pady=(0,6))
        ttk.Button(link_row, text="Open Privacy Policy", command=lambda: _open_url("https://github.com/EdynuT/DOTformat/blob/main/PRIVACY_POLICY.md")).pack(side=tk.LEFT, padx=6)
        ttk.Button(link_row, text="Open Terms", command=lambda: _open_url("https://github.com/EdynuT/DOTformat/blob/main/TERMS.md")).pack(side=tk.LEFT, padx=6)
        btn_row = ttk.Frame(win); btn_row.pack(pady=6)
        def accept():
            try:
                from datetime import datetime
                set_setting(key, datetime.now().isoformat())
            except Exception:
                pass
            win.destroy()
        def decline():
            try:
                messagebox.showinfo("Info", "You can close the app if you prefer not to accept.", parent=win)
            except Exception:
                pass
        ttk.Button(btn_row, text="Accept", command=accept).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Cancel", command=decline).pack(side=tk.LEFT, padx=6)


    def show_add_user_dialog() -> None:
        win = tk.Toplevel(root)
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
            u = ent_u.get().strip(); p = ent_p.get(); c = ent_c.get()
            if not u or not p:
                messagebox.showwarning("Warn", "Fill all fields", parent=win); return
            if len(p) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters", parent=win); return
            if p != c:
                messagebox.showerror("Error", "Passwords do not match", parent=win); return
            svc = UserService()
            if svc.repo.find_by_username(u):
                messagebox.showerror("Error", "Username exists", parent=win); return
            if svc.register(u, p):
                if ENABLE_DB_ENCRYPTION and _k_app is not None:
                    try:
                        with get_auth_connection() as conn:
                            cur = conn.execute("SELECT id FROM users WHERE username=?", (u,))
                            row = cur.fetchone()
                            if row:
                                create_and_store_wrapper(row[0], p, k_app=_k_app)
                    except Exception as e:
                        messagebox.showwarning("Warning", f"User created but key wrapper failed: {e}", parent=win)
                try:
                    # Detailed log: who created which user
                    with get_auth_connection() as conn:
                        actor = conn.execute("SELECT id, username FROM users WHERE username=?", (current_user,)).fetchone()
                        target = conn.execute("SELECT id, username FROM users WHERE username=?", (u,)).fetchone()
                    if actor and target:
                        detail = f"{actor[1]} (ID: {actor[0]}) created user {target[1]} (ID: {target[0]})"
                    else:
                        detail = f"User created: {u}"
                    _conversion_service.log_success("user_create", None, None, username=current_user, detail=detail[:500])
                except Exception:
                    pass
                messagebox.showinfo("Success", "User added.", parent=win)
                win.destroy()
            else:
                messagebox.showerror("Error", "Failed to create user", parent=win)

        ttk.Button(win, text="Create", command=do_create).pack(pady=10)
        ttk.Button(win, text="Close", command=win.destroy).pack()

    # Admin badge
    if role == 'admin':
        badge = ttk.Label(header_frame, text='ADMIN', foreground='white', background='#000000', padding=(6,2))
        badge.place(relx=1.0, rely=0.0, anchor='ne')

    # Ensure the main frame expands properly
    mainframe.columnconfigure(0, weight=1)

    def on_close():
        try:
            backup_databases()
        except Exception:
            pass
        _atomic_encrypt_plaintext_db()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # ------------------------------------------------------------
    # Options dialog (admin/user)
    # ------------------------------------------------------------
    # ------------------------------------------------------------
    # User / Admin management helpers
    # ------------------------------------------------------------
    user_repo = UserRepository()

    def _first_admin_id():
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1")
            row = cur.fetchone(); return row[0] if row else None

    def _count_admins():
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT COUNT(1) FROM users WHERE role='admin'")
            (c,) = cur.fetchone(); return c

    def _get_all_users():
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id ASC")
            return cur.fetchall()

    def _log(feature: str, detail: str | None = None):
        try:
            _conversion_service.log_success(feature, None, None, username=current_user)
        except Exception:
            pass

    def _prompt_admin_password(parent) -> bool:
        pwd = simpledialog.askstring("Admin Password", "Enter admin password:", show='*', parent=parent)
        if not pwd:
            return False
        with get_auth_connection() as conn:
            cur = conn.execute("SELECT password_hash FROM users WHERE username=?", (current_user,))
            row = cur.fetchone()
            if not row:
                return False
            return verify_password(pwd, row[0])

    def change_password_dialog():
        cp = tk.Toplevel(root)
        cp.title("Change Password")
        cp.geometry("300x220")
        cp.resizable(False, False)
        cp.grab_set()
        f = ttk.Frame(cp, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Current:").grid(row=0,column=0,sticky='w'); cur_e = ttk.Entry(f, show='*'); cur_e.grid(row=0,column=1,pady=4)
        ttk.Label(f, text="New:").grid(row=1,column=0,sticky='w'); new_e = ttk.Entry(f, show='*'); new_e.grid(row=1,column=1,pady=4)
        ttk.Label(f, text="Confirm:").grid(row=2,column=0,sticky='w'); conf_e = ttk.Entry(f, show='*'); conf_e.grid(row=2,column=1,pady=4)

        def do_change():
            cur_p = cur_e.get(); n1 = new_e.get(); n2 = conf_e.get()
            if not cur_p or not n1:
                messagebox.showwarning("Warn", "Fill fields", parent=cp); return
            if len(n1) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters", parent=cp); return
            if n1 != n2:
                messagebox.showerror("Error", "Passwords do not match", parent=cp); return
            with get_auth_connection() as conn:
                row = conn.execute("SELECT id, password_hash FROM users WHERE username=?", (current_user,)).fetchone()
                if not row:
                    messagebox.showerror("Error", "User not found", parent=cp); return
                uid, stored = row
                if not verify_password(cur_p, stored):
                    messagebox.showerror("Error", "Current password incorrect", parent=cp); return
                new_hash = hash_password(n1)
                conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, uid))
                if ENABLE_DB_ENCRYPTION and _k_app is not None:
                    conn.execute("DELETE FROM key_wrappers WHERE user_id=?", (uid,))
                    conn.commit()
                    try:
                        create_and_store_wrapper(uid, n1, k_app=_k_app)
                    except Exception as e:
                        messagebox.showwarning("Warning", f"Password changed but key wrapper failed: {e}", parent=cp)
                conn.commit()
            try:
                with get_auth_connection() as conn:
                    actor = conn.execute("SELECT id, username FROM users WHERE username=?", (current_user,)).fetchone()
                if actor:
                    detail = f"{actor[1]} (ID: {actor[0]}) changed own password"
                else:
                    detail = "Password changed"
                _conversion_service.log_success("user_password_change", None, None, username=current_user, detail=detail[:500])
            except Exception:
                pass
            messagebox.showinfo("Success", "Password updated", parent=cp)
            cp.destroy()

        ttk.Button(f, text="Change", command=do_change).grid(row=3,column=0,pady=10)
        ttk.Button(f, text="Close", command=cp.destroy).grid(row=3,column=1,pady=10)

    def view_users_dialog():
        if role != 'admin':
            return
        vu = tk.Toplevel(root)
        vu.title("Users")
        vu.geometry("500x320")
        vu.resizable(False, False)
        frm = ttk.Frame(vu, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)
        cols = ("id","username","role","created")
        tree = ttk.Treeview(frm, columns=cols, show='headings', height=11)
        meta = {"id":"ID","username":"Name","role":"Role","created":"Created"}
        for c,t in meta.items():
            tree.heading(c, text=t)
            w = 50 if c=='id' else 130 if c!='created' else 150
            tree.column(c, width=w, anchor='w')
        tree.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(6,0))
        ttk.Button(btns, text="Change Role", command=lambda: change_role(tree, vu)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Delete User", command=lambda: delete_user(tree, vu)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Close", command=vu.destroy).pack(side=tk.RIGHT, padx=4)

        def refresh():
            for r in tree.get_children(): tree.delete(r)
            for r in _get_all_users(): tree.insert('', 'end', values=r)
        refresh()

    def change_role(tree: ttk.Treeview, parent):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Warn", "Select a user", parent=parent); return
        item = tree.item(sel[0])
        uid, uname, uro, _ = item['values']
        first_admin = _first_admin_id()
        if uid == first_admin:
            messagebox.showinfo("Info", "Cannot change the base admin.", parent=parent); return
        # Block changing own role to avoid accidental lockouts and conflicts
        if uname == current_user:
            messagebox.showerror("Error", "You cannot change your own role.", parent=parent); return
        if uname == current_user and _count_admins()==1 and uro=='admin':
            messagebox.showerror("Error", "Cannot demote the last admin.", parent=parent); return
        if not _prompt_admin_password(parent):
            messagebox.showerror("Error", "Password incorrect", parent=parent); return
        new_role = 'admin' if uro=='user' else 'user'
        with get_auth_connection() as conn:
            actor = conn.execute("SELECT id, username FROM users WHERE username=?", (current_user,)).fetchone()
            target = conn.execute("SELECT id, username FROM users WHERE id=?", (uid,)).fetchone()
            conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))
            conn.commit()
        try:
            if actor and target:
                detail = f"{actor[1]} (ID: {actor[0]}) changed role of {target[1]} (ID: {target[0]}) to {new_role}"
            else:
                detail = f"Role updated to {new_role} for user ID {uid}"
            _conversion_service.log_success("user_role_change", None, None, username=current_user, detail=detail[:500])
        except Exception:
            pass
        messagebox.showinfo("Success", f"Role updated to {new_role}", parent=parent)
        for r in tree.get_children(): tree.delete(r)
        for r in _get_all_users(): tree.insert('', 'end', values=r)

    def delete_user(tree: ttk.Treeview, parent):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Warn", "Select a user", parent=parent); return
        item = tree.item(sel[0])
        uid, uname, uro, _ = item['values']
        first_admin = _first_admin_id()
        if uid == first_admin:
            messagebox.showinfo("Info", "Cannot delete the base admin.", parent=parent); return
        if uname == current_user:
            messagebox.showerror("Error", "Cannot delete the logged in user.", parent=parent); return
        if uro=='admin' and _count_admins()==1:
            messagebox.showerror("Error", "Cannot delete the last admin.", parent=parent); return
        if not messagebox.askyesno("Confirm", f"Delete user '{uname}'?", parent=parent):
            return
        if not _prompt_admin_password(parent):
            messagebox.showerror("Error", "Password incorrect", parent=parent); return
        with get_auth_connection() as conn:
            actor = conn.execute("SELECT id, username FROM users WHERE username=?", (current_user,)).fetchone()
            target = conn.execute("SELECT id, username FROM users WHERE id=?", (uid,)).fetchone()
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
            conn.execute("DELETE FROM key_wrappers WHERE user_id=?", (uid,))
            conn.commit()
        try:
            if actor and target:
                detail = f"{actor[1]} (ID: {actor[0]}) deleted user {target[1]} (ID: {target[0]})"
            else:
                detail = f"Deleted user ID {uid}"
            _conversion_service.log_success("user_delete", None, None, username=current_user, detail=detail[:500])
        except Exception:
            pass
        messagebox.showinfo("Success", "User deleted", parent=parent)
        for r in tree.get_children(): tree.delete(r)
        for r in _get_all_users(): tree.insert('', 'end', values=r)

    def open_options():
        opt = tk.Toplevel(root)
        opt.title("Options")
        # Slightly taller to host privacy buttons
        opt.geometry("290x340") if role == 'admin' else opt.geometry("260x300")
        opt.resizable(False, False)
        # Removed grab_set to avoid modal blocking

        frm = ttk.Frame(opt, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        def wrap(f):
            def _w():
                try:
                    f()
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=opt)
            return _w
        # Action handlers (scoped inside options)
        def act_create_user():
            show_add_user_dialog()

        def act_view_users():
            view_users_dialog()

        def act_log():
            open_history()

        def act_change_password():
            change_password_dialog()

        def act_logout():
            try:
                _conversion_service.log_success("logout", None, None, username=current_user)
            except Exception:
                pass
            opt.destroy()
            perform_logout()

        def act_privacy():
            open_privacy_dialog()


        # Admin-only buttons
        if role == 'admin':
            ttk.Button(frm, text="Create User", command=lambda: (opt.destroy(), act_create_user())).pack(fill='x', pady=4)
            ttk.Button(frm, text="View Users", command=lambda: (opt.destroy(), act_view_users())).pack(fill='x', pady=4)
            ttk.Button(frm, text="Log", command=lambda: (opt.destroy(), act_log())).pack(fill='x', pady=4)
            ttk.Separator(frm).pack(fill='x', pady=6)
        # Common buttons
        ttk.Button(frm, text="Privacy & Terms", command=lambda: (opt.destroy(), act_privacy())).pack(fill='x', pady=4)
        ttk.Button(frm, text="Change Password", command=lambda: (opt.destroy(), act_change_password())).pack(fill='x', pady=4)
        ttk.Button(frm, text="Log Out", command=lambda: (opt.destroy(), act_logout())).pack(fill='x', pady=8)
        ttk.Button(frm, text="Close", command=opt.destroy).pack(fill='x', pady=4)

    # Corner Options button (top-left)
    options_btn = ttk.Button(root, text='☰', command=open_options)
    options_btn.place(x=4, y=4)

    # Help icon (bottom-right) showing brief feature descriptions
    def open_help():
        help_win = tk.Toplevel(root)
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
        ttk.Button(help_win, text="Close", command=help_win.destroy).pack(pady=(0,8))

    help_btn = ttk.Button(root, text='?', width=3, command=open_help)
    help_btn.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor='se')

    # Quick startup log check to ensure conversion_log table exists (early surface of issues)
    try:
        _conversion_service.log_success("_startup_check", None, None, username=current_user)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to validate conversion_log table: {e}\nCheck if the file is corrupted.")
    # Ensure first-run consent
    try:
        _ensure_privacy_consent_once()
    except Exception:
        pass

def main():
    """Main GUI entry point (initial launch)."""
    global root, _conversion_service, _user_plain_password
    root = tk.Tk()
    if _conversion_service is None:
        _conversion_service = ConversionService()
    # Attempt to restore databases if missing/corrupted
    try:
        try_restore_if_missing_or_corrupt()
    except Exception:
        pass
    if DEV_FRESH_START:
        try:
            if DB_FILE.exists(): DB_FILE.unlink()
            enc_candidate = get_encrypted_db_file()
            if enc_candidate.exists(): enc_candidate.unlink()
        except Exception: pass
    init_auth_schema()
    auth = AuthController(); login_result = auth.prompt(root)
    if not login_result:
        root.destroy(); return
    username, raw_password, role = login_result
    _user_plain_password = raw_password
    uid = _prepare_database(username, raw_password)
    if uid is None:
        root.destroy(); return
    build_app_ui(username, role, raw_password, uid)
    root.mainloop()
    