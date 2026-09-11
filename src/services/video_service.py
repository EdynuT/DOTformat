"""Communication layer between the GUI and ``models.convert_video``.

Holds no conversion logic of its own -- it calls into the models package and
logs each job's outcome (DB history via ``ConversionService``, console via
``utils.console_log``). Unlike ``image_service``/``services.job_runner``, video
conversion does not need an isolated child process for cancellation: ffmpeg
already runs as a real OS subprocess, so cancelling just means terminating it,
which ``models.convert_video.convert_single`` does itself when it notices
``cancel_event`` -- see that module's docstring. The GUI
(``src.gui.views.video_view``) never imports ``src.models`` directly; this class
is the only door.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from ..models import convert_video
from .conversion_service import ConversionService
from .job_runner import OperationCancelled
from ..utils.console_log import log_error, log_info, log_warning

VIDEO_EXTENSIONS = convert_video.VIDEO_EXTENSIONS
BatchOutcome = convert_video.BatchOutcome


class VideoService:
    def __init__(self) -> None:
        self.conversion_logger = ConversionService()

    def get_video_duration(self, path: str) -> float:
        return convert_video.get_video_duration(path)

    def list_batch_jobs(self, input_dir: str, output_dir: str, output_format: str) -> list[tuple[str, str]]:
        return convert_video.list_batch_jobs(input_dir, output_dir, output_format)

    def convert_single(
        self,
        input_file: str,
        output_file: str,
        output_format: str,
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        username: Optional[str] = None,
    ) -> str:
        log_info(f"Converting video {input_file} -> {output_file}")
        try:
            convert_video.convert_single(
                input_file, output_file, output_format,
                report=on_progress, cancel_event=cancel_event,
            )
        except convert_video.VideoConversionCancelled:
            self._cleanup_partial(output_file)
            log_info("Video conversion cancelled by user")
            raise OperationCancelled()
        except Exception as exc:
            log_error(f"Video conversion failed: {exc}")
            self._cleanup_partial(output_file)
            self._log_history_error("video_convert", input_file, str(exc), username)
            raise

        log_info(f"Video conversion finished: {output_file}")
        self._log_history_success("video_convert", input_file, output_file, username)
        return output_file

    def convert_batch(
        self,
        jobs: list[tuple[str, str]],
        output_format: str,
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        username: Optional[str] = None,
    ) -> convert_video.BatchOutcome:
        if not jobs:
            return convert_video.BatchOutcome(converted=[], errors=[])

        log_info(f"Converting {len(jobs)} video(s) to {output_format.upper()}")
        total = len(jobs)
        converted: list[str] = []
        errors: list[str] = []

        for index, (src, dst) in enumerate(jobs):
            if cancel_event is not None and cancel_event.is_set():
                break
            if on_status:
                on_status(f"{os.path.basename(src)}  ({index + 1}/{total})")

            def _item_progress(pct: float, index=index) -> None:
                if on_progress:
                    on_progress(((index + pct / 100.0) / total) * 100.0)

            try:
                convert_video.convert_single(
                    src, dst, output_format, report=_item_progress, cancel_event=cancel_event,
                )
                converted.append(dst)
                self._log_history_success("video_batch", src, dst, username)
            except convert_video.VideoConversionCancelled:
                self._cleanup_partial(dst)
                break
            except Exception as exc:
                self._cleanup_partial(dst)
                errors.append(f"{os.path.basename(src)}: {exc}")
                self._log_history_error("video_batch", src, str(exc), username)

        if cancel_event is not None and cancel_event.is_set():
            log_info("Video batch conversion cancelled by user")
            raise OperationCancelled()

        log_info(f"Video batch finished: {len(converted)}/{total} converted")
        return convert_video.BatchOutcome(converted=converted, errors=errors)

    # ---- internal helpers ----
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


__all__ = ["VideoService", "BatchOutcome", "VIDEO_EXTENSIONS"]
