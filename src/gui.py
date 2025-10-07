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
from src.models.audio_to_text import convert_audio_to_text
from src.models.qrcode_generator import generate_qr_code
from src.models.convert_video import convert_video_choice
from src.models.remove_background import remove_background
from src.db.connection import init_schema, DB_FILE
from src.controllers.log_controller import LogController
from src.services.conversion_service import ConversionService
from src.controllers.auth_controller import AuthController
from src.utils.db_crypto import decrypt_file, encrypt_file, CryptoError
from src.db.auth_connection import init_auth_schema, get_auth_connection
from src.utils.app_paths import get_encrypted_db_file
from src.utils.envelope_key import load_wrapper_for_user, create_and_store_wrapper, unwrap_k_app
from src.services.user_service import UserService
from src.utils.security import hash_password

# Single global service instance for logging
_conversion_service: ConversionService | None = None
current_user: str | None = None

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
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return messagebox.showwarning("Warning", "No PDF file selected.", parent=pdf_win)
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        default_docx_name = f"{base_name}.docx"
        docx_file = filedialog.asksaveasfilename(title="Save DOCX as", defaultextension=".docx", initialfile=default_docx_name, filetypes=[("DOCX File", "*.docx")])
        if not docx_file:
            return messagebox.showwarning("Warning", "No DOCX directory selected.", parent=pdf_win)
        try:
            success, msg = pdf_to_docx(pdf_file, docx_file)
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
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        output_dir = filedialog.askdirectory(title="Select the directory to save images")
        if not output_dir:
            return
        try:
            success, msg = pdf_to_png(pdf_file, output_dir)
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
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        password = simpledialog.askstring("PDF Password", "Enter a password for the PDF (leave blank for no password):", show='*', parent=pdf_win)
        if password is None:
            return
        output_pdf = filedialog.asksaveasfilename(title="Save protected PDF as", defaultextension=".pdf", initialfile="protected.pdf", filetypes=[("PDF File", "*.pdf")])
        if not output_pdf:
            return
        if password == "":
            try:
                with open(pdf_file, "rb") as src, open(output_pdf, "wb") as dst:
                    dst.write(src.read())
                _conversion_service.log_success("pdf_copy", pdf_file, output_pdf, username=current_user)
                messagebox.showinfo("Success", f"PDF saved without password at: {output_pdf}", parent=pdf_win)
            except Exception as e:
                _conversion_service.log_error("pdf_copy", pdf_file, str(e), username=current_user)
                messagebox.showerror("Error", f"Failed to save PDF: {e}", parent=pdf_win)
        else:
            try:
                protect_pdf(pdf_file, password, output_pdf)
                _conversion_service.log_success("pdf_protect", pdf_file, output_pdf, username=current_user)
                messagebox.showinfo("Success", f"Protected PDF saved at: {output_pdf}", parent=pdf_win)
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
    audio_file = filedialog.askopenfilename(title="Select the audio file", filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg;*.aac;*.wma;*.m4a;*.mp4;*.webm;*.avi;*.mov;*.3gp"), ("All Files", "*.*")])
    if not audio_file:
        messagebox.showwarning("Warning", "No file selected.")
        return
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    default_text_name = f"{base_name}.txt"
    text_file = filedialog.asksaveasfilename(title="Save transcription as", defaultextension=".txt", initialfile=default_text_name, filetypes=[("Text File", "*.txt")])
    if not text_file:
        messagebox.showwarning("Warning", "No save location specified.")
        return
    try:
        success, msg = convert_audio_to_text(audio_file, text_file)
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
    if not text:
        messagebox.showwarning("Warning", "No text or URL provided.")
        return
    save_path = filedialog.asksaveasfilename(title="Save QR Code as", defaultextension=".png", filetypes=[("PNG Image", "*.png")])
    if not save_path:
        messagebox.showwarning("Warning", "No save location specified.")
        return
    try:
        success, msg = generate_qr_code(text, save_path)
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
    input_dir = filedialog.askdirectory(title="Select the folder with videos to convert")
    if not input_dir:
        messagebox.showwarning("Warning", "No folder selected.")
        return
    output_dir = filedialog.askdirectory(title="Select the directory to save converted videos")
    if not output_dir:
        messagebox.showwarning("Warning", "No folder selected.")
        return
    video_extensions = ('.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp4', '.mpeg', '.mpg', '.dav')
    videos = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_extensions)]
    if not videos:
        messagebox.showwarning("Warning", "No videos found in the folder.")
        return
    results = []
    for video_file in videos:
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_converted.{output_format}")
        try:
            success, msg = convert_video_choice(video_file, output_file, output_format)
            if success:
                _conversion_service.log_success("video_batch", video_file, output_file, username=current_user)
                results.append(f"{os.path.basename(video_file)}: Success")
            else:
                _conversion_service.log_error("video_batch", video_file, msg, username=current_user)
                results.append(f"{os.path.basename(video_file)}: Error")
        except Exception as e:
            _conversion_service.log_error("video_batch", video_file, str(e), username=current_user)
            results.append(f"{os.path.basename(video_file)}: Exception")
    messagebox.showinfo("Conversion Completed", "\n".join(results))

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

def main():
    """Main GUI entry point."""
    global root, _conversion_service, _user_plain_password, _k_app, _legacy_decrypted_with_raw
    root = tk.Tk()

    if _conversion_service is None:
        _conversion_service = ConversionService()

    if DEV_FRESH_START:
        try:
            if DB_FILE.exists():
                DB_FILE.unlink()
            enc_candidate = get_encrypted_db_file()
            if enc_candidate.exists():
                enc_candidate.unlink()
        except Exception:
            pass

    # Auth schema first (users + wrappers + settings)
    init_auth_schema()

    # Prompt authentication
    auth = AuthController()
    login_result = auth.prompt(root)
    if not login_result:
        root.destroy(); return
    username, raw_password = login_result
    _user_plain_password = raw_password

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
        root.destroy(); return

    # Load / prepare wrapper first
    if ENABLE_DB_ENCRYPTION:
        rec = load_wrapper_for_user(user_id)
        if rec:
            try:
                _k_app = unwrap_k_app(raw_password, rec)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to unlock key: {e}")
                root.destroy(); return
        else:
            _k_app = None  # will create after possible legacy decrypt
    # -----------------------------------------------------------
    # Decrypt or initialize main data database (dotformat.db)
    # -----------------------------------------------------------
    try:
        enc_path = get_encrypted_db_file()

        if ENABLE_DB_ENCRYPTION:
            # Case A: Encrypted file exists and plaintext missing -> need to decrypt
            if enc_path.exists() and not DB_FILE.exists():
                decrypt_ok = False
                errors: list[str] = []
                # 1) Try master key wrapper (preferred)
                if _k_app is not None:
                    try:
                        decrypt_file(enc_path, _k_app.hex(), dest=DB_FILE)
                        decrypt_ok = True
                    except Exception as e:
                        errors.append(f"Master key failed: {e}")
                # 2) Fallback legacy: try raw user password (older versions encrypted with it directly)
                if not decrypt_ok:
                    try:
                        decrypt_file(enc_path, raw_password, dest=DB_FILE)
                        decrypt_ok = True
                        _legacy_decrypted_with_raw = True
                    except Exception as e:
                        errors.append(f"Legacy password failed: {e}")
                if not decrypt_ok:
                    messagebox.showerror("Error", "Failed to decrypt database.\n" + "\n".join(errors))
                    root.destroy(); return
                # If we only had legacy path, create a wrapper now so next run uses K_APP
                if _k_app is None:
                    try:
                        _k_app = create_and_store_wrapper(user_id, raw_password)
                    except Exception as e:
                        messagebox.showwarning("Warning", f"Could not create key wrapper: {e}")
                # Always run migrations/schema after decrypt (ensures new columns)
                try:
                    init_schema()
                except Exception as e:
                    messagebox.showwarning("Warning", f"Failed to apply post-decrypt migrations: {e}")

            # Case B: Neither plaintext nor encrypted file -> brand new DB
            elif not enc_path.exists() and not DB_FILE.exists():
                init_schema()
                # Generate + store a wrapper immediately (fresh install)
                if _k_app is None:
                    try:
                        _k_app = create_and_store_wrapper(user_id, raw_password)
                    except Exception:
                        pass
            else:
                # Plaintext already present (possibly leftover from crash or previous dev session)
                # Ensure schema/migrations are applied
                try:
                    init_schema()
                except Exception as e:
                    messagebox.showwarning("Warning", f"Failed to apply migrations on existing DB: {e}")
        else:
            # Encryption disabled: ensure schema present (create if new)
            init_schema()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to prepare database: {e}")
        root.destroy(); return

    # At this point conversion_log table must exist (init_schema executed in all paths).
    # -----------------------------------------------------------

    # (Future) Use _k_app to decrypt an encrypted data.db variant if we move from file-level to record-level.
    global current_user
    current_user = username
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
    btn_history = ttk.Button(mainframe, text="History", command=lambda: log_controller.open_window(root))
    btn_history.grid(column=0, row=6, pady=8, padx=5, sticky='EW')

    def add_user_action():
        # Modal to create a new user after DB already decrypted
        win = tk.Toplevel(root)
        win.title("Add User")
        win.geometry("300x200")
        win.resizable(False, False)
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
            if p != c:
                messagebox.showerror("Error", "Passwords do not match", parent=win); return
            svc = UserService()
            if svc.repo.find_by_username(u):
                messagebox.showerror("Error", "Username exists", parent=win); return
            if svc.register(u, p):
                # Create wrapper for new user using existing K_APP
                if ENABLE_DB_ENCRYPTION and _k_app is not None:
                    try:
                        # We need the new user's id
                        with get_auth_connection() as conn:
                            cur = conn.execute("SELECT id FROM users WHERE username=?", (u,))
                            row = cur.fetchone()
                            if row:
                                create_and_store_wrapper(row[0], p, k_app=_k_app)
                    except Exception as e:
                        messagebox.showwarning("Warning", f"User created but key wrapper failed: {e}", parent=win)
                messagebox.showinfo("Success", "User added.", parent=win)
                win.destroy()
            else:
                messagebox.showerror("Error", "Failed to create user", parent=win)

        ttk.Button(win, text="Create", command=do_create).pack(pady=10)
        ttk.Button(win, text="Close", command=win.destroy).pack()

    btn_add_user = ttk.Button(mainframe, text="Add User", command=add_user_action)
    btn_add_user.grid(column=0, row=7, pady=8, padx=5, sticky='EW')

    # Ensure the main frame expands properly
    mainframe.columnconfigure(0, weight=1)

    def on_close():
        try:
            if ENABLE_DB_ENCRYPTION and not DEV_FRESH_START and DB_FILE.exists():
                # Always prefer K_APP now; if legacy flag set, ensures re-encryption with K_APP wrapper password
                key_pwd = _k_app.hex() if _k_app is not None else _user_plain_password
                if key_pwd:
                    try:
                        encrypt_file(Path(DB_FILE), key_pwd, dest=get_encrypted_db_file(), overwrite=True)
                        # Wipe plaintext
                        try:
                            with open(DB_FILE, 'rb+') as f:
                                data = f.read(); f.seek(0); f.write(b'\x00'*len(data)); f.truncate()
                        except Exception:
                            pass
                        try:
                            os.remove(DB_FILE)
                        except Exception:
                            pass
                    except Exception:
                        pass
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Quick startup log check to ensure conversion_log table exists (early surface of issues)
    try:
        _conversion_service.log_success("_startup_check", None, None, username=current_user)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to validate conversion_log table: {e}\nCheck if the file is corrupted.")

    # Start the GUI main event loop
    root.mainloop()