"""User interest profile management service.

Provides functions to update interest weights on like/unlike events
and apply time-based decay to stale interests.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from supabase import Client

from backend.config import Settings

logger = logging.getLogger(__name__)


async def update_interests_on_like(
    client: Client,
    user_id: int,
    article_id: int,
    settings: Settings,
) -> None:
    """Update user interests when an article is liked.

    Fetches the article's keywords and upserts each into user_interests,
    incrementing weight for existing keywords or inserting new ones.

    Args:
        client: Supabase client instance.
        user_id: ID of the user who liked the article.
        article_id: ID of the liked article.
        settings: Application settings for weight increment.
    """
    article = _fetch_article(client, article_id)
    if article is None:
        return

    keywords: list[str] = article.get("keywords") or []
    if not keywords:
        logger.info("Article %d has no keywords, skipping interest update", article_id)
        return

    source_feed: str | None = article.get("source_feed")
    increment = settings.interests.like_weight_increment
    now = datetime.now(timezone.utc).isoformat()

    # Fetch existing interests for this user to calculate new weights
    existing = _fetch_user_interests_by_keywords(client, user_id, keywords)

    for keyword in keywords:
        current_weight = existing.get(keyword, 0.0)
        new_weight = current_weight + increment
        client.table("user_interests").upsert(
            {
                "user_id": user_id,
                "keyword": keyword,
                "weight": new_weight,
                "source": source_feed,
                "updated_at": now,
            },
            on_conflict="user_id,keyword",
        ).execute()

    logger.info(
        "Updated %d interest(s) for user %d from article %d",
        len(keywords),
        user_id,
        article_id,
    )


async def remove_interests_on_unlike(
    client: Client,
    user_id: int,
    article_id: int,
    settings: Settings,
) -> None:
    """Reverse interest updates when an article is unliked.

    Decrements weight for each keyword in the article.
    Removes entries where weight drops to zero or below.

    Args:
        client: Supabase client instance.
        user_id: ID of the user who unliked the article.
        article_id: ID of the unliked article.
        settings: Application settings for weight decrement.
    """
    article = _fetch_article(client, article_id)
    if article is None:
        return

    keywords: list[str] = article.get("keywords") or []
    if not keywords:
        return

    decrement = settings.interests.like_weight_increment
    existing = _fetch_user_interests_by_keywords(client, user_id, keywords)

    for keyword in keywords:
        current_weight = existing.get(keyword)
        if current_weight is None:
            continue

        new_weight = current_weight - decrement
        if new_weight <= 0:
            client.table("user_interests").delete().eq("user_id", user_id).eq(
                "keyword", keyword
            ).execute()
        else:
            now = datetime.now(timezone.utc).isoformat()
            client.table("user_interests").upsert(
                {
                    "user_id": user_id,
                    "keyword": keyword,
                    "weight": new_weight,
                    "updated_at": now,
                },
                on_conflict="user_id,keyword",
            ).execute()

    logger.info(
        "Removed/decremented %d interest(s) for user %d from article %d",
        len(keywords),
        user_id,
        article_id,
    )


async def apply_time_decay(
    client: Client,
    user_id: int,
    settings: Settings,
) -> int:
    """Apply time-based decay to stale user interests.

    For interests not updated within the decay interval, multiplies weight
    by the decay factor. Removes entries that fall below the minimum threshold.

    Args:
        client: Supabase client instance.
        user_id: ID of the user whose interests to decay.
        settings: Application settings with decay parameters.

    Returns:
        Number of interests that were decayed or removed.
    """
    decay_factor = settings.interests.decay_factor
    interval_days = settings.interests.decay_interval_days
    min_weight = 0.01

    cutoff = datetime.now(timezone.utc) - timedelta(days=interval_days)
    now = datetime.now(timezone.utc).isoformat()

    response = (
        client.table("user_interests")
        .select("id, keyword, weight, updated_at")
        .eq("user_id", user_id)
        .lt("updated_at", cutoff.isoformat())
        .execute()
    )
    stale = cast(list[dict[str, Any]], response.data)

    if not stale:
        logger.info("No stale interests found for user %d", user_id)
        return 0

    decayed_count = 0
    for interest in stale:
        new_weight = interest["weight"] * decay_factor
        interest_id = interest["id"]

        if new_weight < min_weight:
            client.table("user_interests").delete().eq("id", interest_id).execute()
            logger.debug(
                "Removed interest '%s' (weight %.4f below threshold)",
                interest["keyword"],
                new_weight,
            )
        else:
            client.table("user_interests").update(
                {"weight": new_weight, "updated_at": now}
            ).eq("id", interest_id).execute()
        decayed_count += 1

    logger.info(
        "Applied time decay to %d interest(s) for user %d", decayed_count, user_id
    )
    return decayed_count


def _fetch_article(client: Client, article_id: int) -> dict[str, Any] | None:
    """Fetch a single article by ID.

    Args:
        client: Supabase client instance.
        article_id: ID of the article to fetch.

    Returns:
        Article dict or None if not found.
    """
    response = (
        client.table("articles")
        .select("id, keywords, source_feed")
        .eq("id", article_id)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data)
    if not rows:
        logger.warning("Article %d not found", article_id)
        return None
    return rows[0]


def _fetch_user_interests_by_keywords(
    client: Client,
    user_id: int,
    keywords: list[str],
) -> dict[str, float]:
    """Fetch existing interest weights for given keywords.

    Args:
        client: Supabase client instance.
        user_id: ID of the user.
        keywords: List of keywords to look up.

    Returns:
        Mapping of keyword to current weight.
    """
    response = (
        client.table("user_interests")
        .select("keyword, weight")
        .eq("user_id", user_id)
        .in_("keyword", keywords)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data)
    return {row["keyword"]: row["weight"] for row in rows}
