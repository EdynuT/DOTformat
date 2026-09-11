"""Business logic for video format conversion via ffmpeg.

Pure logic, no Tkinter -- same rule as the other modules in this package. The
GUI never imports this module directly; ``services.video_service.VideoService``
is the only caller.

ffmpeg already runs as a real OS subprocess, so unlike the image-conversion
models (which need ``services.job_runner``'s isolated-process kill to interrupt
a library call with no checkpoint), cancelling here just means terminating that
subprocess -- the per-line ffmpeg-output loop in :func:`convert_single` already
gives a natural place to check a ``threading.Event`` and react immediately.
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import cv2

from ..utils.ffmpeg_finder import ensure_ffmpeg

VIDEO_EXTENSIONS = ('.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp4', '.mpeg', '.mpg', '.dav')

_CODECS = {
    'mp4': ('libx264', 'aac'),
    'avi': ('mpeg4', 'mp3'),
    'mov': ('libx264', 'aac'),
}

_TIME_PATTERN = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')


class VideoConversionCancelled(Exception):
    """Raised by :func:`convert_single` when ``cancel_event`` was set mid-run."""


@dataclass(frozen=True)
class BatchOutcome:
    converted: list[str]
    errors: list[str]


def get_video_duration(video_file: str) -> float:
    """Duration in seconds, via OpenCV. Returns 1 if it cannot be determined."""
    cap = cv2.VideoCapture(video_file)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 1
    cap.release()
    return duration


def resolve_ffmpeg_exe() -> str:
    ffmpeg, _ = ensure_ffmpeg(allow_download=True)
    if ffmpeg and os.path.exists(str(ffmpeg)):
        return str(ffmpeg)
    return 'ffmpeg'


def list_batch_jobs(input_dir: str, output_dir: str, output_format: str) -> list[tuple[str, str]]:
    """(src, dst) pairs for every video in ``input_dir``, named ``<name>_converted.<fmt>``."""
    jobs = []
    for name in sorted(os.listdir(input_dir)):
        if not name.lower().endswith(VIDEO_EXTENSIONS):
            continue
        src = os.path.join(input_dir, name)
        base_name = os.path.splitext(name)[0]
        dst = os.path.join(output_dir, f"{base_name}_converted.{output_format}")
        jobs.append((src, dst))
    return jobs


def _popen_kwargs() -> dict:
    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return dict(startupinfo=startupinfo, creationflags=creationflags)


def convert_single(
    input_file: str,
    output_file: str,
    output_format: str,
    *,
    total_duration: Optional[float] = None,
    report: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    """Converts one video with ffmpeg, reporting progress parsed from its own output.

    Raises :class:`VideoConversionCancelled` if ``cancel_event`` gets set while
    running -- the caller is responsible for removing the partial
    ``output_file`` ffmpeg was writing to (``-y`` means it writes straight to
    the final path, no temp+rename). Raises ``RuntimeError`` if ffmpeg exits
    with a non-zero status.
    """
    vcodec, acodec = _CODECS.get(output_format.lower(), ('libx264', 'aac'))
    if total_duration is None:
        total_duration = get_video_duration(input_file)

    cmd = [
        resolve_ffmpeg_exe(), '-y',
        '-i', input_file,
        '-vcodec', vcodec,
        '-acodec', acodec,
        output_file,
    ]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
        **_popen_kwargs(),
    )

    # Gentle nudge so progress doesn't look frozen when ffmpeg goes quiet for a
    # stretch (e.g. near the end, during muxing).
    stop_nudge = threading.Event()
    last_update = {'t': time.time(), 'pct': 0.0}

    def nudger():
        while not stop_nudge.is_set():
            time.sleep(0.25)
            if report and (time.time() - last_update['t']) > 1.5 and last_update['pct'] < 99.0:
                last_update['pct'] = min(99.0, last_update['pct'] + 0.4)
                report(last_update['pct'])

    threading.Thread(target=nudger, daemon=True).start()

    try:
        for line in process.stderr:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise VideoConversionCancelled()
            match = _TIME_PATTERN.search(line)
            if match and report:
                h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), float(match.group(4))
                current_time = h * 3600 + m * 60 + s + (ms / 100.0)
                percent = min((current_time / max(1e-6, total_duration)) * 100, 98.0)
                last_update['t'] = time.time()
                last_update['pct'] = percent
                report(percent)
        process.wait()
    finally:
        stop_nudge.set()
        if process.poll() is None:
            process.terminate()

    if process.returncode != 0:
        raise RuntimeError("ffmpeg exited with an error (conversion failed).")
    if report:
        report(100.0)


__all__ = [
    "VIDEO_EXTENSIONS",
    "BatchOutcome",
    "VideoConversionCancelled",
    "get_video_duration",
    "list_batch_jobs",
    "resolve_ffmpeg_exe",
    "convert_single",
]
