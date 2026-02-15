"""Article route handlers."""

import logging
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status

from backend.schemas.articles import ArticleDetail
from backend.seed import DEFAULT_USER_EMAIL
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


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


def _enrich_article_with_interactions(
    client: Any, article: dict[str, Any], user_id: int
) -> dict[str, Any]:
    """Add is_liked and is_bookmarked flags to a single article.

    Args:
        client: Supabase client instance.
        article: Article dict to enrich.
        user_id: The user whose interactions to query.

    Returns:
        The article dict with is_liked and is_bookmarked set.
    """
    interactions = (
        client.table("interactions")
        .select("type")
        .eq("user_id", user_id)
        .eq("article_id", article["id"])
        .execute()
    )
    interaction_rows = cast(list[dict[str, Any]], interactions.data)

    article["is_liked"] = any(r["type"] == "like" for r in interaction_rows)
    article["is_bookmarked"] = any(r["type"] == "bookmark" for r in interaction_rows)
    return article


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: int) -> dict[str, Any]:
    """Return full details for a single article.

    Args:
        article_id: The ID of the article to retrieve.

    Returns:
        Full article detail including interaction status for the default user.

    Raises:
        HTTPException: 404 if article not found.
    """
    client = get_supabase_client()

    result = client.table("articles").select("*").eq("id", article_id).execute()
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    article = rows[0]

    # Enrich with interaction status
    user_id = _get_default_user_id(client)
    if user_id is not None:
        article = _enrich_article_with_interactions(client, article, user_id)
    else:
        article["is_liked"] = False
        article["is_bookmarked"] = False

    return article
