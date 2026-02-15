"""Pipeline management route handlers.

Provides an endpoint to manually trigger the daily newsletter pipeline.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run")
async def trigger_pipeline() -> dict[str, Any]:
    """Manually trigger the daily newsletter pipeline.

    Runs the full pipeline (collect, score, filter, summarize, persist)
    and returns a summary of the results.

    Returns:
        Dict with pipeline execution status and article counts.
    """
    try:
        result = await run_daily_pipeline()
        return {
            "status": "success",
            "message": "Pipeline completed successfully",
            "articles_collected": result["articles_collected"],
            "articles_scored": result["articles_scored"],
            "articles_filtered": result["articles_filtered"],
            "articles_saved": result["articles_saved"],
            "newsletter_date": result["newsletter_date"],
        }
    except Exception as exc:
        logger.exception("Pipeline execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {exc}",
        ) from exc
