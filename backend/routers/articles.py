"""Article route handlers."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, status

from backend.schemas.articles import ArticleDetail
from backend.seed import DEFAULT_USER_EMAIL
from backend.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/articles", tags=["articles"])


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


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: int) -> dict[str, Any]:
    """Return full article detail with interaction flags.

    Args:
        article_id: The ID of the article to retrieve.

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
    user_id = _get_default_user_id()

    interactions_result = (
        client.table("interactions")
        .select("type")
        .eq("user_id", user_id)
        .eq("article_id", article_id)
        .execute()
    )
    interactions = cast(list[dict[str, Any]], interactions_result.data)

    article["is_liked"] = any(i["type"] == "like" for i in interactions)
    article["is_bookmarked"] = any(i["type"] == "bookmark" for i in interactions)

    return article
