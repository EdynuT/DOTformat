import os
import sys

# PyMuPDF (fitz/pymupdf) is shipped as raw, uncompiled data under "extra-libs" next to
# the executable (see build_nuitka.py) instead of being compiled by Nuitka — its
# SWIG-generated wrapper is too large for Nuitka's C compilation step to handle. Make it
# importable exactly as it would be from a venv's site-packages. In non-frozen runs (e.g.
# `python main.py` from source) this directory doesn't exist and the check is a no-op.
_extra_libs = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "extra-libs")
if os.path.isdir(_extra_libs) and _extra_libs not in sys.path:
    sys.path.insert(0, _extra_libs)

import multiprocessing

from src.gui.app import run

# Run with:  python main.py
if __name__ == "__main__":
    # Required for frozen (PyInstaller) builds: without this, any library that
    # spawns worker processes (onnxruntime/numba/rembg, etc.) can cause the
    # whole frozen app to be re-executed recursively, opening new windows in a loop.
    multiprocessing.freeze_support()
    run()
