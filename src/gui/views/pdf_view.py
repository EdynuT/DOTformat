"""PDF Manager view: convert to DOCX/PNG, or add a password to a PDF."""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from ..context import AppContext
from ..widgets.progress import run_with_progress
from ...models.pdf_manager import pdf_to_docx, pdf_to_png, protect_pdf
from ...utils.user_settings import get_setting, set_setting


def _ask_dpi(parent) -> int | None:
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

    lbl_text = tk.StringVar(value=f"{initial} DPI")

    def set_value(v: int):
        v = nearest_tick(v)
        var.set(v)
        lbl_text.set(f"{v} DPI")
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

    ttk.Button(frm, text="-", width=3, command=dec).grid(row=0, column=0, padx=(0, 6))
    scale = ttk.Scale(frm, from_=100, to=500, orient='horizontal', length=260, command=on_change)
    scale_ref["w"] = scale
    set_value(initial)
    scale.grid(row=0, column=1)
    ttk.Button(frm, text="+", width=3, command=inc).grid(row=0, column=2, padx=(6, 0))

    ttk.Label(win, textvariable=lbl_text).pack(pady=(6, 2))
    ttk.Label(win, text="Recommended: 300 DPI", foreground="#008000").pack()

    selected = {"val": None}
    btns = ttk.Frame(win)
    btns.pack(pady=10)

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


def pdf_manager_action(ctx: AppContext) -> None:
    """Opens a window with options for PDF management: convert to DOCX, convert to PNG, or add password."""
    root = ctx.root
    conversion_service = ctx.conversion_service
    pdf_win = tk.Toplevel(root)
    pdf_win.title("PDF Manager")
    pdf_win.geometry("320x240")
    pdf_win.resizable(False, False)
    pdf_win.grab_set()

    def to_docx():
        pdf_win.lift()
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        default_docx_name = f"{base_name}.docx"
        set_setting("last_dir_pdf", os.path.dirname(pdf_file))
        docx_file = filedialog.asksaveasfilename(title="Save DOCX as", defaultextension=".docx", initialfile=default_docx_name, initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("DOCX File", "*.docx")])
        if not docx_file:
            return
        try:
            success, msg = run_with_progress(root, "Converting PDF to DOCX", lambda _: pdf_to_docx(pdf_file, docx_file), auto=True)
            if success:
                conversion_service.log_success("pdf_to_docx", pdf_file, docx_file, username=ctx.current_user)
                messagebox.showinfo("Success", msg, parent=pdf_win)
            else:
                conversion_service.log_error("pdf_to_docx", pdf_file, msg, username=ctx.current_user)
                messagebox.showerror("Error", msg, parent=pdf_win)
        except Exception as e:
            conversion_service.log_error("pdf_to_docx", pdf_file, str(e), username=ctx.current_user)
            messagebox.showerror("Error", f"Unexpected error: {e}", parent=pdf_win)

    def to_png():
        pdf_win.lift()
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        set_setting("last_dir_pdf", os.path.dirname(pdf_file))
        output_dir = filedialog.asksaveasfilename(title="Select the directory to save images", initialdir=(get_setting("last_dir_pdf") or ""))
        if not output_dir:
            return
        dpi = _ask_dpi(pdf_win)
        if dpi is None:
            return
        try:
            success, msg = run_with_progress(root, "Exporting pages as PNG", lambda _: pdf_to_png(pdf_file, output_dir, dpi), auto=True)
            if success:
                conversion_service.log_success("pdf_to_png", pdf_file, output_dir, username=ctx.current_user)
                messagebox.showinfo("Success", msg, parent=pdf_win)
            else:
                conversion_service.log_error("pdf_to_png", pdf_file, msg, username=ctx.current_user)
                messagebox.showerror("Error", msg, parent=pdf_win)
        except Exception as e:
            conversion_service.log_error("pdf_to_png", pdf_file, str(e), username=ctx.current_user)
            messagebox.showerror("Error", f"Unexpected error: {e}", parent=pdf_win)

    def add_password():
        pdf_win.lift()
        pdf_file = filedialog.askopenfilename(title="Select the PDF file", initialdir=(get_setting("last_dir_pdf") or ""), filetypes=[("PDF File", "*.pdf"), ("All Files", "*.*")])
        if not pdf_file:
            return
        # Early check: if PDF is already protected, block and return to main UI
        try:
            import fitz  # type: ignore
            try:
                d = fitz.open(pdf_file)
                needs_pass = getattr(d, 'needs_pass', False)
                try:
                    d.close()
                except Exception:
                    pass
            except Exception:
                needs_pass = True
            if needs_pass:
                messagebox.showerror("Protected PDF", "This PDF is already password-protected.", parent=pdf_win)
                pdf_win.destroy()
                return
        except Exception:
            try:
                import PyPDF2  # type: ignore
                r = PyPDF2.PdfReader(pdf_file)
                if getattr(r, 'is_encrypted', False):
                    messagebox.showerror("Protected PDF", "This PDF is already password-protected.", parent=pdf_win)
                    pdf_win.destroy()
                    return
            except Exception:
                messagebox.showerror("Protected PDF", "This PDF appears protected.", parent=pdf_win)
                pdf_win.destroy()
                return
        password = simpledialog.askstring("PDF Password", "Enter a password for the PDF (leave blank for no password):", show='*', parent=pdf_win)
        if password is None:
            return
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
                success, msg = run_with_progress(root, "Saving PDF", _copy, auto=True)
                if success:
                    conversion_service.log_success("pdf_copy", pdf_file, output_pdf, username=ctx.current_user)
                    messagebox.showinfo("Success", msg, parent=pdf_win)
                else:
                    conversion_service.log_error("pdf_copy", pdf_file, msg, username=ctx.current_user)
                    messagebox.showerror("Error", msg, parent=pdf_win)
            except Exception as e:
                conversion_service.log_error("pdf_copy", pdf_file, str(e), username=ctx.current_user)
                messagebox.showerror("Error", f"Failed to save PDF: {e}", parent=pdf_win)
        else:
            try:
                def _prot(_):
                    ok, msg = protect_pdf(pdf_file, password, output_pdf)
                    if not ok:
                        raise RuntimeError(msg)
                    return True, msg
                success, msg = run_with_progress(root, "Protecting PDF", _prot, auto=True)
                if success:
                    conversion_service.log_success("pdf_protect", pdf_file, output_pdf, username=ctx.current_user)
                    messagebox.showinfo("Success", msg, parent=pdf_win)
                else:
                    conversion_service.log_error("pdf_protect", pdf_file, msg, username=ctx.current_user)
                    messagebox.showerror("Error", msg, parent=pdf_win)
            except Exception as e:
                conversion_service.log_error("pdf_protect", pdf_file, str(e), username=ctx.current_user)
                messagebox.showerror("Error", f"Failed to protect PDF: {e}", parent=pdf_win)

    ttk.Label(pdf_win, text="Choose a PDF operation:").pack(pady=10)
    ttk.Button(pdf_win, text="Convert PDF to DOCX", command=to_docx).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Convert PDF to PNG", command=to_png).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Add Password to PDF", command=add_password).pack(fill="x", padx=30, pady=5)
    ttk.Button(pdf_win, text="Close", command=pdf_win.destroy).pack(fill="x", padx=30, pady=10)


__all__ = ["pdf_manager_action"]
