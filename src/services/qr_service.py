"""Communication layer between the GUI and ``models.qrcode_generator``.

Holds no generation logic of its own -- it calls into the models package and
logs the outcome (DB history via ``ConversionService``, console via
``utils.console_log``). No cancellation support: generating a QR code is a
single, near-instant in-memory operation with nothing worth interrupting --
unlike the other features, there is no isolated-process or subprocess
machinery here. The GUI (``src.gui.views.qr_view``) never imports
``src.models`` directly; this class is the only door.
"""
from __future__ import annotations

from typing import Optional

from ..models import qrcode_generator
from .conversion_service import ConversionService
from ..utils.console_log import log_error, log_info


class QrService:
    def __init__(self) -> None:
        self.conversion_logger = ConversionService()

    def generate(self, text: str, save_path: str, username: Optional[str] = None) -> str:
        ok, msg = qrcode_generator.generate_qr_code(text, save_path)
        if not ok:
            log_error(f"QR code generation failed: {msg}")
            self._log_history_error(msg, username)
            raise RuntimeError(msg)

        log_info(f"QR code saved at {save_path}")
        self._log_history_success(save_path, username)
        return msg

    # ---- internal helpers ----
    def _log_history_success(self, dst: str, username: Optional[str]) -> None:
        try:
            self.conversion_logger.log_success("qr_code", None, dst, username=username)
        except Exception:
            pass

    def _log_history_error(self, message: str, username: Optional[str]) -> None:
        try:
            self.conversion_logger.log_error("qr_code", None, message, username=username)
        except Exception:
            pass


__all__ = ["QrService"]
