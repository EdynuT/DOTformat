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
from src.db.auth_connection import init_auth_schema, get_auth_connection
from src.db.connection import init_schema, DB_FILE
from src.controllers.log_controller import LogController
from src.controllers.auth_controller import AuthController
from src.utils.db_crypto import decrypt_file, encrypt_file, CryptoError
from src.utils.app_paths import get_encrypted_db_file
from src.utils.envelope_key import load_wrapper_for_user, create_and_store_wrapper, unwrap_k_app
from src.utils.security import hash_password, verify_password
from src.services.conversion_service import ConversionService
from src.services.user_service import UserService
from src.repositories.user_repository import UserRepository

# Single global service instance for logging
_conversion_service: ConversionService | None = None
current_user: str | None = None
current_role: str | None = None

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

    def show_add_user_dialog() -> None:
        win = tk.Toplevel(root)
        win.title("Create User")
        win.geometry("300x210")
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
                    _conversion_service.log_success("user_create", None, None, username=current_user)
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
            _log("user_password_change")
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
        if uname == current_user and _count_admins()==1 and uro=='admin':
            messagebox.showerror("Error", "Cannot demote the last admin.", parent=parent); return
        if not _prompt_admin_password(parent):
            messagebox.showerror("Error", "Password incorrect", parent=parent); return
        new_role = 'admin' if uro=='user' else 'user'
        with get_auth_connection() as conn:
            conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))
            conn.commit()
        _log("user_role_change")
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
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
            conn.execute("DELETE FROM key_wrappers WHERE user_id=?", (uid,))
            conn.commit()
        _log("user_delete")
        messagebox.showinfo("Success", "User deleted", parent=parent)
        for r in tree.get_children(): tree.delete(r)
        for r in _get_all_users(): tree.insert('', 'end', values=r)

    def open_options():
        opt = tk.Toplevel(root)
        opt.title("Options")
        opt.geometry("270x340") if role == 'admin' else opt.geometry("230x210")
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

        # Admin-only buttons
        if role == 'admin':
            ttk.Button(frm, text="Create User", command=lambda: (opt.destroy(), act_create_user())).pack(fill='x', pady=4)
            ttk.Button(frm, text="View Users", command=lambda: (opt.destroy(), act_view_users())).pack(fill='x', pady=4)
            ttk.Button(frm, text="Log", command=lambda: (opt.destroy(), act_log())).pack(fill='x', pady=4)
            ttk.Separator(frm).pack(fill='x', pady=6)
        # Common buttons
        ttk.Button(frm, text="Change Password", command=lambda: (opt.destroy(), act_change_password())).pack(fill='x', pady=4)
        ttk.Button(frm, text="Log Out", command=lambda: (opt.destroy(), act_logout())).pack(fill='x', pady=8)
        ttk.Button(frm, text="Close", command=opt.destroy).pack(fill='x', pady=4)

    # Corner Options button (top-left)
    options_btn = ttk.Button(root, text='☰', command=open_options)
    options_btn.place(x=4, y=4)

    # Quick startup log check to ensure conversion_log table exists (early surface of issues)
    try:
        _conversion_service.log_success("_startup_check", None, None, username=current_user)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to validate conversion_log table: {e}\nCheck if the file is corrupted.")

def main():
    """Main GUI entry point (initial launch)."""
    global root, _conversion_service, _user_plain_password
    root = tk.Tk()
    if _conversion_service is None:
        _conversion_service = ConversionService()
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