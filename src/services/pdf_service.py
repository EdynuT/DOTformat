"""Communication layer between the GUI and ``models.pdf_manager``.

Holds no PDF-processing logic of its own -- it calls into the models package,
wraps each operation in ``services.job_runner.run_isolated`` so a "Cancelar"
click in the progress window can kill it outright (even mid-``pdf2docx``/
``PyPDF2`` call -- see that module's docstring for why a plain
``threading.Event`` cannot do that on its own), and logs each job's outcome (DB
history via ``ConversionService``, console via ``utils.console_log``). The GUI
(``src.gui.views.pdf_view``) never imports ``src.models`` directly; this class
is the only door.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from ..models import pdf_manager
from .conversion_service import ConversionService
from .job_runner import OperationCancelled, run_isolated
from ..utils.console_log import log_error, log_info, log_warning


class PdfService:
    def __init__(self) -> None:
        self.conversion_logger = ConversionService()

    def is_pdf_protected(self, path: str) -> bool:
        return pdf_manager.is_pdf_protected(path)

    def to_docx(
        self, pdf_file: str, docx_file: str, cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        username: Optional[str] = None,
    ) -> str:
        return self._run_job(
            "pdf_to_docx", pdf_manager.pdf_to_docx_job, (pdf_file, docx_file),
            pdf_file, docx_file, cancel_event, on_progress, on_status, username,
        )

    def to_png(
        self, pdf_file: str, output_dir: str, dpi: int, cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        username: Optional[str] = None,
    ) -> str:
        return self._run_job(
            "pdf_to_png", pdf_manager.pdf_to_png_job, (pdf_file, output_dir, dpi),
            pdf_file, output_dir, cancel_event, on_progress, on_status, username,
        )

    def protect(
        self, input_pdf: str, password: str, output_pdf: str, cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        username: Optional[str] = None,
    ) -> str:
        return self._run_job(
            "pdf_protect", pdf_manager.protect_pdf_job, (input_pdf, password, output_pdf),
            input_pdf, output_pdf, cancel_event, on_progress, on_status, username,
        )

    def copy_without_password(
        self, input_pdf: str, output_pdf: str, cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        username: Optional[str] = None,
    ) -> str:
        return self._run_job(
            "pdf_copy", pdf_manager.copy_pdf_job, (input_pdf, output_pdf),
            input_pdf, output_pdf, cancel_event, on_progress, on_status, username,
        )

    # ---- internal helpers ----
    def _run_job(
        self, feature: str, target, args: tuple, src: Optional[str], dst: str, cancel_event,
        on_progress: Optional[Callable[[float], None]],
        on_status: Optional[Callable[[str], None]],
        username: Optional[str],
    ) -> str:
        log_info(f"{feature}: {src} -> {dst}")
        current_file = {"path": None}

        result = run_isolated(
            target,
            args=args,
            on_progress=on_progress,
            on_status=on_status,
            on_current_file=lambda path: current_file.__setitem__("path", path),
            cancel_event=cancel_event,
        )

        if result.cancelled:
            self._cleanup_partial(current_file["path"])
            log_info(f"{feature} cancelled by user")
            raise OperationCancelled()

        if not result.ok:
            log_error(f"{feature} failed: {result.error}")
            self._log_history_error(feature, src, result.error or "", username)
            raise RuntimeError(result.error or f"{feature} failed")

        log_info(f"{feature} finished: {dst}")
        self._log_history_success(feature, src, dst, username)
        return result.value

    def _cleanup_partial(self, path: Optional[str]) -> None:
        if not path:
            return
        try:
            if os.path.exists(path):
                os.remove(path)
                log_info(f"Removed partial output after cancel: {path}")
        except Exception as exc:
            log_warning(f"Could not remove partial output {path}: {exc}")

    def _log_history_success(self, feature: str, src: Optional[str], dst: str, username: Optional[str]) -> None:
        try:
            self.conversion_logger.log_success(feature, src, dst, username=username)
        except Exception:
            pass

    def _log_history_error(self, feature: str, src: Optional[str], message: str, username: Optional[str]) -> None:
        try:
            self.conversion_logger.log_error(feature, src, message, username=username)
        except Exception:
            pass


__all__ = ["PdfService"]
