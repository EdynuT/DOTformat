"""Business logic for AI background removal and mask post-processing.

Pure logic, no Tkinter -- same rule as the other modules in this package. The
GUI never imports this module directly; ``services.background_service.
BackgroundService`` is the only caller.

``remove_background_job`` is the one call with no checkpoint in the middle
(``rembg.remove()`` cannot be interrupted once started), so it is meant to be
run through ``services.job_runner.run_isolated`` for real cancellation -- see
that module's docstring. Heavy imports (rembg, numpy, cv2) are deferred to
inside that function so it can double as the isolated child process's own entry
point without paying their import cost anywhere else.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from PIL import Image, ImageFilter

REQUIRED_PACKAGES = (("rembg", "rembg"), ("numpy", "numpy"), ("cv2", "opencv-python-headless"))


def check_dependencies() -> list[str]:
    """pip package names for any of the AI dependencies that are missing."""
    import importlib.util

    missing = []
    for mod_name, pip_name in REQUIRED_PACKAGES:
        try:
            spec = importlib.util.find_spec(mod_name)
        except Exception:
            spec = None
        if spec is None:
            missing.append(pip_name)
    return missing


def default_output_path(input_path: str) -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base, _ = os.path.splitext(os.path.basename(input_path))
    return os.path.join(desktop, f"{base}_nobg.png")


def clean_mask(image: Image.Image) -> Image.Image:
    """Apply a median filter to remove small noise in the alpha/mask."""
    return image.filter(ImageFilter.MedianFilter(size=3))


def fill_small_holes(pil_image: Image.Image) -> Image.Image:
    """Fill small holes in alpha channel (best effort if deps present)."""
    try:
        import numpy as np
        import cv2
    except Exception:
        return pil_image
    try:
        img = np.array(pil_image)
        if img.shape[2] == 4:
            alpha = img[:, :, 3]
            mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)[1]
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            img[:, :, 3] = mask
            return Image.fromarray(img)
    except Exception:
        return pil_image
    return pil_image


def smooth_edges(pil_image: Image.Image) -> Image.Image:
    """Slight Gaussian blur on alpha to soften edges."""
    img = pil_image.convert("RGBA")
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=1))
    return Image.merge("RGBA", (r, g, b, a))


def erase_circle(image: Image.Image, center: tuple[int, int], radius: int) -> Image.Image:
    """Makes a circular area transparent (manual eraser brush stroke)."""
    try:
        import numpy as np
        import cv2
    except Exception:
        return image
    img_np = np.array(image)
    if img_np.shape[2] != 4:
        return image
    alpha = img_np[:, :, 3].copy()
    cv2.circle(alpha, center, radius, 0, -1)
    img_np[:, :, 3] = alpha
    return Image.fromarray(img_np)


def _normalize_rembg_output(out) -> Image.Image:
    """rembg.remove() may return bytes (PNG), a PIL Image, or a numpy array."""
    if isinstance(out, bytes):
        from io import BytesIO
        try:
            return Image.open(BytesIO(out)).convert("RGBA")
        except Exception as e:
            raise RuntimeError(f"Failed to decode rembg bytes: {e}") from e
    if hasattr(out, "mode") and hasattr(out, "size"):
        try:
            return out.convert("RGBA")
        except Exception:
            return out
    try:
        return Image.fromarray(out).convert("RGBA")
    except Exception as e:
        raise RuntimeError(f"Unsupported rembg output type: {type(out)} ({e})") from e


def remove_background_job(
    input_path: str,
    *,
    report: Optional[Callable[[float], None]] = None,
    set_status: Optional[Callable[[str], None]] = None,
    set_current_file: Optional[Callable[[Optional[str]], None]] = None,
) -> Image.Image:
    """Runs the AI model on ``input_path`` and returns an RGBA image. No file is
    written here -- the caller decides if/where to save after post-processing.
    """
    # In no-console builds on Windows, sys.stdout/stderr can be None; some
    # native libs write to them and crash with "NoneType has no attribute
    # 'write'". This also runs in an isolated child process, which can
    # inherit the same no-console setup.
    try:
        import sys
        if getattr(sys, "stdout", None) is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="ignore")
        if getattr(sys, "stderr", None) is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="ignore")
    except Exception:
        pass

    def _status(msg: str) -> None:
        if set_status:
            set_status(msg)

    def _progress(val: float) -> None:
        if report:
            report(val)

    _status("Loading AI libraries…")
    _progress(5)
    try:
        from rembg import remove
    except Exception as e:
        raise RuntimeError(
            f"Missing or broken 'rembg' dependency ({type(e).__name__}: {e}). "
            "If running from source, install with: python -m pip install rembg"
        ) from e

    _status("Loading image…")
    _progress(10)
    input_image = Image.open(input_path).convert("RGBA")

    _status("Applying AI model…")
    _progress(35)
    out = remove(input_image)
    img = _normalize_rembg_output(out)

    _status("Finalizing…")
    _progress(95)
    return img


__all__ = [
    "REQUIRED_PACKAGES",
    "check_dependencies",
    "default_output_path",
    "clean_mask",
    "fill_small_holes",
    "smooth_edges",
    "erase_circle",
    "remove_background_job",
]
