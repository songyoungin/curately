"""Daily digest route handlers."""

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth import get_current_user_id
from backend.schemas.digest import DigestResponse
from backend.services.digest import generate_daily_digest, persist_digest
from backend.supabase_client import get_supabase_client
from backend.time_utils import today_kst

router = APIRouter(prefix="/api/digests", tags=["digests"])


@router.get("/today", response_model=DigestResponse)
async def get_today_digest(
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return today's digest."""
    client = get_supabase_client()
    today = today_kst().isoformat()

    result = client.table("digests").select("*").eq("digest_date", today).execute()
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No digest found for today",
        )

    return rows[0]


@router.get("", response_model=list[DigestResponse])
async def list_digests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """List digests in reverse chronological order with pagination."""
    client = get_supabase_client()

    result = (
        client.table("digests")
        .select("*")
        .order("digest_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return cast(list[dict[str, Any]], result.data)


@router.get("/{digest_date}", response_model=DigestResponse)
async def get_digest_by_date(
    digest_date: date,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return digest for the specified date."""
    client = get_supabase_client()

    result = (
        client.table("digests")
        .select("*")
        .eq("digest_date", digest_date.isoformat())
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No digest found for {digest_date}",
        )

    return rows[0]


@router.post("/generate", response_model=DigestResponse, status_code=201)
async def generate_digest(
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate (or regenerate) today's digest."""
    client = get_supabase_client()
    today = today_kst().isoformat()

    count_result = (
        client.table("articles")
        .select("id", count="exact")  # type: ignore[arg-type]
        .eq("newsletter_date", today)
        .execute()
    )
    if not count_result.count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No articles found for {today}, cannot generate digest",
        )

    content, article_ids = await generate_daily_digest(client, today)

    if not content["headline"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Digest generation failed (LLM returned empty result)",
        )

    digest_id = await persist_digest(client, today, content, article_ids)

    result = client.table("digests").select("*").eq("id", digest_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    return rows[0]


@router.post("/generate/{digest_date}", response_model=DigestResponse, status_code=201)
async def generate_digest_for_date(
    digest_date: date,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate (or regenerate) digest for the specified date."""
    client = get_supabase_client()
    date_str = digest_date.isoformat()

    count_result = (
        client.table("articles")
        .select("id", count="exact")  # type: ignore[arg-type]
        .eq("newsletter_date", date_str)
        .execute()
    )
    if not count_result.count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No articles found for {date_str}, cannot generate digest",
        )

    content, article_ids = await generate_daily_digest(client, date_str)

    if not content["headline"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Digest generation failed (LLM returned empty result)",
        )

    digest_id = await persist_digest(client, date_str, content, article_ids)

    result = client.table("digests").select("*").eq("id", digest_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    return rows[0]
