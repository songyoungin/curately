"""Article route handlers."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, status

from backend.schemas.articles import ArticleDetail, ArticleListItem
from backend.seed import DEFAULT_USER_EMAIL
from backend.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/articles", tags=["articles"])

_ARTICLE_LIST_COLUMNS = (
    "id, source_feed, source_url, title, author, published_at, "
    "summary, relevance_score, categories, keywords, newsletter_date"
)


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


@router.get("/bookmarked", response_model=list[ArticleListItem])
async def list_bookmarked_articles() -> list[dict[str, Any]]:
    """Return all bookmarked articles for the default user."""
    client = get_supabase_client()
    user_id = _get_default_user_id()

    # Fetch bookmark interaction article IDs
    bookmark_result = (
        client.table("interactions")
        .select("article_id")
        .eq("user_id", user_id)
        .eq("type", "bookmark")
        .execute()
    )
    bookmark_rows = cast(list[dict[str, Any]], bookmark_result.data)

    if not bookmark_rows:
        return []

    article_ids = [row["article_id"] for row in bookmark_rows]
    articles_result = (
        client.table("articles")
        .select(_ARTICLE_LIST_COLUMNS)
        .in_("id", article_ids)
        .execute()
    )
    articles = cast(list[dict[str, Any]], articles_result.data)

    return _attach_interaction_flags(articles, user_id)


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
