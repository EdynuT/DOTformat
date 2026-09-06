"""Image conversion view: thin wrapper around models.convert_image.ImageConverter."""
from __future__ import annotations
import traceback

from ..context import AppContext
from ...models.convert_image import ImageConverter


def convert_image_action(ctx: AppContext) -> None:
    try:
        ImageConverter(ctx.root).convert_image()
        ctx.conversion_service.log_success("image_convert", None, None, username=ctx.current_user)
    except Exception as e:
        ctx.conversion_service.log_error("image_convert", None, str(e), username=ctx.current_user)
        traceback.print_exc()


__all__ = ["convert_image_action"]
