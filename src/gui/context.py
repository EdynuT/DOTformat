"""Shared context passed to every GUI view/dialog.

Bundles the Tk root window and the services each feature view needs, so
individual view modules don't rely on module-level globals.
"""
from __future__ import annotations
import tkinter as tk
from dataclasses import dataclass, field

from ..services.audio_service import AudioService
from ..services.background_service import BackgroundService
from ..services.conversion_service import ConversionService
from ..services.image_service import ImageService
from ..services.pdf_service import PdfService
from ..services.qr_service import QrService
from ..services.session_service import SessionService
from ..services.video_service import VideoService


@dataclass
class AppContext:
    root: tk.Tk
    conversion_service: ConversionService = field(default_factory=ConversionService)
    image_service: ImageService = field(default_factory=ImageService)
    video_service: VideoService = field(default_factory=VideoService)
    background_service: BackgroundService = field(default_factory=BackgroundService)
    pdf_service: PdfService = field(default_factory=PdfService)
    audio_service: AudioService = field(default_factory=AudioService)
    qr_service: QrService = field(default_factory=QrService)
    session: SessionService = field(default_factory=SessionService)

    @property
    def current_user(self) -> str | None:
        return self.session.current_user

    @property
    def current_role(self) -> str | None:
        return self.session.current_role


__all__ = ["AppContext"]
