"""Business/data logic for the conversion log history view.

Keeps row fetching, filtering, sorting, exporting and maintenance operations
free of any Tkinter dependency; the history dialog only handles widgets.
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from .conversion_service import ConversionService
from ..db.maintenance import normalize_conversion_log_ids, restore_log_from_backup

# Reordered row: (id, username, feature, input, output, status, detail, created)
Row = Tuple[object, ...]

COLUMNS = ("id", "username", "feature", "input", "output", "status", "detail", "created")
_COLUMN_INDEX = {name: i for i, name in enumerate(COLUMNS)}


class LogService:
    def __init__(self) -> None:
        self.conversion_service = ConversionService()

    def fetch_rows(self, limit: int = 500) -> List[Row]:
        rows: List[Row] = []
        for rec in self.conversion_service.recent(limit=limit):
            # rec layout: (id, feature, input, output, status, detail, username, created)
            rows.append((rec[0], rec[6], rec[1], rec[2], rec[3], rec[4], rec[5], rec[7]))
        return rows

    def filter_rows(self, rows: List[Row], search: str, status_filter: str) -> List[Row]:
        s = search.strip().lower()
        result: List[Row] = []
        for r in rows:
            if status_filter != "ALL" and r[5] != status_filter:
                continue
            if s:
                id_str = str(r[0])
                hay = [id_str, *(str(x or '').lower() for x in r[1:7])]
                if not any(s in h for h in hay):
                    continue
            result.append(r)
        return result

    def sort_rows(self, rows: List[Row], col: str, ascending: bool = True) -> List[Row]:
        idx = _COLUMN_INDEX[col]

        def sort_key(row: Row):
            val = row[idx]
            if col == 'id':
                try:
                    return int(val)
                except Exception:
                    return 0
            return (val or "").lower()

        return sorted(rows, key=sort_key, reverse=not ascending)

    def export_rows(self, rows: List[Row], path: str, fmt: str) -> None:
        if fmt == 'csv':
            import csv
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for r in rows:
                    writer.writerow(r)
        elif fmt == 'xlsx':
            from openpyxl import Workbook  # type: ignore
            wb = Workbook()
            ws = wb.active
            ws.title = "logs"
            for r in rows:
                ws.append(list(r))
            wb.save(path)
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

    @staticmethod
    def default_export_filename(fmt: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"DOTformat_Log_{ts}.{fmt}"

    def normalize_ids(self, progress: Optional[Callable[[float], None]] = None) -> tuple[bool, str, int]:
        return normalize_conversion_log_ids(progress=progress)

    def restore_from_backup(self) -> tuple[bool, str]:
        return restore_log_from_backup()


__all__ = ["LogService", "COLUMNS"]
