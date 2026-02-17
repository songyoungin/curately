"""Pipeline route handlers for manual trigger and status."""

import logging

from fastapi import APIRouter, Header, HTTPException, status

from backend.config import get_settings
from backend.scheduler import run_weekly_rewind_for_all_users
from backend.services.pipeline import PipelineResult, run_daily_pipeline
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineResult)
async def trigger_pipeline(
    x_pipeline_token: str | None = Header(default=None, alias="X-Pipeline-Token"),
) -> PipelineResult:
    """Manually trigger the daily pipeline.

    Runs the full pipeline (collect, score, filter, summarize, persist)
    and returns result stats. Intended for development and testing.
    """
    logger.info("Manual pipeline trigger requested")
    settings = get_settings()
    expected_token = settings.pipeline_trigger_token
    if expected_token and x_pipeline_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid pipeline trigger token",
        )

    try:
        client = get_supabase_client()
        result = await run_daily_pipeline(client)
    except Exception as exc:
        logger.exception("Pipeline execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {type(exc).__name__}",
        ) from exc
    return result


@router.post("/rewind/run", status_code=204)
async def trigger_weekly_rewind(
    x_pipeline_token: str | None = Header(default=None, alias="X-Pipeline-Token"),
) -> None:
    """Manually trigger weekly rewind generation for all users."""
    settings = get_settings()
    expected_token = settings.pipeline_trigger_token
    if expected_token and x_pipeline_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid pipeline trigger token",
        )

    await run_weekly_rewind_for_all_users()
