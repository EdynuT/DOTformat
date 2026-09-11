"""Reusable Tkinter progress-window helpers used by the feature views."""
from __future__ import annotations
import inspect
import threading
import tkinter as tk
from tkinter import ttk

from ...services.job_runner import OperationCancelled


def _accepts_extra_arg(fn, base_arity: int) -> bool:
    """Whether ``fn`` declares more positional parameters than ``base_arity``.

    Used to detect, without changing every existing call site at once, whether a
    ``work_fn`` opts into receiving a trailing ``cancel_event`` argument. A plain
    ``lambda report: ...`` (arity 1) does not; ``lambda report, cancel_event: ...``
    (arity 2) does.
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    params = list(sig.parameters.values())
    if any(p.kind == p.VAR_POSITIONAL for p in params):
        return True
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) > base_arity


def run_with_progress(root: tk.Tk, title: str, work_fn, *, auto: bool = False):
    """Run work_fn(report) in a background thread behind a determinate 0-100 progress bar.

    If auto=True and the worker does not report progress, a gentle auto-increment
    simulates activity up to ~92%.

    If ``work_fn`` declares a second parameter (``work_fn(report, cancel_event)``),
    a "Cancelar" button is shown; pressing it (or closing the window) sets that
    ``threading.Event`` and it becomes ``work_fn``'s responsibility to notice it
    and raise ``services.job_runner.OperationCancelled`` (propagated to the
    caller). Older callers that only take ``report`` are unaffected -- no button
    is shown and the window behaves exactly as before.
    """
    supports_cancel = _accepts_extra_arg(work_fn, 1)
    cancel_event = threading.Event()

    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("380x140" if supports_cancel else "380x110")
    win.resizable(False, False)
    win.grab_set()
    try:
        win.transient(root)
        win.lift()
        win.attributes("-topmost", True)
        win.update_idletasks()
    except Exception:
        pass
    ttk.Label(win, text=title).pack(pady=(12, 4))
    var = tk.DoubleVar(value=0.0)
    bar = ttk.Progressbar(win, mode='determinate', variable=var, maximum=100, length=320)
    bar.pack(pady=8)

    def report(value: float):
        v = max(0.0, min(100.0, float(value)))
        try:
            win.after(0, lambda: (var.set(v), bar.update_idletasks()))
        except Exception:
            pass

    result = {'val': None, 'err': None, 'cancelled': False}

    auto_running = {'on': auto}

    def _tick():
        if not auto_running['on']:
            return
        try:
            current = var.get()
            if current < 92:
                step = 0.8 if current < 50 else 0.4
                var.set(min(92, current + step))
                bar.update_idletasks()
        except Exception:
            pass
        finally:
            if auto_running['on']:
                win.after(120, _tick)

    if auto:
        win.after(200, _tick)

    def _worker():
        try:
            if supports_cancel:
                result['val'] = work_fn(report, cancel_event)
            else:
                result['val'] = work_fn(report)
        except OperationCancelled:
            result['cancelled'] = True
        except Exception as e:
            result['err'] = e
        finally:
            try:
                auto_running['on'] = False
                if not result['cancelled']:
                    win.after(0, lambda: (var.set(100), bar.update_idletasks()))
                win.after(80, lambda: win.destroy())
            except Exception:
                pass

    def on_cancel():
        if cancel_event.is_set():
            return
        cancel_event.set()
        if cancel_btn is not None:
            try:
                cancel_btn.config(state='disabled', text='Cancelando…')
            except Exception:
                pass

    cancel_btn = None
    if supports_cancel:
        cancel_btn = ttk.Button(win, text="Cancelar", command=on_cancel)
        cancel_btn.pack(pady=(0, 10))
        win.protocol("WM_DELETE_WINDOW", on_cancel)
    else:
        # Prevent user from closing the window mid-task (avoids returning None)
        win.protocol("WM_DELETE_WINDOW", lambda: None)

    threading.Thread(target=_worker, daemon=True).start()
    root.wait_window(win)
    if result['cancelled']:
        raise OperationCancelled()
    if result['err']:
        raise result['err']
    return result['val']


def run_with_progress_status(root: tk.Tk, title: str, work_fn, *, auto: bool = False):
    """Like run_with_progress, but work_fn receives (report_pct, set_status) callbacks.

    If ``work_fn`` declares a third parameter
    (``work_fn(report, set_status, cancel_event)``), a "Cancelar" button is shown
    with the same contract as :func:`run_with_progress`.
    """
    supports_cancel = _accepts_extra_arg(work_fn, 2)
    cancel_event = threading.Event()

    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("420x170" if supports_cancel else "420x140")
    win.resizable(False, False)
    win.grab_set()
    try:
        win.transient(root)
        win.lift()
        win.attributes("-topmost", True)
        win.update_idletasks()
    except Exception:
        pass

    ttk.Label(win, text=title).pack(pady=(10, 4))
    var = tk.DoubleVar(value=0.0)
    bar = ttk.Progressbar(win, mode='determinate', variable=var, maximum=100, length=360)
    bar.pack(pady=4)
    status_text = tk.StringVar(value="")
    status_lbl = ttk.Label(win, textvariable=status_text, foreground="#555")
    status_lbl.pack(pady=(2, 8))

    def report(value: float):
        v = max(0.0, min(100.0, float(value)))
        try:
            win.after(0, lambda: (var.set(v), bar.update_idletasks()))
        except Exception:
            pass

    def set_status(msg: str):
        try:
            win.after(0, lambda: (status_text.set(str(msg)), status_lbl.update_idletasks()))
        except Exception:
            pass

    result = {'val': None, 'err': None, 'cancelled': False}
    auto_running = {'on': auto}

    def _tick():
        if not auto_running['on']:
            return
        try:
            current = var.get()
            if current < 92:
                step = 0.8 if current < 50 else 0.4
                var.set(min(92, current + step))
                bar.update_idletasks()
        except Exception:
            pass
        finally:
            if auto_running['on']:
                win.after(200, _tick)

    if auto:
        win.after(200, _tick)

    def _worker():
        try:
            if supports_cancel:
                result['val'] = work_fn(report, set_status, cancel_event)
            else:
                result['val'] = work_fn(report, set_status)
        except OperationCancelled:
            result['cancelled'] = True
        except Exception as e:
            result['err'] = e
        finally:
            try:
                auto_running['on'] = False
                if not result['cancelled']:
                    win.after(0, lambda: (var.set(100), bar.update_idletasks()))
                win.after(80, lambda: win.destroy())
            except Exception:
                pass

    def on_cancel():
        if cancel_event.is_set():
            return
        cancel_event.set()
        set_status("Cancelando…")
        if cancel_btn is not None:
            try:
                cancel_btn.config(state='disabled', text='Cancelando…')
            except Exception:
                pass

    cancel_btn = None
    if supports_cancel:
        cancel_btn = ttk.Button(win, text="Cancelar", command=on_cancel)
        cancel_btn.pack(pady=(0, 10))
        win.protocol("WM_DELETE_WINDOW", on_cancel)
    else:
        win.protocol("WM_DELETE_WINDOW", lambda: None)

    threading.Thread(target=_worker, daemon=True).start()
    root.wait_window(win)
    if result['cancelled']:
        raise OperationCancelled()
    if result['err']:
        raise result['err']
    return result['val']


def run_steps(root: tk.Tk, title: str, steps_total: int, work_fn):
    """Run a known number of steps (each step increments evenly to 100)."""
    steps_total = max(1, int(steps_total))

    def _runner(report):
        done = {'n': 0}

        def inc(n: int = 1):
            done['n'] += n
            report((done['n'] / steps_total) * 100.0)

        return work_fn(inc)

    return run_with_progress(root, title, _runner, auto=False)


__all__ = ["run_with_progress", "run_with_progress_status", "run_steps"]
