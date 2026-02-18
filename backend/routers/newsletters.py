"""Newsletter route handlers."""

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth import get_current_user_id
from backend.schemas.articles import NewsletterListItem, NewsletterResponse
from backend.supabase_client import get_supabase_client
from backend.time_utils import today_kst

router = APIRouter(prefix="/api/newsletters", tags=["newsletters"])


def _attach_interaction_flags(
    articles: list[dict[str, Any]], user_id: int
) -> list[dict[str, Any]]:
    """Attach is_liked and is_bookmarked flags to articles.

    Args:
        articles: List of article dicts from Supabase.
        user_id: The user ID to check interactions for.

    Returns:
        Articles with is_liked and is_bookmarked fields set.
    """
    if not articles:
        return articles

    article_ids = [a["id"] for a in articles]
    client = get_supabase_client()
    interactions_result = (
        client.table("interactions")
        .select("article_id, type")
        .eq("user_id", user_id)
        .in_("article_id", article_ids)
        .execute()
    )
    interactions = cast(list[dict[str, Any]], interactions_result.data)

    liked_ids: set[int] = set()
    bookmarked_ids: set[int] = set()
    for interaction in interactions:
        if interaction["type"] == "like":
            liked_ids.add(interaction["article_id"])
        elif interaction["type"] == "bookmark":
            bookmarked_ids.add(interaction["article_id"])

    for article in articles:
        article["is_liked"] = article["id"] in liked_ids
        article["is_bookmarked"] = article["id"] in bookmarked_ids

    return articles


_ARTICLE_LIST_COLUMNS = (
    "id, source_feed, source_url, title, author, published_at, "
    "summary, detailed_summary, relevance_score, categories, keywords, newsletter_date"
)


@router.get("", response_model=list[NewsletterListItem])
async def list_newsletters(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """List newsletter editions, paginated and sorted by date descending.

    Args:
        limit: Maximum number of editions to return.
        offset: Number of editions to skip.
    """
    client = get_supabase_client()
    result = (
        client.table("articles")
        .select("newsletter_date")
        .not_.is_("newsletter_date", "null")
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    counts: dict[str, int] = {}
    for row in rows:
        d = row["newsletter_date"]
        counts[d] = counts.get(d, 0) + 1

    editions = sorted(counts.items(), key=lambda x: x[0], reverse=True)
    page = editions[offset : offset + limit]
    return [{"date": d, "article_count": c} for d, c in page]


@router.get("/today", response_model=NewsletterResponse)
async def get_today_newsletter(
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return today's newsletter with articles sorted by relevance score."""
    today = today_kst()
    return _get_newsletter_by_date(today, user_id)


@router.get("/{newsletter_date}", response_model=NewsletterResponse)
async def get_newsletter_by_date(
    newsletter_date: date,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return a specific date's newsletter.

    Args:
        newsletter_date: The date in YYYY-MM-DD format.
        user_id: Injected by the JWT auth dependency.

    Raises:
        HTTPException: 404 if no articles exist for the given date.
    """
    return _get_newsletter_by_date(newsletter_date, user_id)


def _get_newsletter_by_date(target_date: date, user_id: int) -> dict[str, Any]:
    """Fetch articles for a specific newsletter date.

    Args:
        target_date: The newsletter date to fetch.
        user_id: The authenticated user's ID for interaction flags.

    Returns:
        Newsletter response dict with date, count, and articles.

    Raises:
        HTTPException: 404 if no articles found for the date.
    """
    client = get_supabase_client()
    result = (
        client.table("articles")
        .select(_ARTICLE_LIST_COLUMNS)
        .eq("newsletter_date", target_date.isoformat())
        .order("relevance_score", desc=True)
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No newsletter found for {target_date.isoformat()}",
        )

    articles = _attach_interaction_flags(rows, user_id)

    return {
        "date": target_date,
        "article_count": len(articles),
        "articles": articles,
    }
