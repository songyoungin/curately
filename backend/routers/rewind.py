"""Rewind report route handlers."""

from datetime import timedelta, timezone
from datetime import datetime as dt
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status

from backend.schemas.rewind import RewindReportResponse
from backend.seed import DEFAULT_USER_EMAIL
from backend.services.rewind import generate_rewind_report, persist_rewind_report
from backend.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/rewind", tags=["rewind"])


def _get_default_user_id() -> int:
    """Fetch the default MVP user's ID from the database.

    Returns:
        The user ID for the default user.

    Raises:
        HTTPException: If the default user is not found.
    """
    client = get_supabase_client()
    result = (
        client.table("users").select("id").eq("email", DEFAULT_USER_EMAIL).execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user not found",
        )
    row = cast(dict[str, Any], result.data[0])
    return cast(int, row["id"])


@router.get("/latest", response_model=RewindReportResponse)
async def get_latest_rewind() -> dict[str, Any]:
    """Return the most recent rewind report for the default user.

    Raises:
        HTTPException: 404 if no reports exist.
    """
    client = get_supabase_client()
    user_id = _get_default_user_id()

    result = (
        client.table("rewind_reports")
        .select("*")
        .eq("user_id", user_id)
        .order("period_end", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rewind reports found",
        )

    return rows[0]


@router.get("/{report_id}", response_model=RewindReportResponse)
async def get_rewind_by_id(report_id: int) -> dict[str, Any]:
    """Return a specific rewind report by ID.

    Args:
        report_id: The report ID to fetch.

    Raises:
        HTTPException: 404 if report not found.
    """
    client = get_supabase_client()

    result = client.table("rewind_reports").select("*").eq("id", report_id).execute()
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rewind report {report_id} not found",
        )

    return rows[0]


@router.post("/generate", response_model=RewindReportResponse, status_code=201)
async def generate_rewind() -> dict[str, Any]:
    """Trigger generation of a new weekly rewind report.

    Calculates the period as the last 7 days and generates a comparative
    analysis using Gemini.

    Returns:
        The newly created rewind report.
    """
    client = get_supabase_client()
    user_id = _get_default_user_id()

    today = dt.now(timezone.utc).date()
    period_start = today - timedelta(days=7)
    period_end = today

    report = await generate_rewind_report(client, user_id)
    report_id = await persist_rewind_report(
        client, user_id, report, period_start, period_end
    )

    # Fetch the persisted row to return full response
    result = client.table("rewind_reports").select("*").eq("id", report_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    return rows[0]
