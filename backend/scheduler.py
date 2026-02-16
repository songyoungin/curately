"""APScheduler integration for recurring pipeline jobs.

Provides daily pipeline and weekly rewind scheduling using AsyncIOScheduler.
Start and stop functions are designed to be called from the FastAPI lifespan.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import get_settings
from backend.services.pipeline import run_daily_pipeline
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with configured jobs.

    Registers the daily pipeline job and a weekly rewind stub,
    then starts the scheduler.

    Returns:
        The running scheduler instance.
    """
    global _scheduler  # noqa: PLW0603

    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    # Daily pipeline job
    _scheduler.add_job(
        _run_daily_pipeline_job,
        trigger="cron",
        hour=settings.schedule.daily_pipeline_hour,
        minute=settings.schedule.daily_pipeline_minute,
        id="daily_pipeline",
        name="Daily newsletter pipeline",
        replace_existing=True,
    )
    logger.info(
        "Scheduled daily pipeline at %02d:%02d",
        settings.schedule.daily_pipeline_hour,
        settings.schedule.daily_pipeline_minute,
    )

    # Weekly rewind job (stub)
    _scheduler.add_job(
        _run_weekly_rewind_job,
        trigger="cron",
        day_of_week=settings.schedule.rewind_day_of_week,
        hour=settings.schedule.rewind_hour,
        minute=settings.schedule.rewind_minute,
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
    """Execute the weekly rewind analysis (stub)."""
    logger.info("Weekly rewind job triggered (not yet implemented)")
