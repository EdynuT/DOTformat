import os
import platform
import stat
import sys
import tarfile
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

# Widely used prebuilt essentials for Windows
FFMPEG_WINDOWS_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# Static, self-contained Linux builds (no system libs needed) by John Van Sickle.
FFMPEG_LINUX_TAR_URLS = {
    "amd64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    "arm64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz",
}


def _linux() -> Optional[str]:
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "amd64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    return None  # 32-bit/other architectures aren't published as static builds


def _download_url() -> Optional[str]:
    if sys.platform == "win32":
        return FFMPEG_WINDOWS_ZIP_URL
    if sys.platform.startswith("linux"):
        arch = _linux()
        return FFMPEG_LINUX_TAR_URLS.get(arch) if arch else None
    return None  # macOS isn't wired up yet


def _project_root() -> Path:
    # utils/ffmpeg_finder.py -> src/utils -> src -> root
    here = Path(__file__).resolve()
    try:
        return here.parents[2]
    except IndexError:
        return here.parent


def _localapp_ffmpeg_bin() -> Path:
    return get_base_data_dir() / "ffmpeg" / "bin"


def _exe_name(base: str) -> str:
    return f"{base}.exe" if sys.platform == "win32" else base


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

    Order: project/ffmpeg > PATH > per-user app data cache > PyInstaller bundle.
    """
    ffmpeg = next((p for p in _candidates(_exe_name("ffmpeg")) if p.exists()), None)
    ffprobe = next((p for p in _candidates(_exe_name("ffprobe")) if p.exists()), None)
    return ffmpeg, ffprobe


def _prepend_to_process_path(bin_dir: Path) -> None:
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def _place_binaries(found_dir: Path, target_bin: Path, exe_names: tuple[str, str]) -> bool:
    """Copy ffmpeg/ffprobe from found_dir into target_bin, making them executable."""
    target_bin.mkdir(parents=True, exist_ok=True)
    copied_any = False
    for exe in exe_names:
        src = found_dir / exe
        if not src.exists():
            continue
        dst = target_bin / exe
        if dst.exists():
            try:
                dst.unlink()
            except Exception:
                pass
        src.replace(dst)
        if sys.platform != "win32":
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        copied_any = True
    return copied_any


def _download_and_extract_windows_zip(zip_path: Path, target_bin: Path) -> bool:
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
        found_bin = None
        for p in target_bin.parent.rglob("ffmpeg.exe"):
            if p.parent.name.lower() == "bin":
                found_bin = p.parent
                break
        if not found_bin:
            return False
        return _place_binaries(found_bin, target_bin, ("ffmpeg.exe", "ffprobe.exe"))


def _download_and_extract_linux_tar(tar_path: Path, target_bin: Path) -> bool:
    with tarfile.open(tar_path, "r:xz") as t:
        t.extractall(target_bin.parent, filter="data")
        # John Van Sickle's static builds place the binaries directly under a versioned
        # top-level folder (e.g. ffmpeg-7.0.2-amd64-static/ffmpeg), with no "bin" subdir.
        found_ffmpeg = next(target_bin.parent.rglob("ffmpeg"), None)
        if not found_ffmpeg or not found_ffmpeg.is_file():
            return False
        return _place_binaries(found_ffmpeg.parent, target_bin, ("ffmpeg", "ffprobe"))


def _download_and_extract_ffmpeg(target_bin: Path) -> bool:
    """Download and extract FFmpeg to target_bin/.

    Returns True on success, False otherwise.
    """
    try:
        import urllib.request
    except Exception:
        return False

    url = _download_url()
    if not url:
        return False

    target_bin.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        archive_path = Path(td) / ("ffmpeg.zip" if url.endswith(".zip") else "ffmpeg.tar.xz")
        try:
            with urllib.request.urlopen(url) as r, open(archive_path, "wb") as f:
                f.write(r.read())
        except Exception:
            return False
        try:
            if archive_path.suffix == ".zip":
                return _download_and_extract_windows_zip(archive_path, target_bin)
            return _download_and_extract_linux_tar(archive_path, target_bin)
        except Exception:
            return False


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
        f"{_localapp_ffmpeg_bin()}."
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
            "You can remove it later by deleting this folder:\n"
            f"{_localapp_ffmpeg_bin().parent}"
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

    Search order: project bundle > PATH > per-user app data cache > PyInstaller bundle.
    If not found and allow_download and Tk is available, prompt to download to that cache.
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

def ensure_ffmpeg_cli() -> Tuple[Optional[Path], Optional[Path]]:
    """Non-interactive variant of ensure_ffmpeg() for build/setup scripts.

    ensure_ffmpeg() gates its download behind a Tk confirmation dialog, which needs a
    running Tk root and a human to click it — neither exists in a headless CLI script.
    This looks for ffmpeg/ffprobe and, if missing, downloads them straight away
    (no prompt), printing progress instead of showing a dialog.
    """
    ffmpeg, ffprobe = find_ffmpeg_paths()
    if ffmpeg is None or ffprobe is None:
        target_bin = _localapp_ffmpeg_bin()
        print(f"FFmpeg not found. Downloading a portable build to {target_bin} ...")
        if _download_and_extract_ffmpeg(target_bin):
            ffmpeg, ffprobe = find_ffmpeg_paths()
            print("FFmpeg installed successfully!")
        else:
            print("Could not download FFmpeg automatically for this platform/architecture.")
            print("Install it manually and make sure it's on PATH.")
    for exe in (ffmpeg, ffprobe):
        if exe:
            _prepend_to_process_path(exe.parent)
    return ffmpeg, ffprobe


__all__ = [
    "find_ffmpeg_paths",
    "ensure_ffmpeg",
    "ensure_ffmpeg_cli",
]
