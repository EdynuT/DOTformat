"""Business logic for PDF operations: convert to DOCX/PNG, copy, and password-protect.

Pure logic, no Tkinter -- same rule as the other modules in this package. The
GUI never imports this module directly; ``services.pdf_service.PdfService`` is
the only caller.

Every public function keeps returning ``(bool, str)`` (its existing contract);
the optional ``report``/``set_status``/``set_current_file`` keyword arguments
are for callers that want progress feedback (namely
``services.job_runner.run_isolated``, which always passes all three) and are
no-ops if omitted. The ``*_job`` wrappers translate that tuple contract into a
raise-on-failure one, which is what ``job_runner`` expects from its target.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

import PyPDF2
import pymupdf  # PyMuPDF
from pdf2docx import Converter


def is_pdf_protected(pdf_file: str) -> bool:
    """Best-effort check for whether ``pdf_file`` is already password-protected."""
    try:
        doc = pymupdf.open(pdf_file)
        needs_pass = getattr(doc, 'needs_pass', False)
        try:
            doc.close()
        except Exception:
            pass
        return bool(needs_pass)
    except Exception:
        pass
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        return bool(getattr(reader, 'is_encrypted', False))
    except Exception:
        return True  # cannot open it safely either way -- assume the worst


def pdf_to_docx(
    pdf_file, docx_file, *,
    report: Optional[Callable[[float], None]] = None,
    set_status: Optional[Callable[[str], None]] = None,
    set_current_file: Optional[Callable[[Optional[str]], None]] = None,
):
    """
    Converts a PDF file to a DOCX file.
    """
    if not pdf_file or not docx_file:
        return False, "Missing input PDF or output DOCX path."
    if set_status:
        set_status("Converting PDF to DOCX…")
    if set_current_file:
        set_current_file(docx_file)
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        if report:
            report(100.0)
        return True, f"DOCX file saved successfully at '{docx_file}'!"
    except Exception as e:
        try:
            # Attempt to close converter if partially opened
            cv.close()  # type: ignore
        except Exception:
            pass
        return False, str(e)


def protect_pdf(
    input_pdf, password, output_pdf, *,
    report: Optional[Callable[[float], None]] = None,
    set_status: Optional[Callable[[str], None]] = None,
    set_current_file: Optional[Callable[[Optional[str]], None]] = None,
):
    """
    Protects a PDF file by adding a password provided by the user.
    Parameters:
      - input_pdf (str): Path to the input PDF file.
      - password (str): The password to secure the PDF (must be provided by the user).
      - output_pdf (str): Path where the protected PDF will be saved.
    """
    if not input_pdf or not output_pdf:
        return False, "Missing input or output path."
    if set_status:
        set_status("Protecting PDF…")
    if set_current_file:
        set_current_file(output_pdf)
    try:
        # Early reject: if the PDF is already password-protected, do not proceed here.
        if is_pdf_protected(input_pdf):
            return False, "This PDF is already password-protected. Unlock/remove the password first, then set a new one."

        # Build the protected PDF
        reader = PyPDF2.PdfReader(input_pdf)
        writer = PyPDF2.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        if password:
            writer.encrypt(password)
        with open(output_pdf, "wb") as pdf_out:
            writer.write(pdf_out)
        if report:
            report(100.0)
        return True, f"Protected PDF saved at '{output_pdf}'!"
    except Exception as e:
        return False, str(e)


def pdf_to_png(
    pdf_file, output_dir, dpi: int = 200, *,
    report: Optional[Callable[[float], None]] = None,
    set_status: Optional[Callable[[str], None]] = None,
    set_current_file: Optional[Callable[[Optional[str]], None]] = None,
):
    """
    Converts each page of a PDF file into individual PNG images using PyMuPDF
    (no Poppler required on Windows).

    Args:
        pdf_file (str): Path to the input PDF.
        output_dir (str): Directory where PNG files will be saved.
        dpi (int): Render resolution. 300 DPI is a good default.

    Returns:
        tuple[bool, str]: (success, message)
    """
    if not pdf_file or not output_dir:
        return False, "Missing input PDF or output directory."
    try:
        os.makedirs(output_dir, exist_ok=True)
        # Open PDF; for encrypted PDFs, this will raise unless previously unlocked
        doc = pymupdf.open(pdf_file)
        try:
            zoom = dpi / 72.0  # 72 DPI is the PDF default
            mat = pymupdf.Matrix(zoom, zoom)
            total = max(1, doc.page_count)
            for i in range(doc.page_count):
                output_path = os.path.join(output_dir, f"page_{i + 1}.png")
                if set_status:
                    set_status(f"Page {i + 1}/{doc.page_count}")
                if set_current_file:
                    set_current_file(output_path)
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                pix.save(output_path)
                if set_current_file:
                    set_current_file(None)
                if report:
                    report(((i + 1) / total) * 100.0)
        finally:
            doc.close()
        return True, f"Images successfully saved in '{output_dir}'!"
    except Exception as e:
        return False, str(e)


def copy_pdf(
    input_pdf: str, output_pdf: str, *,
    report: Optional[Callable[[float], None]] = None,
    set_status: Optional[Callable[[str], None]] = None,
    set_current_file: Optional[Callable[[Optional[str]], None]] = None,
):
    """Copies a PDF byte-for-byte (used for the "leave without a password" choice)."""
    if set_status:
        set_status("Saving PDF…")
    if set_current_file:
        set_current_file(output_pdf)
    try:
        with open(input_pdf, "rb") as src, open(output_pdf, "wb") as dst:
            dst.write(src.read())
        if report:
            report(100.0)
        return True, f"PDF saved without password at: {output_pdf}"
    except Exception as e:
        return False, str(e)


def _job(fn, *args, **kwargs):
    """Adapts a ``(bool, str)``-returning function to job_runner's raise-on-failure contract."""
    ok, msg = fn(*args, **kwargs)
    if not ok:
        raise RuntimeError(msg)
    return msg


def pdf_to_docx_job(pdf_file, docx_file, *, report=None, set_status=None, set_current_file=None):
    return _job(pdf_to_docx, pdf_file, docx_file, report=report, set_status=set_status, set_current_file=set_current_file)


def pdf_to_png_job(pdf_file, output_dir, dpi, *, report=None, set_status=None, set_current_file=None):
    return _job(pdf_to_png, pdf_file, output_dir, dpi, report=report, set_status=set_status, set_current_file=set_current_file)


def protect_pdf_job(input_pdf, password, output_pdf, *, report=None, set_status=None, set_current_file=None):
    return _job(protect_pdf, input_pdf, password, output_pdf, report=report, set_status=set_status, set_current_file=set_current_file)


def copy_pdf_job(input_pdf, output_pdf, *, report=None, set_status=None, set_current_file=None):
    return _job(copy_pdf, input_pdf, output_pdf, report=report, set_status=set_status, set_current_file=set_current_file)


__all__ = [
    "is_pdf_protected",
    "pdf_to_docx",
    "protect_pdf",
    "pdf_to_png",
    "copy_pdf",
    "pdf_to_docx_job",
    "pdf_to_png_job",
    "protect_pdf_job",
    "copy_pdf_job",
]
