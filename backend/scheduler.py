"""APScheduler integration for daily pipeline execution.

Configures and manages the async scheduler that triggers the
daily newsletter pipeline at the configured time (default 06:00).
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import get_settings
from backend.services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def init_scheduler() -> None:
    """Initialize and start the scheduler with the daily pipeline job.

    Reads schedule configuration from settings and adds a cron trigger
    for the daily pipeline. Replaces any existing job with the same ID.
    """
    settings = get_settings()
    scheduler.add_job(
        run_daily_pipeline,
        "cron",
        hour=settings.schedule.daily_pipeline_hour,
        minute=settings.schedule.daily_pipeline_minute,
        id="daily_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: daily pipeline at %02d:%02d",
        settings.schedule.daily_pipeline_hour,
        settings.schedule.daily_pipeline_minute,
    )


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler if it is running."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
