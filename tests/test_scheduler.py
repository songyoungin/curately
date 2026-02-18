"""Scheduler timezone tests."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from backend.scheduler import run_weekly_rewind_for_all_users, start_scheduler


@pytest.mark.asyncio
@patch("backend.scheduler.today_kst", return_value=date(2026, 2, 17))
@patch("backend.scheduler.persist_rewind_report", new_callable=AsyncMock)
@patch("backend.scheduler.generate_rewind_report", new_callable=AsyncMock)
@patch("backend.scheduler.get_settings")
@patch("backend.scheduler.get_supabase_client")
async def test_weekly_rewind_uses_kst_period(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
    mock_generate: AsyncMock,
    mock_persist: AsyncMock,
    _mock_today_kst: MagicMock,
) -> None:
    """Verify weekly rewind period boundaries are computed in KST."""
    users_table = MagicMock()
    users_table.select.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    client = MagicMock()
    client.table.return_value = users_table
    mock_get_client.return_value = client

    mock_get_settings.return_value = MagicMock()
    mock_generate.return_value = {
        "overview": "",
        "hot_topics": [],
        "trend_changes": {"rising": [], "declining": []},
        "suggestions": [],
    }
    mock_persist.return_value = 1

    await run_weekly_rewind_for_all_users()

    persist_call = mock_persist.call_args
    assert persist_call is not None
    assert persist_call.args[3] == date(2026, 2, 10)
    assert persist_call.args[4] == date(2026, 2, 17)


@patch("backend.scheduler.get_settings")
@patch("backend.scheduler.AsyncIOScheduler")
def test_start_scheduler_uses_kst_timezone(
    mock_scheduler_cls: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """Verify internal APScheduler is configured to Asia/Seoul timezone."""
    scheduler = MagicMock()
    mock_scheduler_cls.return_value = scheduler

    settings = MagicMock()
    settings.schedule.daily_pipeline_hour = 6
    settings.schedule.daily_pipeline_minute = 0
    settings.schedule.rewind_day_of_week = "sun"
    settings.schedule.rewind_hour = 23
    settings.schedule.rewind_minute = 0
    mock_get_settings.return_value = settings

    start_scheduler()

    kst = ZoneInfo("Asia/Seoul")
    mock_scheduler_cls.assert_called_once_with(timezone=kst)

    first_call = scheduler.add_job.call_args_list[0]
    second_call = scheduler.add_job.call_args_list[1]

    assert first_call.kwargs["timezone"] == kst
    assert second_call.kwargs["timezone"] == kst
