import os
import sys
import zipfile
import tempfile
from pathlib import Path
from shutil import which
from typing import Optional, Tuple

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:  # pragma: no cover
    tk = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore

from .app_paths import get_base_data_dir

FFMPEG_ZIP_URL = (
    # Widely used prebuilt essentials for Windows
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)


def _project_root() -> Path:
    # utils/ffmpeg_finder.py -> src/utils -> src -> root
    here = Path(__file__).resolve()
    try:
        return here.parents[2]
    except IndexError:
        return here.parent


def _localapp_ffmpeg_bin() -> Path:
    return get_base_data_dir() / "ffmpeg" / "bin"


def _candidates(exe: str) -> list[Path]:
    root = _project_root()
    cand: list[Path] = []

    # 1) Project packaged/bundled
    cand.append(root / "ffmpeg" / "bin" / exe)
    cand.append(root / "ffmpeg" / exe)

    # 2) PATH
    p = which(exe)
    if p:
        cand.append(Path(p))

    # 3) Local app data cache
    cand.append(_localapp_ffmpeg_bin() / exe)

    # 4) PyInstaller extraction
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None)
        if base:
            cand.append(Path(base) / "ffmpeg" / "bin" / exe)
            cand.append(Path(base) / "ffmpeg" / exe)
        cand.append(Path(os.path.dirname(sys.executable)) / exe)

    # Remove duplicates preserving order
    seen = set()
    uniq: list[Path] = []
    for c in cand:
        s = str(c)
        if s not in seen:
            seen.add(s)
            uniq.append(c)
    return uniq


def find_ffmpeg_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """Return paths to (ffmpeg, ffprobe) or (None, None) if not found.

    Order: project/ffmpeg > PATH > %LOCALAPPDATA%/DOTformat/ffmpeg/bin > PyInstaller bundle.
    """
    ffmpeg = next((p for p in _candidates("ffmpeg.exe") if p.exists()), None)
    ffprobe = next((p for p in _candidates("ffprobe.exe") if p.exists()), None)
    return ffmpeg, ffprobe


def _prepend_to_process_path(bin_dir: Path) -> None:
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def _download_and_extract_ffmpeg(target_bin: Path) -> bool:
    """Download and extract FFmpeg to target_bin/.

    Returns True on success, False otherwise.
    """
    try:
        import urllib.request
    except Exception:
        return False

    target_bin.mkdir(parents=True, exist_ok=True)

    # Download to temp
    with tempfile.TemporaryDirectory() as td:
        zip_path = Path(td) / "ffmpeg.zip"
        try:
            with urllib.request.urlopen(FFMPEG_ZIP_URL) as r, open(zip_path, "wb") as f:
                f.write(r.read())
        except Exception:
            return False
        # Extract
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                # Find files under */bin/ffmpeg.exe and ffprobe.exe
                members = [m for m in z.namelist() if m.lower().endswith("/bin/ffmpeg.exe") or m.lower().endswith("/bin/ffprobe.exe")]
                if not members:
                    # Extract all and search afterwards
                    z.extractall(target_bin.parent)
                else:
                    for m in members:
                        z.extract(m, target_bin.parent)
                # After extraction, search for bin containing ffmpeg.exe
                extracted_root = target_bin.parent
                found_bin = None
                for p in extracted_root.rglob("ffmpeg.exe"):
                    if p.parent.name.lower() == "bin":
                        found_bin = p.parent
                        break
                if not found_bin:
                    return False
                # Move files to target_bin
                target_bin.mkdir(parents=True, exist_ok=True)
                for exe in ("ffmpeg.exe", "ffprobe.exe"):
                    src = found_bin / exe
                    if src.exists():
                        dst = target_bin / exe
                        if dst.exists():
                            try:
                                dst.unlink()
                            except Exception:
                                pass
                        src.replace(dst)
        except Exception:
            return False
    return True


def _show_missing_dialog() -> Optional[bool]:
    """Show a small modal asking to download FFmpeg. Returns True to download, False to cancel.

    Also provides a 'What is FFmpeg?' button showing a brief explanation.
    If tkinter isn't available, return None.
    """
    if tk is None:
        return None
    root = tk._default_root
    if root is None:
        # No Tk root; cannot show UI
        return None
    win = tk.Toplevel(root)
    win.title("FFmpeg required")
    win.geometry("450x210")
    win.resizable(False, False)
    win.grab_set()
    ttk.Label(win, text="FFmpeg is required to process audio/video.").pack(pady=(10,4))
    msg = (
        "FFmpeg is a free, open-source toolkit used to decode/encode audio and video.\n"
        "DOTformat uses it to convert audio formats (pydub) and to transcode videos.\n\n"
        "We can download a portable FFmpeg now (no admin needed) and place it under\n"
        "%LOCALAPPDATA%/DOTformat/ffmpeg/bin."
    )
    lbl = ttk.Label(win, text=msg, justify="left")
    lbl.pack(padx=10)

    choice = {"val": False}

    def on_download():
        choice["val"] = True
        win.destroy()

    def on_what():
        message = (
            "FFmpeg is a command-line program used by many apps to work with media.\n"
            "We don't modify system PATH; we store a local copy for this app only.\n"
            "You can remove it later by deleting the DOTformat folder in your\n"
            "AppData directory."
        )
        messagebox.showinfo("What is FFmpeg?", message, parent=win)

    def on_cancel():
        choice["val"] = False
        win.destroy()

    btns = ttk.Frame(win); btns.pack(pady=12)
    ttk.Button(btns, text="Download now", command=on_download).pack(side="left", padx=6)
    ttk.Button(btns, text="What is FFmpeg?", command=on_what).pack(side="left", padx=6)
    ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="left", padx=6)

    win.wait_window()
    return choice["val"]


def ensure_ffmpeg(allow_download: bool = True) -> Tuple[Optional[Path], Optional[Path]]:
    """Ensure ffmpeg/ffprobe are available.

    Search order: project bundle > PATH > %LOCALAPPDATA% > PyInstaller bundle.
    If not found and allow_download and Tk is available, prompt to download to %LOCALAPPDATA%.
    Prepends the chosen bin directory to PATH for this process.
    """
    ffmpeg, ffprobe = find_ffmpeg_paths()
    if ffmpeg is None or ffprobe is None:
        if allow_download and _show_missing_dialog():
            target_bin = _localapp_ffmpeg_bin()
            ok = _download_and_extract_ffmpeg(target_bin)
            if ok:
                ffmpeg, ffprobe = find_ffmpeg_paths()
    # If found, prepend bin dir to PATH for downstream libs
    for exe in (ffmpeg, ffprobe):
        if exe:
            _prepend_to_process_path(exe.parent)
    return ffmpeg, ffprobe

__all__ = [
    "find_ffmpeg_paths",
    "ensure_ffmpeg",
]
