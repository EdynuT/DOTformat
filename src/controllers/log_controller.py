"""Tkinter controller for viewing recent conversion logs."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import os
from ..services.conversion_service import ConversionService
from typing import List, Tuple, Any, Optional

class LogController:
    def __init__(self) -> None:
        self.service = ConversionService()

    def open_window(self, parent: tk.Tk | tk.Toplevel) -> None:
        self._data_cache: List[Tuple[Any, ...]] = []  # all cached rows
        self._current_view: List[Tuple[Any, ...]] = []  # rows after filters applied (used for export)
        self._sort_state: dict[str, bool] = {}  # col -> ascending(bool)

        win = tk.Toplevel(parent)
        win.title("Conversion History")
        win.geometry("1150x480")
        win.resizable(True, True)

        # Search / filter frame
        filter_frame = ttk.Frame(win, padding=(6,6,6,0))
        filter_frame.pack(fill=tk.X)
        ttk.Label(filter_frame, text="Search ID/Username:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(4,10))

        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT)
        status_var = tk.StringVar(value="ALL")
        status_cb = ttk.Combobox(filter_frame, textvariable=status_var, values=["ALL","SUCCESS","ERROR"], width=10, state="readonly")
        status_cb.pack(side=tk.LEFT, padx=(4,10))

        def apply_filters(*_):
            self._apply_filters(tree, search_var.get().strip(), status_var.get())

        search_entry.bind("<Return>", lambda e: apply_filters())
        status_cb.bind("<<ComboboxSelected>>", lambda e: apply_filters())

        # Treeview
        columns = ("id", "username", "feature", "input", "output", "status", "detail", "created")
        tree = ttk.Treeview(win, columns=columns, show="headings")
        headers = {
            "id": "ID",
            "username": "User",
            "feature": "Feature",
            "input": "Input",
            "output": "Output",
            "status": "Status",
            "detail": "Detail",
            "created": "Created"
        }

        def make_sort_cmd(col: str):
            def _cmd():
                asc = self._sort_state.get(col, True)
                self._sort_state[col] = not asc  # toggle for next time
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

        # Buttons
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Button(btn_frame, text="Refresh", command=lambda: self._reload(tree, search_var, status_var)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Export", command=lambda: self._export_dialog(win)).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(btn_frame, text="Clear Filters", command=lambda: (search_var.set(""), status_var.set("ALL"), apply_filters())).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side=tk.RIGHT)

        # Initial population
        self._reload(tree, search_var, status_var)

    def _populate(self, tree: ttk.Treeview) -> None:
        # Keep original method for backward compatibility (now wrappers call _reload/_apply_filters)
        self._reload(tree, tk.StringVar(value=""), tk.StringVar(value="ALL"))

    # New helpers
    def _reload(self, tree: ttk.Treeview, search_var: tk.StringVar, status_var: tk.StringVar):
        self._data_cache.clear()
        for rec in self.service.recent(limit=500):
            # rec layout: (id, feature, input, output, status, detail, username, created)
            reordered = (rec[0], rec[6], rec[1], rec[2], rec[3], rec[4], rec[5], rec[7])
            self._data_cache.append(reordered)
        self._apply_filters(tree, search_var.get().strip(), status_var.get())

    def _apply_filters(self, tree: ttk.Treeview, search: str, status_filter: str):
        for row in tree.get_children(): tree.delete(row)
        self._current_view.clear()
        s = search.lower()
        for r in self._data_cache:
            # r = (id, username, feature, input, output, status, detail, created)
            if status_filter != "ALL" and r[5] != status_filter:
                continue
            if s:
                # match against id (string), username, feature, input, output, detail
                id_str = str(r[0])
                hay = [id_str, *(str(x or '').lower() for x in r[1:7])]
                if not any(s in h for h in hay):
                    continue
            tree.insert("", "end", values=r)
            self._current_view.append(r)

    def _sort(self, tree: ttk.Treeview, col: str, ascending: bool = True):
        if not self._data_cache:
            return
        idx_map = {"id":0, "username":1, "feature":2, "input":3, "output":4, "status":5, "detail":6, "created":7}
        idx = idx_map[col]
        # Try numeric cast for id
        def sort_key(row):
            val = row[idx]
            if col == 'id':
                try: return int(val)
                except Exception: return 0
            return (val or "").lower()
        self._data_cache.sort(key=sort_key, reverse=not ascending)
        # Re-apply current visible filters (no stored filters -> show all)
        for row in tree.get_children(): tree.delete(row)
        for r in self._data_cache:
            tree.insert("", "end", values=r)

    # Export helpers
    def _export_dialog(self, parent):
        # Ask user for format
        fmt_win = tk.Toplevel(parent)
        fmt_win.title("Export Format")
        fmt_win.resizable(False, False)
        ttk.Label(fmt_win, text="Choose export format:").pack(padx=12, pady=(12,6))
        choice = tk.StringVar(value="csv")
        for text,val in (("CSV","csv"),("XLSX","xlsx")):
            ttk.Radiobutton(fmt_win, text=text, value=val, variable=choice).pack(anchor='w', padx=16)

        def go():
            fmt = choice.get()
            ext = f".{fmt}"
            filetypes = [(fmt.upper(), f"*{ext}"), ("All Files","*.*")]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"DOTformat_Log_{ts}{ext}"
            # Default initial directory: user's Downloads
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(downloads_dir):
                downloads_dir = os.path.expanduser("~")
            path = filedialog.asksaveasfilename(parent=fmt_win, title="Save as", defaultextension=ext, initialfile=default_name, initialdir=downloads_dir, filetypes=filetypes)
            if not path:
                return
            fmt_win.destroy()
            self._do_export(path, fmt)
        ttk.Button(fmt_win, text="Export", command=go).pack(pady=(8,4))
        ttk.Button(fmt_win, text="Cancel", command=fmt_win.destroy).pack(pady=(0,10))

    def _do_export(self, path: str, fmt: str):
        try:
            # Export only currently filtered rows; if empty, warn
            rows = self._current_view
            if not rows:
                messagebox.showwarning("Warning", "No rows to export (adjust filters).")
                return
            # rows entries are already reordered (id, username, feature, input, output, status, detail, created)
            if fmt == 'csv':
                import csv
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    for r in rows:
                        writer.writerow(r)
            else:  # xlsx
                try:
                    from openpyxl import Workbook
                except ImportError:
                    messagebox.showerror("Error", "Package 'openpyxl' not installed. Add 'openpyxl' to requirements.txt")
                    return
                wb = Workbook(); ws = wb.active; ws.title = "logs"
                for r in rows:
                    ws.append(list(r))
                try: wb.save(path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save XLSX: {e}")
                    return
            messagebox.showinfo("Success", f"Exported to: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
