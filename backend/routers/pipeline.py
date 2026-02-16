"""Pipeline route handlers for manual trigger and status."""

import logging

from fastapi import APIRouter, HTTPException, status

from backend.services.pipeline import PipelineResult, run_daily_pipeline
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineResult)
async def trigger_pipeline() -> PipelineResult:
    """Manually trigger the daily pipeline.

    Runs the full pipeline (collect, score, filter, summarize, persist)
    and returns result stats. Intended for development and testing.
    """
    logger.info("Manual pipeline trigger requested")
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
