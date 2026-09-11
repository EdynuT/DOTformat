"""Communication layer between the GUI and ``models.audio_to_text``.

Holds no transcription logic of its own -- it calls into the models package,
wraps the whole job in ``services.job_runner.run_isolated`` so a "Cancelar"
click in the progress window can kill it outright, and logs the outcome (DB
history via ``ConversionService``, console via ``utils.console_log``).

The per-chunk Google Speech Recognition request
(``speech_recognition.Recognizer.recognize_google``) has no checkpoint to
interrupt mid-call -- it is a single blocking network request -- so, per the
same reasoning as ``image_service``/``background_service``, the whole
transcription runs in an isolated child process rather than relying on a
``threading.Event`` a worker thread could check between chunks. No output file
is written until every chunk has transcribed successfully, so cancelling never
needs to clean up a partial ``text_file``. The GUI
(``src.gui.views.audio_view``) never imports ``src.models`` directly; this
class is the only door.
"""
from __future__ import annotations

from typing import Callable, Optional

from ..models import audio_to_text
from .conversion_service import ConversionService
from .job_runner import OperationCancelled, run_isolated
from ..utils.console_log import log_error, log_info

SUPPORTED_EXTENSIONS = audio_to_text.SUPPORTED_EXTENSIONS


class AudioService:
    SUPPORTED_EXTENSIONS = audio_to_text.SUPPORTED_EXTENSIONS

    def __init__(self) -> None:
        self.conversion_logger = ConversionService()

    def transcribe(
        self,
        audio_file: str,
        text_file: str,
        language: str,
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        username: Optional[str] = None,
    ) -> str:
        log_info(f"Transcribing {audio_file} -> {text_file} ({language})")

        result = run_isolated(
            audio_to_text.convert_audio_to_text_job,
            args=(audio_file, text_file, language),
            on_progress=on_progress,
            on_status=on_status,
            cancel_event=cancel_event,
        )

        if result.cancelled:
            log_info("Audio transcription cancelled by user")
            raise OperationCancelled()

        if not result.ok:
            log_error(f"Audio transcription failed: {result.error}")
            self._log_history_error(audio_file, result.error or "", username)
            raise RuntimeError(result.error or "transcription failed")

        log_info(f"Audio transcription finished: {text_file}")
        self._log_history_success(audio_file, text_file, username)
        return result.value

    # ---- internal helpers ----
    def _log_history_success(self, src: str, dst: str, username: Optional[str]) -> None:
        try:
            self.conversion_logger.log_success("audio_to_text", src, dst, username=username)
        except Exception:
            pass

    def _log_history_error(self, src: str, message: str, username: Optional[str]) -> None:
        try:
            self.conversion_logger.log_error("audio_to_text", src, message, username=username)
        except Exception:
            pass


__all__ = ["AudioService", "SUPPORTED_EXTENSIONS"]
