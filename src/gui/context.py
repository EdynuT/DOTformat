"""Shared context passed to every GUI view/dialog.

Bundles the Tk root window and the services each feature view needs, so
individual view modules don't rely on module-level globals.
"""
from __future__ import annotations
import tkinter as tk
from dataclasses import dataclass, field

from ..services.conversion_service import ConversionService
from ..services.session_service import SessionService


@dataclass
class AppContext:
    root: tk.Tk
    conversion_service: ConversionService = field(default_factory=ConversionService)
    session: SessionService = field(default_factory=SessionService)

    @property
    def current_user(self) -> str | None:
        return self.session.current_user

    @property
    def current_role(self) -> str | None:
        return self.session.current_role


__all__ = ["AppContext"]
