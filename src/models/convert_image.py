"""Business logic for image conversion: format conversion, SVG vectorize/rasterize,
and merging images into a PDF.

Pure logic, no Tkinter -- same rule as ``svg_converter.py``, ``pdf_manager.py``,
``qrcode_generator.py`` and ``audio_to_text.py`` in this package. The GUI never
imports this module directly; ``services.image_service.ImageService`` is the only
caller, and is responsible for cancellation (via ``services.job_runner``) and
logging around the functions here.

The three ``*_batch_job`` functions are the actual conversion algorithms and are
also what ``job_runner.run_isolated`` uses as a child-process target, so they must
stay module-level (picklable) and report progress only through the
``report``/``set_status``/``set_current_file`` callbacks they receive -- see
``job_runner``'s docstring for why.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional

import img2pdf
from PIL import Image

from . import svg_converter

OUTPUT_FORMATS = tuple(svg_converter.RASTER_OUTPUT_FORMATS) + ("svg",)


@dataclass(frozen=True)
class ConvertJob:
    src: str
    dst: str


@dataclass(frozen=True)
class BatchOutcome:
    converted: list[str]
    errors: list[str]


def plan_jobs(
    image_files: list[str],
    out_dir: str,
    output_format: str,
    confirm_overwrite: Callable[[str], bool],
) -> list[ConvertJob]:
    """Builds the (src, dst) pairs for a batch.

    Skips files already in the target format (or, for SVG output, files that are
    already vector), and asks ``confirm_overwrite(dst)`` before reusing an
    existing destination path. ``confirm_overwrite`` is supplied by the caller so
    this stays free of any actual dialog -- the GUI passes a function that shows
    a messagebox; a test can pass one that always returns True/False.
    """
    jobs: list[ConvertJob] = []
    for file in image_files:
        input_ext = os.path.splitext(file)[1][1:].lower()
        if output_format == "svg":
            if input_ext == "svg":
                continue
        elif input_ext == output_format:
            continue
        base_name = os.path.splitext(os.path.basename(file))[0]
        dst = os.path.join(out_dir, f"{base_name}.{output_format}")
        if os.path.exists(dst) and not confirm_overwrite(dst):
            continue
        jobs.append(ConvertJob(src=file, dst=dst))
    return jobs


def biggest_job(jobs: list[ConvertJob]) -> Optional[ConvertJob]:
    if not jobs:
        return None
    return max(jobs, key=lambda job: svg_converter.image_pixels(job.src))


def image_size(path: str) -> tuple[int, int]:
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return (0, 0)


# ---- batch algorithms (also used as job_runner child-process targets) ----

def vectorize_batch_job(job_tuples, opts, max_long_edge, *, report, set_status, set_current_file):
    """Traces each (src, dst) pair to an SVG via ``svg_converter.vectorize``."""
    total = len(job_tuples)
    converted = []
    errors = []
    for index, (src, dst) in enumerate(job_tuples):
        set_current_file(dst)
        set_status(f"{os.path.basename(src)}  ({index + 1}/{total})")
        try:
            svg_converter.vectorize(src, dst, opts, status=None, max_long_edge=max_long_edge)
            converted.append((src, dst))
        except Exception as exc:
            errors.append(f"{os.path.basename(src)}: {exc}")
        set_current_file(None)
        report(((index + 1) / total) * 100.0)
    return converted, errors


def convert_batch_job(job_tuples, output_format, *, report, set_status, set_current_file):
    """Converts each (src, dst) pair to a raster format, or renders SVG sources."""
    total = len(job_tuples)
    fmt = output_format.lower()
    converted = []
    errors = []
    for index, (src, dst) in enumerate(job_tuples):
        set_current_file(dst)
        set_status(f"{os.path.basename(src)}  ({index + 1}/{total})")
        try:
            input_ext = os.path.splitext(src)[1][1:].lower()
            if input_ext == "svg":
                svg_converter.rasterize(src, dst, fmt, scale=2.0)
            else:
                with Image.open(src) as img:
                    try:
                        w, h = img.size
                        is_huge = (w * h) >= 100_000_000
                    except Exception:
                        is_huge = False
                    if fmt in ("jpg", "jpeg"):
                        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                            img = img.convert("RGBA")
                            bg = Image.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[3])
                            img = bg
                        else:
                            img = img.convert("RGB")
                        if is_huge:
                            img.save(dst, format="JPEG", quality=90)
                        else:
                            img.save(dst, format="JPEG", quality=100, subsampling=0, optimize=True)
                    elif fmt == "png" and is_huge:
                        img.save(dst, format="PNG", compress_level=6, optimize=False)
                    else:
                        img.save(dst, format=output_format.upper())
            converted.append((src, dst))
        except Exception as exc:
            errors.append(f"{os.path.basename(src)}: {exc}")
        set_current_file(None)
        report(((index + 1) / total) * 100.0)
    return converted, errors


def images_to_pdf_job(image_files, output_pdf_path, *, report, set_status, set_current_file):
    """Flattens alpha channels as needed and combines images into one PDF."""
    tmp_paths: list[str] = []

    def _prepare_no_alpha(path: str) -> str:
        try:
            with Image.open(path) as im:
                if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                    rgb = Image.new("RGB", im.size, (255, 255, 255))
                    if im.mode != "RGBA":
                        im = im.convert("RGBA")
                    rgb.paste(im, mask=im.split()[3])
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tmp_paths.append(tmp.name)
                    tmp.close()
                    rgb.save(tmp.name, format="JPEG", quality=95)
                    return tmp.name
        except Exception:
            pass
        return path

    set_status("Preparing images…")
    total = max(1, len(image_files))
    prepared = []
    for index, path in enumerate(image_files):
        prepared.append(_prepare_no_alpha(path))
        report(((index + 1) / total) * 50.0)

    set_current_file(output_pdf_path)
    set_status("Generating PDF…")
    try:
        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert(prepared))
        report(100.0)
        return output_pdf_path
    finally:
        for p in tmp_paths:
            try:
                os.remove(p)
            except Exception:
                pass
        set_current_file(None)


__all__ = [
    "OUTPUT_FORMATS",
    "ConvertJob",
    "BatchOutcome",
    "plan_jobs",
    "biggest_job",
    "image_size",
    "vectorize_batch_job",
    "convert_batch_job",
    "images_to_pdf_job",
]
