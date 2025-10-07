"""Tkinter controller for viewing recent conversion logs."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from ..services.conversion_service import ConversionService

class LogController:
    def __init__(self) -> None:
        self.service = ConversionService()

    def open_window(self, parent: tk.Tk | tk.Toplevel) -> None:
        win = tk.Toplevel(parent)
        win.title("Conversion History")
        win.geometry("940x360")
        win.resizable(True, True)
        # Display order: ID | User | Feature | Input | Output | Status | Detail | Created
        # Underlying record order remains (id, feature, input, output, status, detail, username, created)
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
        for col, text in headers.items():
            tree.heading(col, text=text)
            if col == "detail":
                width = 260
            elif col == "id":
                width = 50
            elif col == "username":
                width = 110
            else:
                width = 120
            tree.column(col, width=width, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Button(btn_frame, text="Refresh", command=lambda: self._populate(tree)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side=tk.RIGHT)

        self._populate(tree)

    def _populate(self, tree: ttk.Treeview) -> None:
        for row in tree.get_children():
            tree.delete(row)
        for rec in self.service.recent(limit=200):
            # rec = (id, feature, input, output, status, detail, username, created)
            reordered = (rec[0], rec[6], rec[1], rec[2], rec[3], rec[4], rec[5], rec[7])
            tree.insert("", "end", values=reordered)
