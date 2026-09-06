"""Reusable Tkinter progress-window helpers used by the feature views."""
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import ttk


def run_with_progress(root: tk.Tk, title: str, work_fn, *, auto: bool = False):
    """Run work_fn(report) in a background thread behind a determinate 0-100 progress bar.

    If auto=True and the worker does not report progress, a gentle auto-increment
    simulates activity up to ~92%.
    """
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("380x110")
    win.resizable(False, False)
    win.grab_set()
    try:
        win.transient(root)
        win.lift()
        win.attributes("-topmost", True)
        win.update_idletasks()
    except Exception:
        pass
    # Prevent user from closing the window mid-task (avoids returning None)
    win.protocol("WM_DELETE_WINDOW", lambda: None)
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

    result = {'val': None, 'err': None}

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
            result['val'] = work_fn(report)
        except Exception as e:
            result['err'] = e
        finally:
            try:
                auto_running['on'] = False
                win.after(0, lambda: (var.set(100), bar.update_idletasks()))
                win.after(80, lambda: win.destroy())
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()
    root.wait_window(win)
    if result['err']:
        raise result['err']
    return result['val']


def run_with_progress_status(root: tk.Tk, title: str, work_fn, *, auto: bool = False):
    """Like run_with_progress, but work_fn receives (report_pct, set_status) callbacks."""
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("420x140")
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

    result = {'val': None, 'err': None}
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
            result['val'] = work_fn(report, set_status)
        except Exception as e:
            result['err'] = e
        finally:
            try:
                auto_running['on'] = False
                win.after(0, lambda: (var.set(100), bar.update_idletasks()))
                win.after(80, lambda: win.destroy())
            except Exception:
                pass

    win.protocol("WM_DELETE_WINDOW", lambda: None)
    threading.Thread(target=_worker, daemon=True).start()
    root.wait_window(win)
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
