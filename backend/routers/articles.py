"""Article route handlers."""

import json
import logging
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from backend.auth import get_current_user_id
from backend.config import get_settings
from backend.schemas.articles import ArticleDetail, ArticleListItem
from backend.schemas.interactions import InteractionResponse
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])

_ARTICLE_LIST_COLUMNS = (
    "id, source_feed, source_url, title, author, published_at, "
    "summary, detailed_summary, relevance_score, categories, keywords, newsletter_date"
)


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
async def list_bookmarked_articles(
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """Return all bookmarked articles for the authenticated user."""
    client = get_supabase_client()

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


def _assert_article_exists(client: Any, article_id: int) -> dict[str, Any]:
    """Verify an article exists and return its row.

    Args:
        client: Supabase client instance.
        article_id: The article ID to look up.

    Returns:
        The article row dict.

    Raises:
        HTTPException: 404 if the article does not exist.
    """
    result = client.table("articles").select("*").eq("id", article_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    return rows[0]


async def _generate_and_store_detailed_summary(
    article_id: int, title: str, content: str | None
) -> None:
    """Background task to generate a detailed summary and store it.

    Args:
        article_id: Article to update.
        title: Article title for the prompt.
        content: Article body for the prompt.
    """
    from backend.services.summarizer import generate_detailed_summary

    try:
        summary = await generate_detailed_summary(title, content)
        client = get_supabase_client()
        client.table("articles").update(
            {"detailed_summary": json.dumps(summary, ensure_ascii=False)}
        ).eq("id", article_id).execute()
        logger.info("Stored detailed summary for article %d", article_id)
    except Exception:
        logger.exception(
            "Failed to generate detailed summary for article %d", article_id
        )


@router.post("/{article_id}/like", response_model=InteractionResponse)
async def toggle_like(
    article_id: int,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Toggle a like interaction on an article.

    Args:
        article_id: The article to like/unlike.
        user_id: Injected by the JWT auth dependency.

    Raises:
        HTTPException: 404 if article not found.
    """
    from backend.services.interests import (
        remove_interests_on_unlike,
        update_interests_on_like,
    )

    client = get_supabase_client()
    _assert_article_exists(client, article_id)
    settings = get_settings()

    # Check if like already exists
    existing = (
        client.table("interactions")
        .select("id")
        .eq("user_id", user_id)
        .eq("article_id", article_id)
        .eq("type", "like")
        .execute()
    )
    existing_rows = cast(list[dict[str, Any]], existing.data)

    if existing_rows:
        # Unlike: remove interaction and revert interests
        client.table("interactions").delete().eq("id", existing_rows[0]["id"]).execute()
        await remove_interests_on_unlike(client, user_id, article_id, settings)
        return {
            "article_id": article_id,
            "type": "like",
            "active": False,
            "created_at": None,
        }

    # Like: insert interaction and update interests
    insert_result = (
        client.table("interactions")
        .insert({"user_id": user_id, "article_id": article_id, "type": "like"})
        .execute()
    )
    row = cast(dict[str, Any], insert_result.data[0])
    await update_interests_on_like(client, user_id, article_id, settings)
    return {
        "article_id": article_id,
        "type": "like",
        "active": True,
        "created_at": row.get("created_at"),
    }


@router.post("/{article_id}/bookmark", response_model=InteractionResponse)
async def toggle_bookmark(
    article_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Toggle a bookmark interaction on an article.

    On bookmark creation, triggers an async detailed summary generation.

    Args:
        article_id: The article to bookmark/unbookmark.
        background_tasks: FastAPI background task runner.
        user_id: Injected by the JWT auth dependency.

    Raises:
        HTTPException: 404 if article not found.
    """
    client = get_supabase_client()
    article = _assert_article_exists(client, article_id)

    # Check if bookmark already exists
    existing = (
        client.table("interactions")
        .select("id")
        .eq("user_id", user_id)
        .eq("article_id", article_id)
        .eq("type", "bookmark")
        .execute()
    )
    existing_rows = cast(list[dict[str, Any]], existing.data)

    if existing_rows:
        # Unbookmark: remove interaction
        client.table("interactions").delete().eq("id", existing_rows[0]["id"]).execute()
        return {
            "article_id": article_id,
            "type": "bookmark",
            "active": False,
            "created_at": None,
        }

    # Bookmark: insert interaction and trigger detailed summary
    insert_result = (
        client.table("interactions")
        .insert({"user_id": user_id, "article_id": article_id, "type": "bookmark"})
        .execute()
    )
    row = cast(dict[str, Any], insert_result.data[0])

    background_tasks.add_task(
        _generate_and_store_detailed_summary,
        article_id,
        article.get("title", ""),
        article.get("raw_content"),
    )

    return {
        "article_id": article_id,
        "type": "bookmark",
        "active": True,
        "created_at": row.get("created_at"),
    }


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: int,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return full article detail with interaction flags.

    Args:
        article_id: The ID of the article to retrieve.
        user_id: Injected by the JWT auth dependency.

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
