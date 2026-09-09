"""Raster <-> SVG conversion.

Two directions, deliberately kept free of Tkinter so they can be called from a
worker thread:

* :func:`vectorize`   raster (PNG/JPG/...) -> SVG, tracing with ``vtracer``.
* :func:`rasterize`   SVG -> raster, rendering with ``resvg``.

Why resvg renders the SVG side
------------------------------
Two cheaper-looking options were measured against Firefox on nine SVG features,
and both were rejected.

PyMuPDF is already bundled for the PDF features, so it would have cost nothing
to add. It is not usable here: it renders CSS ``<style>`` rules and gradients as
solid black, and ignores ``clipPath``, ``mask`` and ``stroke-dasharray``
entirely. Those are not exotic -- every Figma, Illustrator and Inkscape export
leans on CSS and gradients -- so most real SVGs would come out wrong.

CairoSVG is far better, and matched Firefox on seven of the nine cases. It fails
on the other two: it ignores ``feColorMatrix`` filters (RMSE 0.209 against
Firefox, versus 0.003 for resvg) and gradient luminance masks (0.383 versus
0.001), and it ignores them *silently* -- no exception, just a plausible-looking
wrong image. It would also have cost the most to ship: ``cairocffi``'s wheel
carries no native binary and dlopens ``libcairo-2.dll`` at runtime, so a Windows
build has to bundle the GTK cairo stack and its whole dependency chain by hand.

resvg matched Firefox everywhere, and its wheel is a single self-contained
2.7 MB native module (``abi3``, so one wheel covers 3.10 through 3.14 on both
Linux and Windows). PyInstaller and Nuitka pick it up without a hook, exactly
like vtracer.

Why the pre-pass in :func:`snap_colors` exists
----------------------------------------------
Tracing a raster straight into vector paths goes wrong on the images people
actually have, and the culprit is anti-aliasing rather than colour as such.
Every soft pixel along an edge is a colour of its own, and the tracer honestly
turns each one into its own sliver of a path. Measured on a four-shape logo
resampled to 1200px:

===========================================  =======  =======
pipeline                                       size    paths
===========================================  =======  =======
traced directly                               227 KB      438
snap_colors(8) + filter_speckle=16             62 KB        4
===========================================  =======  =======

Both render identically. The second is the truth about the image; the first is
438 fragments of it. (The "logo" preset settled on filter_speckle=4 rather than
the 16 used here -- see the note above PRESETS: 16 wins on this synthetic shape
but deletes small real details on actual artwork.)

Getting there needs three things together, and dropping any one of them brings
the fragments back or corrupts the colours:

1. **FASTOCTREE, not MEDIANCUT.** Median-cut splits the palette by pixel count,
   so a small region loses its colour to a larger neighbour. On the test logo it
   dropped the blue circle entirely (RGB distance 99 from the true blue) and
   drifted the green by 32. FASTOCTREE keeps every distinct colour within a
   distance of 2. MAXCOVERAGE was worse than either.
2. **A hard alpha channel.** A soft alpha edge fragments the outline just like a
   soft colour edge does: with the colours snapped but the alpha left smooth,
   the same logo still traced to 230 paths instead of 4.
3. **filter_speckle.** It discards the few fragments that survive. At 0 the
   snapped image still traced to 2125 paths; at 16, to 4.

Fully transparent pixels are also refilled before quantising, because otherwise
their (arbitrary, usually black) RGB claims a palette slot that a real colour
needed.

Why vtracer is always called positionally
-----------------------------------------
``vtracer`` 0.6.15 segfaults the interpreter when its optional parameters are
passed by keyword under Python 3.14 -- including ``color_precision=6``, which is
merely its own default. The same calls are fine under 3.10. Passing all thirteen
arguments positionally works on both, so :func:`_trace` is the single place that
calls into the library and it never uses keywords. Do not "tidy" it into kwargs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

from PIL import Image

# Formats we can vectorise from, and rasterise back to.
RASTER_INPUT_FORMATS = ("png", "jpg", "jpeg", "bmp", "gif", "ico", "webp", "tiff", "tif")
RASTER_OUTPUT_FORMATS = ("png", "jpg", "jpeg", "bmp", "gif", "ico")

# Above this many pixels, tracing at full resolution costs far more than it
# returns, so the user is offered a smaller trace. A 34MP photograph took 6
# minutes, 4.6GB of RAM and produced a 116MB SVG -- correct, but too heavy to
# open. Since an SVG scales to any size anyway, tracing the same photo at
# SUGGESTED_MAX_LONG_EDGE looks the same and costs a fraction.
LARGE_IMAGE_PIXELS = 10_000_000
SUGGESTED_MAX_LONG_EDGE = 3000

# Estimated output above this is worth mentioning: past roughly this size an SVG
# is slower to open than the raster it came from, which defeats the point.
HEAVY_SVG_MB = 20.0

# Long edge of the miniature used by estimate_svg_mb().
PROBE_LONG_EDGE = 500


@dataclass(frozen=True)
class TraceOptions:
    """Vectorisation settings.

    ``colors`` drives the colour-snapping pre-pass (``None`` disables it),
    ``denoise`` the JPEG-artifact pre-pass (0 disables it); the rest are passed
    through to vtracer.
    """

    colors: Optional[int] = 8
    hard_alpha: bool = True
    denoise: int = 0                  # 0 disables; otherwise bilateral strength
    colormode: str = "color"          # "color" | "binary"
    hierarchical: str = "stacked"     # "stacked" | "cutout"
    mode: str = "spline"              # "spline" | "polygon" | "none"
    filter_speckle: int = 16
    color_precision: int = 6
    layer_difference: int = 16
    corner_threshold: int = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: int = 45
    path_precision: int = 3


# Presets covering the three kinds of image people bring, tuned by measuring
# SSIM of the re-rendered SVG against the original on a real set (a vector logo,
# flat character art, an anime still, three digital paintings, a dense map and a
# 34MP photograph). Notes on the non-obvious choices:
#
# * "logo" uses filter_speckle=4, not the 16 an earlier pass suggested. On a
#   synthetic four-shape test 16 looked ideal, but on real artwork it deletes
#   small legitimate details -- it silently removed a character's hair clip --
#   while saving almost nothing: SSIM 0.883 -> 0.915 for 62KB instead of 56KB.
# * "photo" traces polygons rather than splines. On detailed images the two score
#   the same (SSIM 0.812 vs 0.810 on one painting, and still level when the SVG
#   is rendered back at 4x its traced size), but splines cost roughly three times
#   the bytes: 8.44MB against 2.98MB. Splines are kept only for "logo", whose
#   output a person might actually open and edit, and whose files are tiny anyway.
# * "illustration" is the middle rung, and had to be earned: an earlier version
#   using splines and a 48-colour snap scored *worse* than "photo" and produced
#   *larger* files (5.03MB vs 2.65MB on one painting), which makes it pointless.
#   As tuned it reaches 96.6% of "photo"'s SSIM at 49.4% of its size, so the
#   choice it offers is a real one: half the file for a few percent of detail.
# * "photo" leaves colors=None. Snapping a palette is what rescues flat art, and
#   what ruins a photograph -- it is the difference between clean shapes and a
#   posterised mess.
PRESETS: dict[str, TraceOptions] = {
    "logo": TraceOptions(
        colors=12, filter_speckle=4, color_precision=6, layer_difference=48,
        mode="spline", path_precision=3,
    ),
    "illustration": TraceOptions(
        colors=64, filter_speckle=4, color_precision=7, layer_difference=8,
        mode="polygon", path_precision=3,
    ),
    "photo": TraceOptions(
        colors=None, filter_speckle=2, color_precision=8, layer_difference=4,
        mode="polygon", path_precision=3,
    ),
}

PRESET_LABELS = {
    "logo": "Logo / flat art",
    "illustration": "Illustration",
    "photo": "Detailed photo",
}


class SvgDependencyError(RuntimeError):
    """Raised when the library backing a conversion direction is unavailable."""


def vtracer_available() -> bool:
    try:
        import vtracer  # noqa: F401
    except Exception:
        return False
    return True


def svg_render_available() -> bool:
    try:
        import resvg_py  # noqa: F401
    except Exception:
        return False
    return True


def image_pixels(path: str) -> int:
    """Pixel count of ``path``, or 0 if it cannot be read."""
    try:
        with Image.open(path) as im:
            w, h = im.size
        return w * h
    except Exception:
        return 0


def is_large_image(path: str) -> bool:
    """Whether ``path`` is big enough to be worth offering a smaller trace."""
    return image_pixels(path) >= LARGE_IMAGE_PIXELS


def estimate_svg_mb(
    src_path: str,
    opts: TraceOptions,
    max_long_edge: int | None = None,
) -> float:
    """Predict the size of the SVG this image would produce, in megabytes.

    Traces a PROBE_LONG_EDGE miniature -- which takes between 0.1s and about a
    second even for a 34MP photograph -- and scales its bytes-per-megapixel up to
    the real pixel count. Validated against eight fully traced images:

    ======================  ==========  ==========
    image                     measured   predicted
    ======================  ==========  ==========
    anime still (0.09MP)       0.21MB      0.21MB
    character art (0.59MP)     0.65MB      0.68MB
    painting (0.53MP)          2.65MB      2.75MB
    painting (0.90MP)          3.22MB      3.75MB
    dense map (1.57MP)         8.45MB      8.62MB
    photograph (34MP)        116.64MB    155.58MB
    ======================  ==========  ==========

    Seven of eight land within 20%; the 34MP photograph over-predicts by a third,
    which is the safe direction for a warning.

    The miniature is resampled with NEAREST rather than LANCZOS on purpose. Flat
    artwork is the one case where bytes do *not* scale with area -- a logo traces
    to the same handful of shapes at any size -- and smooth resampling invents
    anti-aliased edges the real image never had. With LANCZOS a flat vector logo
    was over-predicted by 222x (3.10MB against 0.014MB actual), enough to warn
    about the one kind of image this feature handles perfectly. NEAREST brings
    that to 0.12MB, far below any threshold, while leaving photographs accurate.

    Returns 0.0 if anything goes wrong: a failed guess must never block a
    conversion that would have worked.
    """
    import tempfile

    probe_svg = None
    probe_png = None
    try:
        with Image.open(src_path) as im:
            im.load()
            width, height = im.size
            full = im.copy()

        if max_long_edge and max(width, height) > max_long_edge:
            ratio = max_long_edge / max(width, height)
            width, height = max(1, round(width * ratio)), max(1, round(height * ratio))

        longest = max(full.size)
        if longest > PROBE_LONG_EDGE:
            ratio = PROBE_LONG_EDGE / longest
            probe = full.resize(
                (max(1, round(full.width * ratio)), max(1, round(full.height * ratio))),
                Image.NEAREST,
            )
        else:
            probe = full

        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        probe_png = handle.name
        handle.close()
        probe.save(probe_png, format="PNG")

        handle = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
        probe_svg = handle.name
        handle.close()
        _trace(probe_png, probe_svg, opts)

        probe_mp = (probe.width * probe.height) / 1e6
        if probe_mp <= 0:
            return 0.0
        mb_per_mp = (os.path.getsize(probe_svg) / (1024 * 1024)) / probe_mp
        return mb_per_mp * ((width * height) / 1e6)
    except Exception:
        return 0.0
    finally:
        for temp in (probe_png, probe_svg):
            if temp:
                try:
                    os.remove(temp)
                except Exception:
                    pass


def snap_colors(im: Image.Image, colors: int, hard_alpha: bool = True) -> Image.Image:
    """Collapse anti-aliased edges onto a small exact palette.

    See the module docstring for why each step is needed. Returns an RGBA image.
    """
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    has_alpha = alpha.getextrema()[0] < 255

    # A soft alpha edge fragments the outline exactly like a soft colour edge.
    if hard_alpha and has_alpha:
        alpha = alpha.point(lambda a: 255 if a >= 128 else 0)
        has_alpha = alpha.getextrema()[0] < 255

    rgb = im.convert("RGB")

    # Transparent pixels carry arbitrary RGB (usually black). Left alone they
    # win a palette slot that a real colour needed, which is how a visible
    # colour goes missing from the output.
    if has_alpha:
        counts = rgb.getcolors(maxcolors=1 << 24) or []
        if counts:
            filler = max(counts, key=lambda entry: entry[0])[1]
            backdrop = Image.new("RGB", im.size, filler)
            backdrop.paste(rgb, mask=alpha)
            rgb = backdrop

    # FASTOCTREE preserves small-area colours; MEDIANCUT drops them. Dithering
    # must stay off -- it reintroduces exactly the speckle we are removing.
    quantized = rgb.quantize(
        colors=max(2, min(256, int(colors))),
        method=Image.FASTOCTREE,
        dither=Image.Dither.NONE,
    ).convert("RGB")
    quantized.putalpha(alpha)
    return quantized


def reduce_artifacts(im: Image.Image, strength: int) -> Image.Image:
    """Smooth JPEG block artifacts while keeping edges, via a bilateral filter.

    Off by default, because whether it helps depends entirely on how compressed
    the source actually is, and the damage when it is wrong is visible. Measured
    on two digital paintings traced with the "photo" preset:

    * elfo.jpg (674x674 in 60KB -- heavily compressed): without this, the dark
      background traced into a grid of hard-edged rectangles, the JPEG's own 8x8
      blocks promoted into shapes. With strength=3 the blocking is gone and the
      tone matches the original.
    * chapeu.jpg (949x949 in 141KB -- lightly compressed): the same filter
      flattened a subtly mottled wall into banded patches, losing texture the
      unfiltered trace had kept. SSIM 0.917 -> 0.900.

    Note that SSIM actively misleads here: it rewards faithfully reproducing the
    source's own compression artifacts, so it scored the blocky elfo.jpg trace
    higher (0.927 vs 0.851) than the clean one. The judgement above is visual.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return im  # OpenCV is optional; silently skip rather than fail the trace

    had_alpha = im.mode == "RGBA"
    alpha = im.getchannel("A") if had_alpha else None
    rgb = np.asarray(im.convert("RGB"))
    # strength 1 is the setting measured above (diameter 3, sigma 20): enough to
    # dissolve 8x8 JPEG blocks, gentle enough to leave real texture alone. Higher
    # values widen and flatten from there.
    strength = max(1, min(10, int(strength)))
    diameter = strength * 2 + 1
    sigma = 20 + (strength - 1) * 15
    filtered = cv2.bilateralFilter(
        cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), diameter, sigma, sigma
    )
    out = Image.fromarray(cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB))
    if alpha is not None:
        out.putalpha(alpha)
    return out


def _trace(src_path: str, dst_path: str, opts: TraceOptions) -> None:
    """The only call into vtracer. Positional arguments only -- see module docstring."""
    try:
        import vtracer
    except Exception as exc:
        raise SvgDependencyError(
            "SVG output needs the 'vtracer' package.\n"
            "Install it with:  pip install vtracer\n"
            f"(underlying error: {exc})"
        ) from exc

    vtracer.convert_image_to_svg_py(
        src_path,
        dst_path,
        opts.colormode,
        opts.hierarchical,
        opts.mode,
        int(opts.filter_speckle),
        int(opts.color_precision),
        int(opts.layer_difference),
        int(opts.corner_threshold),
        float(opts.length_threshold),
        int(opts.max_iterations),
        int(opts.splice_threshold),
        int(opts.path_precision),
    )


def vectorize(
    src_path: str,
    dst_path: str,
    opts: TraceOptions | None = None,
    status: Optional[Callable[[str], None]] = None,
    max_long_edge: int | None = None,
) -> str:
    """Trace a raster image into ``dst_path`` as SVG. Returns ``dst_path``.

    ``max_long_edge`` traces a shrunk copy of the image. The result is still
    resolution-independent, so this costs far less than it appears to: it caps
    how much detail is carved into paths, not how large the SVG can be drawn.
    """
    opts = opts or PRESETS["logo"]

    def say(msg: str) -> None:
        if status:
            try:
                status(msg)
            except Exception:
                pass

    say("Reading image…")
    with Image.open(src_path) as im:
        im.load()
        prepared = im.copy()

    if max_long_edge:
        width, height = prepared.size
        longest = max(width, height)
        if longest > max_long_edge:
            ratio = max_long_edge / longest
            prepared = prepared.resize(
                (max(1, round(width * ratio)), max(1, round(height * ratio))),
                Image.LANCZOS,
            )

    temp_path: str | None = None
    try:
        if opts.denoise:
            say("Reducing compression artifacts…")
            prepared = reduce_artifacts(prepared, opts.denoise)
        if opts.colors:
            say("Cleaning up colours…")
            prepared = snap_colors(prepared, opts.colors, opts.hard_alpha)
        else:
            prepared = prepared.convert("RGBA")

        # vtracer reads from disk, so the pre-passed image needs a file. Write it
        # next to the output, where we already know we can write.
        say("Tracing shapes…")
        temp_path = os.path.join(
            os.path.dirname(os.path.abspath(dst_path)),
            f".dotformat_trace_{os.getpid()}.png",
        )
        prepared.save(temp_path, format="PNG")
        _trace(temp_path, dst_path, opts)
    finally:
        try:
            prepared.close()
        except Exception:
            pass
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    say("Finishing…")
    return dst_path


def svg_stats(svg_path: str) -> tuple[float, int]:
    """Return ``(size_in_mb, path_count)`` for a generated SVG."""
    try:
        size_mb = os.path.getsize(svg_path) / (1024 * 1024)
    except Exception:
        size_mb = 0.0
    try:
        with open(svg_path, encoding="utf-8", errors="ignore") as handle:
            paths = handle.read().count("<path")
    except Exception:
        paths = 0
    return size_mb, paths


def rasterize(
    src_path: str,
    dst_path: str,
    output_format: str,
    scale: float = 2.0,
    status: Optional[Callable[[str], None]] = None,
) -> str:
    """Render an SVG to a raster image at ``scale`` times its natural size."""
    try:
        import resvg_py
    except Exception as exc:
        raise SvgDependencyError(
            "Reading SVG files needs the 'resvg-py' package.\n"
            "Install it with:  pip install resvg-py\n"
            f"(underlying error: {exc})"
        ) from exc

    if status:
        try:
            status("Rendering SVG…")
        except Exception:
            pass

    fmt = output_format.lower()

    # resvg always renders RGBA; formats without alpha are flattened below.
    try:
        png_bytes = bytes(
            resvg_py.svg_to_bytes(svg_path=src_path, zoom=float(scale))
        )
    except Exception as exc:
        raise ValueError(f"could not read this SVG ({exc})") from exc

    import io

    try:
        image = Image.open(io.BytesIO(png_bytes))
        image.load()
    except Exception as exc:
        raise ValueError(f"this SVG produced no drawable content ({exc})") from exc

    if status:
        try:
            status("Saving…")
        except Exception:
            pass

    if fmt in ("jpg", "jpeg"):
        if image.mode == "RGBA":
            backdrop = Image.new("RGB", image.size, (255, 255, 255))
            backdrop.paste(image, mask=image.split()[3])
            image = backdrop
        else:
            image = image.convert("RGB")
        image.save(dst_path, format="JPEG", quality=95, subsampling=0, optimize=True)
    elif fmt == "ico":
        # ICO tops out at 256x256; hand Pillow something it can actually store.
        image.convert("RGBA").save(dst_path, format="ICO")
    elif fmt == "bmp":
        image.convert("RGB").save(dst_path, format="BMP")
    else:
        image.save(dst_path, format=fmt.upper())

    return dst_path


__all__ = [
    "LARGE_IMAGE_MESSAGE",
    "PRESETS",
    "PRESET_LABELS",
    "RASTER_INPUT_FORMATS",
    "RASTER_OUTPUT_FORMATS",
    "SvgDependencyError",
    "TraceOptions",
    "estimate_svg_mb",
    "image_pixels",
    "is_large_image",
    "rasterize",
    "reduce_artifacts",
    "snap_colors",
    "svg_render_available",
    "svg_stats",
    "vectorize",
    "vtracer_available",
]
