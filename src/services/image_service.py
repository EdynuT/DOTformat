"""Communication layer between the GUI and ``models.convert_image``/``models.svg_converter``.

Holds no conversion logic of its own -- it calls into the models package, wraps
batch calls in ``services.job_runner.run_isolated`` so a "Cancelar" click in the
progress window can kill the operation outright (even mid-``vtracer``/``img2pdf``
call -- see that module's docstring for why a plain ``threading.Event`` cannot do
that on its own), and logs each job's outcome (DB history via
``ConversionService``, console via ``utils.console_log``). The GUI
(``src.gui.views.image_view``) never imports ``src.models`` directly; this class
is the only door.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from ..models import convert_image, svg_converter
from .conversion_service import ConversionService
from .job_runner import OperationCancelled, run_isolated
from ..utils.console_log import log_debug, log_error, log_info, log_warning

OUTPUT_FORMATS = convert_image.OUTPUT_FORMATS
ConvertJob = convert_image.ConvertJob
BatchOutcome = convert_image.BatchOutcome


class ImageService:
    PRESETS = svg_converter.PRESETS
    PRESET_LABELS = svg_converter.PRESET_LABELS
    SUGGESTED_MAX_LONG_EDGE = svg_converter.SUGGESTED_MAX_LONG_EDGE
    HEAVY_SVG_MB = svg_converter.HEAVY_SVG_MB

    def __init__(self) -> None:
        self.conversion_logger = ConversionService()

    # ---- capability checks ----
    def vtracer_available(self) -> bool:
        return svg_converter.vtracer_available()

    def svg_render_available(self) -> bool:
        return svg_converter.svg_render_available()

    # ---- SVG trace options ----
    def preset_options(self, key: str) -> svg_converter.TraceOptions:
        return svg_converter.PRESETS[key]

    def make_trace_options(self, **fields) -> svg_converter.TraceOptions:
        return svg_converter.TraceOptions(**fields)

    # ---- job planning (delegates to models.convert_image) ----
    def plan_jobs(
        self,
        image_files: list[str],
        out_dir: str,
        output_format: str,
        confirm_overwrite: Callable[[str], bool],
    ) -> list[convert_image.ConvertJob]:
        return convert_image.plan_jobs(image_files, out_dir, output_format, confirm_overwrite)

    def biggest_job(self, jobs: list[convert_image.ConvertJob]) -> Optional[convert_image.ConvertJob]:
        return convert_image.biggest_job(jobs)

    def is_large_image(self, path: str) -> bool:
        return svg_converter.is_large_image(path)

    def image_size(self, path: str) -> tuple[int, int]:
        return convert_image.image_size(path)

    def estimate_svg_mb(
        self, path: str, opts: svg_converter.TraceOptions, max_long_edge: Optional[int]
    ) -> float:
        return svg_converter.estimate_svg_mb(path, opts, max_long_edge)

    # ---- batches (orchestration: cancellation + logging around models.convert_image) ----
    def vectorize_batch(
        self,
        jobs: list[convert_image.ConvertJob],
        opts: svg_converter.TraceOptions,
        max_long_edge: Optional[int],
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> convert_image.BatchOutcome:
        if not jobs:
            return convert_image.BatchOutcome(converted=[], errors=[])

        log_info(f"Vectorizing {len(jobs)} image(s) to SVG")
        job_tuples = [(job.src, job.dst) for job in jobs]
        current_file = {"path": None}

        result = run_isolated(
            convert_image.vectorize_batch_job,
            args=(job_tuples, opts, max_long_edge),
            on_progress=on_progress,
            on_status=on_status,
            on_current_file=lambda path: current_file.__setitem__("path", path),
            cancel_event=cancel_event,
        )

        if result.cancelled:
            self._cleanup_partial(current_file["path"])
            log_info("SVG conversion cancelled by user")
            raise OperationCancelled()

        if not result.ok:
            log_error(f"SVG conversion job failed: {result.error}")
            raise RuntimeError(result.error or "vectorization failed")

        converted, errors = result.value
        for src, dst in converted:
            log_debug(f"Vectorized {src} -> {dst}")
            self._log_history_success("image_to_svg", src, dst)
        for message in errors:
            log_warning(f"SVG conversion failed for one file: {message}")
            self._log_history_error("image_to_svg", None, message)

        log_info(f"SVG conversion finished: {len(converted)}/{len(jobs)} converted")
        return convert_image.BatchOutcome(converted=[dst for _, dst in converted], errors=errors)

    def convert_batch(
        self,
        jobs: list[convert_image.ConvertJob],
        output_format: str,
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> convert_image.BatchOutcome:
        if not jobs:
            return convert_image.BatchOutcome(converted=[], errors=[])

        log_info(f"Converting {len(jobs)} image(s) to {output_format.upper()}")
        job_tuples = [(job.src, job.dst) for job in jobs]
        current_file = {"path": None}

        result = run_isolated(
            convert_image.convert_batch_job,
            args=(job_tuples, output_format),
            on_progress=on_progress,
            on_status=on_status,
            on_current_file=lambda path: current_file.__setitem__("path", path),
            cancel_event=cancel_event,
        )

        if result.cancelled:
            self._cleanup_partial(current_file["path"])
            log_info("Image conversion cancelled by user")
            raise OperationCancelled()

        if not result.ok:
            log_error(f"Image conversion job failed: {result.error}")
            raise RuntimeError(result.error or "conversion failed")

        converted, errors = result.value
        for src, dst in converted:
            log_debug(f"Converted {src} -> {dst}")
            category = "svg_to_image" if src.lower().endswith(".svg") else "image_convert"
            self._log_history_success(category, src, dst)
        for message in errors:
            log_warning(f"Image conversion failed for one file: {message}")
            self._log_history_error("image_convert", None, message)

        log_info(f"Image conversion finished: {len(converted)}/{len(jobs)} converted")
        return convert_image.BatchOutcome(converted=[dst for _, dst in converted], errors=errors)

    def images_to_pdf(
        self,
        image_files: list[str],
        output_pdf_path: str,
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> str:
        log_info(f"Combining {len(image_files)} image(s) into {output_pdf_path}")
        current_file = {"path": None}

        result = run_isolated(
            convert_image.images_to_pdf_job,
            args=(list(image_files), output_pdf_path),
            on_progress=on_progress,
            on_status=on_status,
            on_current_file=lambda path: current_file.__setitem__("path", path),
            cancel_event=cancel_event,
        )

        if result.cancelled:
            self._cleanup_partial(current_file["path"])
            log_info("PDF creation cancelled by user")
            raise OperationCancelled()

        if not result.ok:
            log_error(f"PDF creation failed: {result.error}")
            self._log_history_error("images_to_pdf", image_files[0] if image_files else None, result.error or "")
            raise RuntimeError(result.error or "PDF creation failed")

        log_info(f"PDF created at {output_pdf_path}")
        self._log_history_success("images_to_pdf", image_files[0] if image_files else None, output_pdf_path)
        return result.value

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

    def _log_history_success(self, feature: str, src: Optional[str], dst: str) -> None:
        try:
            self.conversion_logger.log_success(feature, src, dst)
        except Exception:
            pass

    def _log_history_error(self, feature: str, src: Optional[str], message: str) -> None:
        try:
            self.conversion_logger.log_error(feature, src, message)
        except Exception:
            pass


__all__ = ["ImageService", "ConvertJob", "BatchOutcome", "OUTPUT_FORMATS"]
