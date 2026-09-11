"""Runs a unit of work in an isolated child process so cancellation can kill it outright.

Anything that blocks on a C-extension or library call with no checkpoint in the
middle (vtracer's trace, PyPDF2's ``writer.write``, pdf2docx's ``convert``,
rembg's inference, a single speech-recognition request) cannot be interrupted
from inside the interpreter -- a `threading.Event` a worker thread checks
between iterations does nothing while such a call is in progress. Running the
call in its own `multiprocessing.Process` fixes that: cancelling means
terminating (and, if needed, killing) an OS process, which stops it outright
regardless of what it is doing.

``multiprocessing.freeze_support()`` is already called in ``main.py`` before
``run()``, which is what makes this safe to use from a frozen (Nuitka) build
too.
"""
from __future__ import annotations

import multiprocessing as mp
import queue as _queue
import threading
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Optional


class OperationCancelled(Exception):
    """Raised by callers to signal a job ended because of cancellation, not failure."""


@dataclass
class JobResult:
    ok: bool
    cancelled: bool
    error: Optional[str]
    value: Any = None


# Message tags sent by the child process over the queue.
_PROGRESS = "progress"
_STATUS = "status"
_CURRENT_FILE = "current_file"
_DONE = "done"
_ERROR = "error"

# How long terminate() gets before escalating to kill().
_TERMINATE_GRACE_SECONDS = 2.0
# How often the polling loop checks cancel_event/process liveness.
_POLL_INTERVAL_SECONDS = 0.1


def _run_target(target: Callable, args: tuple, kwargs: dict, mp_queue: "mp.Queue") -> None:
    """Runs inside the child process. Reports its own outcome onto the queue."""

    def report(value: float) -> None:
        try:
            mp_queue.put((_PROGRESS, value))
        except Exception:
            pass

    def set_status(msg: str) -> None:
        try:
            mp_queue.put((_STATUS, msg))
        except Exception:
            pass

    def set_current_file(path: Optional[str]) -> None:
        try:
            mp_queue.put((_CURRENT_FILE, path))
        except Exception:
            pass

    try:
        value = target(
            *args,
            report=report,
            set_status=set_status,
            set_current_file=set_current_file,
            **kwargs,
        )
        mp_queue.put((_DONE, value))
    except Exception as exc:
        mp_queue.put((_ERROR, f"{exc}\n{traceback.format_exc()}"))


def run_isolated(
    target: Callable,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    on_progress: Optional[Callable[[float], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
    on_current_file: Optional[Callable[[Optional[str]], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> JobResult:
    """Runs ``target(*args, report=, set_status=, set_current_file=, **kwargs)`` in a
    child process, forwarding its progress/status/current-file callbacks until it
    finishes or ``cancel_event`` is set.

    ``target`` must be a module-level function (picklable), and must call the
    ``report``/``set_status``/``set_current_file`` keyword arguments it receives
    instead of any closure or Tk object -- those cannot cross the process
    boundary. For batches, ``target`` should call ``set_current_file(dst_path)``
    right before starting each item, so the caller knows which output file was
    left partial if cancelled mid-batch.

    On cancellation the child process is terminated (killed if it does not exit
    promptly). The caller is responsible for deleting whatever partial output the
    last-reported current file points to -- this function only stops the process.
    """
    kwargs = kwargs or {}
    mp_queue: "mp.Queue" = mp.Queue()
    process = mp.Process(target=_run_target, args=(target, args, kwargs, mp_queue), daemon=True)
    process.start()

    outcome: dict = {}
    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                process.join(_TERMINATE_GRACE_SECONDS)
                if process.is_alive():
                    process.kill()
                    process.join(_TERMINATE_GRACE_SECONDS)
                return JobResult(ok=False, cancelled=True, error=None)

            try:
                tag, payload = mp_queue.get(timeout=_POLL_INTERVAL_SECONDS)
            except _queue.Empty:
                if not process.is_alive():
                    # Process ended without a final message (crash, killed externally).
                    break
                continue

            if tag == _PROGRESS and on_progress:
                on_progress(payload)
            elif tag == _STATUS and on_status:
                on_status(payload)
            elif tag == _CURRENT_FILE and on_current_file:
                on_current_file(payload)
            elif tag == _DONE:
                outcome["value"] = payload
                break
            elif tag == _ERROR:
                outcome["error"] = payload
                break
    finally:
        if process.is_alive():
            process.join(_TERMINATE_GRACE_SECONDS)
        try:
            mp_queue.close()
        except Exception:
            pass

    if "error" in outcome:
        return JobResult(ok=False, cancelled=False, error=outcome["error"])
    if "value" in outcome:
        return JobResult(ok=True, cancelled=False, error=None, value=outcome["value"])
    return JobResult(ok=False, cancelled=False, error="the operation ended unexpectedly")


__all__ = ["JobResult", "OperationCancelled", "run_isolated"]
