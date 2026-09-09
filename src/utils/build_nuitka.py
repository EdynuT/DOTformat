"""Build DOTformat as a standalone executable with Nuitka.
Produces a self-contained folder under ``nuitka/main.dist/`` (or a single
executable, with ``onefile=True``) with the ``DOTformat`` executable and every
dependency (tkinter, PIL, PyMuPDF, rembg, onnxruntime, etc.) bundled alongside it.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import subprocess
import sys
from pathlib import Path

import fitz
import llvmlite
import numba
import pymatting
import pymupdf

# Packages excluded from Nuitka's compilation (see --nofollow-import-to below) and
# instead shipped as plain, uncompiled files under an "extra-libs" folder via
# --include-raw-dir (see build_nuitka() below), then imported at runtime as ordinary,
# interpreted Python via the sys.path bootstrap in main.py — exactly as they'd run from
# a venv's site-packages.
EXTRA_LIBS = {
    "pymupdf": Path(pymupdf.__file__).resolve().parent,
    "fitz": Path(fitz.__file__).resolve().parent,
    "numba": Path(numba.__file__).resolve().parent,
    "llvmlite": Path(llvmlite.__file__).resolve().parent,
    "pymatting": Path(pymatting.__file__).resolve().parent,
}

# Distribution names (PyPI project names, as opposed to the importable module names
# above) that need their *.dist-info metadata shipped alongside — some packages (e.g.
# pymatting/__init__.py: `importlib.metadata.version(__name__)`) read their own version
# via importlib.metadata at import time, which only works if that metadata directory is
# discoverable on sys.path. fitz is deliberately absent: it reads pymupdf's __version__
# directly (`from pymupdf import __version__`) rather than querying metadata itself.
DIST_INFO_NAMES = ("pymupdf", "numba", "llvmlite", "pymatting")


def _extra_libs_include_args() -> list[str]:
    """--include-raw-dir flags that ship EXTRA_LIBS (plus their dist-info metadata)
    under an "extra-libs/" folder in the distribution, unmodified.

    Nuitka's normal --include-data-dir silently drops files it recognizes as code
    (.py, .so), which is exactly what these packages are made of. --include-raw-dir is
    Nuitka's own escape hatch for this: it goes through the same data-file
    embedding/extraction pipeline (so it places files correctly for --standalone *and*
    --onefile alike — the same mechanism the tk-inter plugin relies on for bundling
    Tcl/Tk's data files) but skips that code-file filtering entirely.
    """
    args = [f"--include-raw-dir={src}=extra-libs/{name}" for name, src in EXTRA_LIBS.items()]
    for name in DIST_INFO_NAMES:
        dist_info_src = Path(str(importlib.metadata.distribution(name)._path))  # type: ignore[attr-defined]
        args.append(f"--include-raw-dir={dist_info_src}=extra-libs/{dist_info_src.name}")
    # On Windows, some of these wheels are repaired by delvewheel, which moves runtime
    # DLLs (e.g. a bundled msvcp140) into a sibling "<name>.libs" folder next to the
    # package itself (site-packages/llvmlite.libs, alongside site-packages/llvmlite) and
    # patches the package's __init__.py to add that folder to the DLL search path before
    # loading its own extension. --nofollow-import-to skips Nuitka's own DLL-dependency
    # walk for these packages entirely, so without this, that sibling folder never gets
    # shipped and the package's native extension fails to load at runtime with an
    # opaque "could not find/load shared object" error, even though the extension file
    # itself is right there — because one of *its* dependencies is missing.
    for name, src in EXTRA_LIBS.items():
        libs_dir = src.parent / f"{name}.libs"
        if libs_dir.is_dir():
            args.append(f"--include-raw-dir={libs_dir}=extra-libs/{libs_dir.name}")
    return args


def build_nuitka(
    project_root,
    venv_path=None,
    low_memory: bool = False,
    onefile: bool = False,
    app_version: str = "0.0.0.0",
) -> None:
    project_root = Path(project_root)
    output_dir = project_root / "nuitka"
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=tk-inter",
        f"--include-data-dir={project_root / 'src' / 'images'}=images",
        *_extra_libs_include_args(),
        f"--output-dir={output_dir}",
        "--output-filename=DOTformat",
        "--assume-yes-for-downloads",
        "--company-name=DOTformat",
        "--product-name=DOTformat",
        "--file-description=DOTformat - Multi-format Converter",
        # Windows requires a numeric version whenever any of the string version fields
        # above (company/product name, file description) are given — Nuitka enforces
        # this itself ("company name and file or product version need to be given when
        # any version information is given") and refuses to build at all on Windows
        # without it, even though the same command builds fine on Linux, where these
        # fields are just informational metadata with no such validation.
        f"--file-version={app_version}",
        f"--product-version={app_version}",
        "--python-flag=no_docstrings",
        "--warn-implicit-exceptions",
        # pymupdf/mupdf.py is a SWIG-generated wrapper (~69k lines / 2.6MB of Python) around
        # an already-compiled C extension, and numba (Nuitka's own help text: "currently
        # not working for standalone") is a sprawling codebase whose whole point is doing
        # its own JIT compilation via llvmlite at runtime. Translating either to C via
        # Nuitka buys nothing and pymupdf's mega-file reliably OOM-kills cc1 (~8.3GB+ RSS
        # on a single generated .c file) — this is the known, currently-unfixed Nuitka
        # issue. --nofollow-import-to always overrides --include-module/--include-package
        # for the same target (Nuitka's own docs), so a package can't be "nofollow but
        # still bundled" through the normal module machinery. Instead: nofollow these
        # entirely (Nuitka won't touch them at all); each is shipped as real files under
        # extra-libs/ via --include-raw-dir above, and main.py adds that folder to
        # sys.path at startup so they're imported as plain, interpreted Python, exactly
        # like they run from a venv. pymatting (rembg's alpha-matting dependency) hard-
        # imports numba with no fallback, so numba must actually be present, not just
        # excluded — excluding it outright (as this build previously did, via
        # --noinclude-numba-mode=nofollow) breaks the Background Remover entirely.
        # pymatting must be nofollowed too, for a different reason: its @njit(cache=True)
        # functions ask numba to locate and hash their *source file* to key the on-disk
        # cache, and a Nuitka-compiled module has no real source file backing it anymore —
        # numba's locator then raises "no locator available for file ...pymatting/util/
        # kdtree.py" at call time. Shipping pymatting as real files on disk (like the
        # others here) keeps that source-introspection working.
        "--nofollow-import-to=pymupdf",
        "--nofollow-import-to=fitz",
        "--nofollow-import-to=numba",
        "--nofollow-import-to=llvmlite",
        "--nofollow-import-to=pymatting",
        # cmath is a dynamically-loaded stdlib C extension (not built into the
        # interpreter), and Nuitka only bundles stdlib extension modules it sees used by
        # the code it actually compiles. Since numba (needed for cmath support in its
        # complex-number typing/codegen) is nofollowed above, Nuitka never sees the
        # `import cmath` inside numba's own source and leaves the .so out, so it must be
        # requested explicitly here.
        "--include-module=cmath",
        # vtracer (raster -> SVG) and resvg_py (SVG -> raster) are single native
        # extension modules. src/models/svg_converter.py imports them lazily,
        # inside functions wrapped in try/except, so that the app can report a
        # clear message when they are missing instead of failing at startup —
        # which also means Nuitka's static analysis has no top-level import to
        # follow. Request them explicitly or the SVG features are silently absent
        # from the build.
        "--include-module=vtracer",
        "--include-module=resvg_py",
        # Nuitka's runtime import hook blocks any import of a --nofollow-import-to'd
        # module by default (a safety net against accidental exclusion), even when the
        # module is reachable on sys.path via our extra-libs bootstrap in main.py. This
        # disables that guard so the import falls through to the normal, filesystem-based
        # Python import machinery instead of raising.
        "--no-deployment-flag=excluded-module-usage",
        # speech_recognition reads its own version.txt at import time, and Nuitka does not
        # bundle package data files by default. Restricted to *.txt on purpose: the 38MB of
        # pocketsphinx-data offline models are dead weight here, as audio_to_text.py only
        # ever calls recognize_google().
        "--include-package-data=speech_recognition:*.txt",
        str(project_root / "main.py"),
    ]
    if sys.platform == "win32":
        # Nuitka allocates a console window by default on Windows (unlike PyInstaller,
        # which our spec already builds with console=False) — without this, DOTformat's
        # Tkinter window opens with a visible cmd.exe window alongside it.
        cmd.insert(-1, "--windows-console-mode=disable")
    if low_memory:
        cmd.insert(-1, "--low-memory")
        # Compiling multiple of the ~1500 generated C files at once is what makes a full
        # build fast, but each parallel gcc process adds to peak RAM use — exactly what
        # low-memory mode is for. Serializing compilation is a deliberate memory/speed
        # trade-off here, made only when the caller opted into --low-memory; otherwise
        # --jobs is left unset so Nuitka defaults to using all available CPU cores,
        # which is what actually keeps a full build's wall-clock time reasonable.
        cmd.insert(-1, "--jobs=1")
    if onefile:
        cmd.insert(-1, "--onefile")
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=project_root)


def main() -> None:
    try:
        parser = argparse.ArgumentParser(description="Build DOTformat as a standalone Nuitka executable.")
        parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
        parser.add_argument("--low-memory", action="store_true", help="Enable Nuitka's --low-memory mode.")
        parser.add_argument("--onefile", action="store_true", help="Enable Nuitka's --onefile mode.")
        parser.add_argument(
            "--app-version",
            default="0.0.0.0",
            help="Windows file/product version, e.g. 3.0.0.0 (four dot-separated integers).",
        )
        args = parser.parse_args()
        build_nuitka(
            args.project_root,
            low_memory=args.low_memory,
            onefile=args.onefile,
            app_version=args.app_version,
        )
    except Exception as e:
        print("Build failed. Details:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
