"""Background removal view: thin wrapper around models.remove_background."""
from __future__ import annotations
from tkinter import messagebox

from ..context import AppContext
from ...models.remove_background import remove_background


def remove_background_action(ctx: AppContext) -> None:
    try:
        remove_background()
        ctx.conversion_service.log_success("remove_background", None, None, username=ctx.current_user)
    except Exception as e:
        ctx.conversion_service.log_error("remove_background", None, str(e), username=ctx.current_user)
        messagebox.showerror("Error", f"Background removal failed: {e}")


__all__ = ["remove_background_action"]
