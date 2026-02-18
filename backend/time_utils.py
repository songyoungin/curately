"""Timezone helpers for date boundary logic."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def today_kst() -> date:
    """Return the current date in Asia/Seoul timezone."""
    return datetime.now(tz=KST).date()


def kst_midnight_utc_iso(target_date: date) -> str:
    """Return UTC ISO timestamp for the KST midnight of a given date."""
    midnight_kst = datetime.combine(target_date, time.min, tzinfo=KST)
    return midnight_kst.astimezone(UTC).isoformat()
