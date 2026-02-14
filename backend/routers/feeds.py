"""Feed management route handlers."""

import logging
from urllib.parse import urlparse

import feedparser
import httpx
from fastapi import APIRouter, HTTPException, status

from backend.schemas.feeds import FeedCreate, FeedResponse, FeedUpdate
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


async def _validate_feed_url(url: str) -> None:
    """RSS 피드 URL의 유효성을 검증한다.

    Args:
        url: 검증할 RSS 피드 URL.

    Raises:
        HTTPException: URL 형식이 잘못되었거나 유효한 RSS 피드가 아닌 경우.
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
async def list_feeds() -> list[dict]:
    """등록된 모든 피드 목록을 반환한다."""
    supabase = get_supabase_client()
    result = (
        supabase.table("feeds").select("*").order("created_at", desc=True).execute()
    )
    return result.data


@router.post("", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(body: FeedCreate) -> dict:
    """새로운 RSS 피드를 등록한다.

    Args:
        body: 피드 이름과 URL.
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
    return result.data[0]


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(feed_id: int) -> None:
    """피드를 삭제한다.

    Args:
        feed_id: 삭제할 피드의 ID.
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
async def update_feed(feed_id: int, body: FeedUpdate) -> dict:
    """피드의 활성 상태를 변경한다.

    Args:
        feed_id: 변경할 피드의 ID.
        body: 변경할 활성 상태.
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
    return result.data[0]
