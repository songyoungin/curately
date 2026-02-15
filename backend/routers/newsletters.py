"""Newsletter route handlers."""

import logging
from collections import Counter
from datetime import UTC, date, datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status

from backend.schemas.articles import ArticleListItem, NewsletterListItem, NewsletterResponse
from backend.seed import DEFAULT_USER_EMAIL
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/newsletters", tags=["newsletters"])


def _get_default_user_id(client: Any) -> int | None:
    """Retrieve the default MVP user's ID.

    Args:
        client: Supabase client instance.

    Returns:
        The default user's ID, or None if the user does not exist.
    """
    result = client.table("users").select("id").eq("email", DEFAULT_USER_EMAIL).execute()
    if result.data:
        return cast(dict[str, Any], result.data[0])["id"]
    return None


def _enrich_with_interactions(
    client: Any, articles: list[dict[str, Any]], user_id: int
) -> list[dict[str, Any]]:
    """Add is_liked and is_bookmarked flags to articles based on user interactions.

    Args:
        client: Supabase client instance.
        articles: List of article dicts to enrich.
        user_id: The user whose interactions to query.

    Returns:
        The same list of article dicts with is_liked and is_bookmarked set.
    """
    if not articles:
        return articles

    article_ids = [a["id"] for a in articles]
    interactions = (
        client.table("interactions")
        .select("article_id, type")
        .eq("user_id", user_id)
        .in_("article_id", article_ids)
        .execute()
    )
    interaction_rows = cast(list[dict[str, Any]], interactions.data)

    liked_ids = {r["article_id"] for r in interaction_rows if r["type"] == "like"}
    bookmarked_ids = {r["article_id"] for r in interaction_rows if r["type"] == "bookmark"}

    for article in articles:
        article["is_liked"] = article["id"] in liked_ids
        article["is_bookmarked"] = article["id"] in bookmarked_ids
    return articles


def _fetch_newsletter_for_date(
    newsletter_date: date,
) -> NewsletterResponse:
    """Fetch articles for a given newsletter date and enrich with interactions.

    Args:
        newsletter_date: The date to query articles for.

    Returns:
        A NewsletterResponse with articles and their interaction status.
    """
    client = get_supabase_client()

    result = (
        client.table("articles")
        .select("*")
        .eq("newsletter_date", newsletter_date.isoformat())
        .order("relevance_score", desc=True)
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    if rows:
        user_id = _get_default_user_id(client)
        if user_id is not None:
            rows = _enrich_with_interactions(client, rows, user_id)
        else:
            for row in rows:
                row["is_liked"] = False
                row["is_bookmarked"] = False
    else:
        for row in rows:
            row["is_liked"] = False
            row["is_bookmarked"] = False

    articles = [ArticleListItem(**row) for row in rows]

    return NewsletterResponse(
        date=newsletter_date,
        article_count=len(articles),
        articles=articles,
    )


@router.get("", response_model=list[NewsletterListItem])
async def list_newsletters(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Return all newsletter editions with article counts.

    Args:
        limit: Maximum number of editions to return (1-100, default 30).
        offset: Number of editions to skip (default 0).

    Returns:
        List of newsletter editions sorted by date descending.
    """
    client = get_supabase_client()

    # Supabase client doesn't support GROUP BY, so we fetch all dates and group in Python
    result = (
        client.table("articles")
        .select("newsletter_date")
        .not_.is_("newsletter_date", "null")
        .order("newsletter_date", desc=True)
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    date_counts = Counter(row["newsletter_date"] for row in rows)
    sorted_dates = sorted(date_counts.keys(), reverse=True)
    paginated = sorted_dates[offset : offset + limit]

    return [{"date": d, "article_count": date_counts[d]} for d in paginated]


@router.get("/today", response_model=NewsletterResponse)
async def today_newsletter() -> NewsletterResponse:
    """Return today's newsletter edition.

    Returns articles published for today's date with interaction status.
    If no articles exist for today, returns an empty newsletter (200).
    """
    today = datetime.now(tz=UTC).date()
    return _fetch_newsletter_for_date(today)


@router.get("/{newsletter_date}", response_model=NewsletterResponse)
async def date_newsletter(newsletter_date: str) -> NewsletterResponse:
    """Return a specific date's newsletter edition.

    Args:
        newsletter_date: The date in YYYY-MM-DD format.

    Returns:
        The newsletter edition for the specified date.

    Raises:
        HTTPException: 422 if date format is invalid, 404 if no articles found.
    """
    try:
        parsed_date = date.fromisoformat(newsletter_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    response = _fetch_newsletter_for_date(parsed_date)

    if response.article_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No newsletter found for date {newsletter_date}",
        )

    return response
