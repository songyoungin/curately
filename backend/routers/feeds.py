"""Feed management route handlers."""

import logging
from typing import Any, cast
from urllib.parse import urlparse

import feedparser
import httpx
from fastapi import APIRouter, HTTPException, status

from backend.schemas.feeds import FeedCreate, FeedResponse, FeedUpdate
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


async def _validate_feed_url(url: str) -> None:
    """Validate that a URL points to a valid RSS feed.

    Args:
        url: RSS feed URL to validate.

    Raises:
        HTTPException: If URL format is invalid or not a valid RSS feed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning("Feed URL returned HTTP %s: %s", e.response.status_code, url)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Feed URL returned HTTP {e.response.status_code}",
        ) from e
    except httpx.RequestError as e:
        logger.warning("Failed to fetch feed URL %s: %s", url, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to fetch feed URL",
        ) from e

    feed = feedparser.parse(response.text)
    if feed.bozo and not feed.entries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL is not a valid RSS feed",
        )


@router.get("", response_model=list[FeedResponse])
async def list_feeds() -> list[dict[str, Any]]:
    """Return all registered feeds."""
    supabase = get_supabase_client()
    result = (
        supabase.table("feeds").select("*").order("created_at", desc=True).execute()
    )
    return cast(list[dict[str, Any]], result.data)


@router.post("", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(body: FeedCreate) -> dict[str, Any]:
    """Register a new RSS feed.

    Args:
        body: Feed name and URL.
    """
    await _validate_feed_url(body.url)

    supabase = get_supabase_client()

    existing = supabase.table("feeds").select("id").eq("url", body.url).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feed with this URL already exists",
        )

    result = (
        supabase.table("feeds").insert({"name": body.name, "url": body.url}).execute()
    )
    return cast(dict[str, Any], result.data[0])


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(feed_id: int) -> None:
    """Delete a feed.

    Args:
        feed_id: ID of the feed to delete.
    """
    supabase = get_supabase_client()

    existing = supabase.table("feeds").select("id").eq("id", feed_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found",
        )

    supabase.table("feeds").delete().eq("id", feed_id).execute()


@router.patch("/{feed_id}", response_model=FeedResponse)
async def update_feed(feed_id: int, body: FeedUpdate) -> dict[str, Any]:
    """Update a feed's active status.

    Args:
        feed_id: ID of the feed to update.
        body: New active status.
    """
    supabase = get_supabase_client()

    existing = supabase.table("feeds").select("id").eq("id", feed_id).execute()
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found",
        )

    result = (
        supabase.table("feeds")
        .update({"is_active": body.is_active})
        .eq("id", feed_id)
        .execute()
    )
    return cast(dict[str, Any], result.data[0])
