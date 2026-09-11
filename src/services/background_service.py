"""Communication layer between the GUI and ``models.remove_background``.

Holds no image-processing logic of its own -- it calls into the models
package. The AI inference step (``models.remove_background.
remove_background_job``) runs through ``services.job_runner.run_isolated``,
since ``rembg.remove()`` has no checkpoint to interrupt mid-call and is the
heaviest, least interruptible step in the whole app -- see that module's
docstring for why a plain ``threading.Event`` cannot cancel it on its own. No
output file exists until the user saves after post-processing, so cancelling
the inference step never needs to clean up a partial file. The GUI
(``src.gui.views.background_view``) never imports ``src.models`` directly; this
class is the only door.
"""
from __future__ import annotations

from typing import Callable, Optional

from PIL import Image

from ..models import remove_background as rb
from .conversion_service import ConversionService
from .job_runner import OperationCancelled, run_isolated
from ..utils.console_log import log_error, log_info


class BackgroundService:
    def __init__(self) -> None:
        self.conversion_logger = ConversionService()

    def check_dependencies(self) -> list[str]:
        return rb.check_dependencies()

    def default_output_path(self, input_path: str) -> str:
        return rb.default_output_path(input_path)

    def remove_background(
        self,
        input_path: str,
        cancel_event,
        on_progress: Optional[Callable[[float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Image.Image:
        log_info(f"Removing background from {input_path}")

        result = run_isolated(
            rb.remove_background_job,
            args=(input_path,),
            on_progress=on_progress,
            on_status=on_status,
            cancel_event=cancel_event,
        )

        if result.cancelled:
            log_info("Background removal cancelled by user")
            raise OperationCancelled()

        if not result.ok:
            log_error(f"Background removal failed: {result.error}")
            self._log_history_error(input_path, result.error or "")
            raise RuntimeError(result.error or "background removal failed")

        log_info("Background removal finished")
        return result.value

    def apply_clean_mask(self, image: Image.Image) -> Image.Image:
        return rb.clean_mask(image)

    def apply_fill_holes(self, image: Image.Image) -> Image.Image:
        return rb.fill_small_holes(image)

    def apply_smooth_edges(self, image: Image.Image) -> Image.Image:
        return rb.smooth_edges(image)

    def erase_circle(self, image: Image.Image, center: tuple[int, int], radius: int) -> Image.Image:
        return rb.erase_circle(image, center, radius)

    def save(
        self,
        image: Image.Image,
        output_path: str,
        input_path: Optional[str] = None,
        username: Optional[str] = None,
    ) -> str:
        image.save(output_path)
        log_info(f"Background-removed image saved at {output_path}")
        try:
            self.conversion_logger.log_success("remove_background", input_path, output_path, username=username)
        except Exception:
            pass
        return output_path

    # ---- internal helpers ----
    def _log_history_error(self, input_path: Optional[str], message: str) -> None:
        try:
            self.conversion_logger.log_error("remove_background", input_path, message)
        except Exception:
            pass


__all__ = ["BackgroundService"]
