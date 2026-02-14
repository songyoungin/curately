"""Rewind report schemas."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class RewindReportResponse(BaseModel):
    """Weekly rewind report."""

    id: int
    period_start: date
    period_end: date
    report_content: dict[str, Any] | None = None
    hot_topics: list[str] | None = None
    trend_changes: dict[str, Any] | None = None
    created_at: datetime
