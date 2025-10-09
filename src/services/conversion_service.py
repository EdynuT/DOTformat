"""Service layer for logging conversions.

Encapsulates business rules (minimal now) and provides a stable API to controllers/UI.
"""
from __future__ import annotations
from typing import List
from ..repositories.conversion_repository import ConversionRepository, Row

class ConversionService:
    def __init__(self) -> None:
        self.repo = ConversionRepository()

    def log_success(self, feature: str, input_path: str | None, output_path: str | None, username: str | None = None, detail: str | None = None) -> None:
        compact = self._compact(detail)
        self.repo.add(feature, input_path, output_path, status="success", detail=compact, username=username)

    def log_error(self, feature: str, input_path: str | None, error: str, username: str | None = None) -> None:
        compact = self._compact(error)
        self.repo.add(feature, input_path, None, status="error", detail=compact, username=username)

    @staticmethod
    def _compact(detail: str | None) -> str | None:
        if not detail:
            return None
        # Keep details concise (first line up to 140 chars)
        first_line = detail.strip().splitlines()[0]
        return (first_line[:140] + ('…' if len(first_line) > 140 else ''))

    def recent(self, limit: int = 50) -> List[Row]:
        return self.repo.list_last(limit=limit)

    def all(self) -> List[Row]:
        """Return all log rows (no limit)."""
        return self.repo.list_all()
