"""Tkinter dialog for browsing/exporting the conversion history.

Business/data logic (filtering, sorting, exporting, maintenance) lives in
`services.log_service.LogService`; this module only manages widgets.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from typing import List

from ...services.log_service import LogService, COLUMNS, Row


class HistoryDialog:
    def __init__(self) -> None:
        self.service = LogService()
        self._data_cache: List[Row] = []
        self._current_view: List[Row] = []
        self._sort_state: dict[str, bool] = {}

    def open_window(self, parent: tk.Tk | tk.Toplevel) -> None:
        win = tk.Toplevel(parent)
        win.title("Conversion History")
        win.geometry("1150x480")
        win.resizable(True, True)

        filter_frame = ttk.Frame(win, padding=(6, 6, 6, 0))
        filter_frame.pack(fill=tk.X)
        ttk.Label(filter_frame, text="Search ID/Username:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT)
        status_var = tk.StringVar(value="ALL")
        status_cb = ttk.Combobox(filter_frame, textvariable=status_var, values=["ALL", "SUCCESS", "ERROR"], width=10, state="readonly")
        status_cb.pack(side=tk.LEFT, padx=(4, 10))

        def apply_filters(*_):
            self._apply_filters(tree, search_var.get().strip(), status_var.get())

        search_entry.bind("<Return>", lambda e: apply_filters())
        status_cb.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        tree = ttk.Treeview(win, columns=COLUMNS, show="headings")
        headers = {
            "id": "ID", "username": "User", "feature": "Feature", "input": "Input",
            "output": "Output", "status": "Status", "detail": "Detail", "created": "Created"
        }

        def make_sort_cmd(col: str):
            def _cmd():
                asc = self._sort_state.get(col, True)
                self._sort_state[col] = not asc
                self._sort(tree, col, ascending=asc)
            return _cmd

        for col, text in headers.items():
            tree.heading(col, text=text, command=make_sort_cmd(col))
            if col == "detail":
                width = 260
            elif col == "id":
                width = 60
            elif col == "username":
                width = 120
            else:
                width = 130
            tree.column(col, width=width, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(btn_frame, text="Refresh", command=lambda: self._reload(tree, search_var, status_var)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Export", command=lambda: self._export_dialog(win)).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_frame, text="Clear Filters", command=lambda: (search_var.set(""), status_var.set("ALL"), apply_filters())).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_frame, text="Normalize IDs", command=lambda: self._normalize_ids(win, tree, search_var, status_var)).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(btn_frame, text="Restore Old Log", command=lambda: self._restore_from_backup(win, tree, search_var, status_var)).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side=tk.RIGHT)

        self._reload(tree, search_var, status_var)

    def _reload(self, tree: ttk.Treeview, search_var: tk.StringVar, status_var: tk.StringVar) -> None:
        self._data_cache = self.service.fetch_rows(limit=500)
        self._apply_filters(tree, search_var.get().strip(), status_var.get())

    def _apply_filters(self, tree: ttk.Treeview, search: str, status_filter: str) -> None:
        for row in tree.get_children():
            tree.delete(row)
        self._current_view = self.service.filter_rows(self._data_cache, search, status_filter)
        for r in self._current_view:
            tree.insert("", "end", values=r)

    def _sort(self, tree: ttk.Treeview, col: str, ascending: bool = True) -> None:
        if not self._data_cache:
            return
        self._data_cache = self.service.sort_rows(self._data_cache, col, ascending=ascending)
        for row in tree.get_children():
            tree.delete(row)
        for r in self._data_cache:
            tree.insert("", "end", values=r)

    def _export_dialog(self, parent) -> None:
        fmt_win = tk.Toplevel(parent)
        fmt_win.title("Export Format")
        fmt_win.resizable(False, False)
        ttk.Label(fmt_win, text="Choose export format:").pack(padx=12, pady=(12, 6))
        choice = tk.StringVar(value="csv")
        for text, val in (("CSV", "csv"), ("XLSX", "xlsx")):
            ttk.Radiobutton(fmt_win, text=text, value=val, variable=choice).pack(anchor='w', padx=16)

        def go():
            fmt = choice.get()
            ext = f".{fmt}"
            filetypes = [(fmt.upper(), f"*{ext}"), ("All Files", "*.*")]
            default_name = self.service.default_export_filename(fmt)
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(downloads_dir):
                downloads_dir = os.path.expanduser("~")
            path = filedialog.asksaveasfilename(parent=fmt_win, title="Save as", defaultextension=ext, initialfile=default_name, initialdir=downloads_dir, filetypes=filetypes)
            if not path:
                return
            fmt_win.destroy()
            self._do_export(path, fmt)
        ttk.Button(fmt_win, text="Export", command=go).pack(pady=(8, 4))
        ttk.Button(fmt_win, text="Cancel", command=fmt_win.destroy).pack(pady=(0, 10))

    def _do_export(self, path: str, fmt: str) -> None:
        rows = self._current_view
        if not rows:
            messagebox.showwarning("Warning", "No rows to export (adjust filters).")
            return
        try:
            self.service.export_rows(rows, path, fmt)
            messagebox.showinfo("Success", f"Exported to: {path}")
        except ImportError:
            messagebox.showerror("Error", "Package 'openpyxl' not installed. Add 'openpyxl' to requirements.txt")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def _normalize_ids(self, parent: tk.Tk | tk.Toplevel, tree: ttk.Treeview, search_var: tk.StringVar, status_var: tk.StringVar) -> None:
        prog = tk.Toplevel(parent)
        prog.title("Updating database…")
        prog.geometry("360x110")
        prog.resizable(False, False)
        prog.grab_set()
        ttk.Label(prog, text="Renumbering log IDs (oldest → 1)…").pack(pady=(10, 4))
        var = tk.DoubleVar(value=0.0)
        bar = ttk.Progressbar(prog, mode='determinate', maximum=100, variable=var, length=300)
        bar.pack(pady=8)

        def report(pct: float):
            try:
                var.set(pct)
                bar.update_idletasks()
            except Exception:
                pass

        def worker():
            try:
                ok, msg, _ = self.service.normalize_ids(progress=report)
                prog.after(0, lambda: (var.set(100), bar.update_idletasks()))
                if ok:
                    messagebox.showinfo("Done", msg, parent=prog)
                    self._reload(tree, search_var, status_var)
                else:
                    messagebox.showerror("Error", msg, parent=prog)
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}", parent=prog)
            finally:
                try:
                    prog.destroy()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _restore_from_backup(self, parent: tk.Tk | tk.Toplevel, tree: ttk.Treeview, search_var: tk.StringVar, status_var: tk.StringVar) -> None:
        if not messagebox.askyesno("Confirm", "Restore previous log snapshot? This will replace the current log table.", parent=parent):
            return
        try:
            ok, msg = self.service.restore_from_backup()
            if ok:
                messagebox.showinfo("Done", msg, parent=parent)
                self._reload(tree, search_var, status_var)
            else:
                messagebox.showwarning("Info", msg, parent=parent)
        except Exception as e:
            messagebox.showerror("Error", f"Restore failed: {e}", parent=parent)


__all__ = ["HistoryDialog"]
