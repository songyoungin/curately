"""APScheduler integration for recurring pipeline jobs.

Provides daily pipeline and weekly rewind scheduling using AsyncIOScheduler.
Start and stop functions are designed to be called from the FastAPI lifespan.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import get_settings
from backend.services.pipeline import run_daily_pipeline
from backend.services.rewind import generate_rewind_report, persist_rewind_report
from backend.supabase_client import get_supabase_client
from backend.time_utils import today_kst

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_KST = ZoneInfo("Asia/Seoul")


def start_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with configured jobs.

    Registers the daily pipeline job and weekly rewind analysis,
    then starts the scheduler.

    Returns:
        The running scheduler instance.
    """
    global _scheduler  # noqa: PLW0603

    settings = get_settings()
    _scheduler = AsyncIOScheduler(timezone=_KST)

    # Daily pipeline job
    _scheduler.add_job(
        _run_daily_pipeline_job,
        trigger="cron",
        hour=settings.schedule.daily_pipeline_hour,
        minute=settings.schedule.daily_pipeline_minute,
        timezone=_KST,
        id="daily_pipeline",
        name="Daily newsletter pipeline",
        replace_existing=True,
    )
    logger.info(
        "Scheduled daily pipeline at %02d:%02d",
        settings.schedule.daily_pipeline_hour,
        settings.schedule.daily_pipeline_minute,
    )

    # Weekly rewind job
    _scheduler.add_job(
        _run_weekly_rewind_job,
        trigger="cron",
        day_of_week=settings.schedule.rewind_day_of_week,
        hour=settings.schedule.rewind_hour,
        minute=settings.schedule.rewind_minute,
        timezone=_KST,
        id="weekly_rewind",
        name="Weekly rewind analysis",
        replace_existing=True,
    )
    logger.info(
        "Scheduled weekly rewind on %s at %02d:%02d",
        settings.schedule.rewind_day_of_week,
        settings.schedule.rewind_hour,
        settings.schedule.rewind_minute,
    )

    _scheduler.start()
    logger.info("Scheduler started")
    return _scheduler


def stop_scheduler() -> None:
    """Stop the running scheduler gracefully."""
    global _scheduler  # noqa: PLW0603

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        _scheduler = None


async def _run_daily_pipeline_job() -> None:
    """Execute the daily pipeline as a scheduled job."""
    logger.info("Scheduled daily pipeline triggered")
    try:
        client = get_supabase_client()
        result = await run_daily_pipeline(client)
        logger.info("Scheduled pipeline complete: %s", result)
    except Exception:
        logger.exception("Scheduled daily pipeline failed")


async def _run_weekly_rewind_job() -> None:
    """Execute the weekly rewind analysis for all users."""
    logger.info("Weekly rewind job triggered")
    await run_weekly_rewind_for_all_users()


async def run_weekly_rewind_for_all_users() -> None:
    """Run weekly rewind generation for every user in the database."""
    try:
        client = get_supabase_client()
        settings = get_settings()

        users = _get_all_users(client)
        if not users:
            logger.warning("No users found, skipping rewind")
            return

        period_end = today_kst()
        period_start = period_end - timedelta(days=7)

        for user in users:
            user_id = int(user["id"])
            try:
                report = await generate_rewind_report(client, user_id, settings)
                report_id = await persist_rewind_report(
                    client, user_id, report, period_start, period_end
                )
                logger.info(
                    "Weekly rewind complete: user_id=%d, report_id=%d, period=%s to %s",
                    user_id,
                    report_id,
                    period_start,
                    period_end,
                )
            except Exception:
                logger.exception("Rewind failed for user_id=%d", user_id)
    except Exception:
        logger.exception("Weekly rewind job failed")


def _get_all_users(client: Any) -> list[dict[str, Any]]:
    """Fetch all user IDs from the database.

    Args:
        client: Supabase client instance.

    Returns:
        List of user rows with at least an 'id' field.
    """
    response = client.table("users").select("id").execute()
    return cast(list[dict[str, Any]], response.data)
