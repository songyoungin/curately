"""Daily pipeline orchestrator service.

Orchestrates the full daily pipeline: collect articles from RSS feeds,
score them against user interests, filter by relevance, generate summaries,
and persist results to the database.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, TypedDict, cast

from supabase import Client

from backend.config import Settings, get_settings
from backend.services.collector import collect_articles
from backend.services.scorer import score_articles
from backend.services.interests import apply_time_decay
from backend.services.summarizer import generate_basic_summary

logger = logging.getLogger(__name__)


class PipelineResult(TypedDict):
    """Result stats returned by the daily pipeline."""

    articles_collected: int
    articles_scored: int
    articles_filtered: int
    articles_summarized: int
    newsletter_date: str


async def run_daily_pipeline(
    client: Client,
    settings: Settings | None = None,
) -> PipelineResult:
    """Run the full daily pipeline.

    Stages:
        1. Collect new articles from RSS feeds
        2. Load user interest keywords and apply time decay
        3. Score articles against interests
        4. Filter by relevance threshold and select top N
        5. Generate Korean summaries for filtered articles
        6. Persist articles with scores, summaries, and newsletter date

    Args:
        client: Supabase client instance.
        settings: Application settings. Uses defaults if None.

    Returns:
        Pipeline result stats including counts and newsletter date.
    """
    if settings is None:
        settings = get_settings()

    today = date.today().isoformat()
    logger.info("Starting daily pipeline for %s", today)

    # Stage 1: Collect articles
    logger.info("Stage 1/7: Collecting articles from RSS feeds")
    articles = await collect_articles(client)
    if not articles:
        logger.info("No new articles collected, pipeline complete")
        return PipelineResult(
            articles_collected=0,
            articles_scored=0,
            articles_filtered=0,
            articles_summarized=0,
            newsletter_date=today,
        )
    logger.info("Collected %d new article(s)", len(articles))

    # Stage 2: Load user interests
    logger.info("Stage 2/7: Loading user interests")
    user_id, interests = _load_user_interests(client)
    logger.info("Loaded %d interest keyword(s)", len(interests))

    # Stage 2.5: Apply time decay to stale interests
    if user_id is not None:
        logger.info("Applying time decay to stale interests")
        decayed = await apply_time_decay(client, user_id, settings)
        if decayed > 0:
            logger.info("Decayed %d interest(s), reloading interests", decayed)
            _, interests = _load_user_interests(client)

    # Stage 3: Score articles
    logger.info("Stage 3/7: Scoring articles against user interests")
    try:
        score_results = await score_articles(articles, interests, settings)
    except Exception:
        logger.error("Scoring stage failed, aborting pipeline")
        return PipelineResult(
            articles_collected=len(articles),
            articles_scored=0,
            articles_filtered=0,
            articles_summarized=0,
            newsletter_date=today,
        )

    # Merge scores into articles
    for i, article in enumerate(articles):
        if i < len(score_results):
            article["relevance_score"] = score_results[i]["relevance_score"]
            article["categories"] = score_results[i]["categories"]
            article["keywords"] = score_results[i]["keywords"]
        else:
            article["relevance_score"] = 0.0
            article["categories"] = []
            article["keywords"] = []

    articles_scored = len(articles)
    logger.info("Scored %d article(s)", articles_scored)

    # Stage 4: Filter articles
    max_total = settings.pipeline.max_articles_per_newsletter
    existing_result = (
        client.table("articles")
        .select("id", count="exact")
        .eq("newsletter_date", today)
        .execute()
    )
    existing_count = existing_result.count or 0
    remaining_slots = max(0, max_total - existing_count)
    logger.info(
        "Stage 4/7: Filtering articles (threshold=%.2f, max=%d, existing=%d, slots=%d)",
        settings.pipeline.relevance_threshold,
        max_total,
        existing_count,
        remaining_slots,
    )
    filtered = _filter_articles(
        articles,
        threshold=settings.pipeline.relevance_threshold,
        max_count=remaining_slots,
    )
    logger.info("Filtered to %d article(s)", len(filtered))

    # Stage 5: Summarize articles
    logger.info("Stage 5/7: Generating summaries")
    summarized_count = 0
    for article in filtered:
        try:
            summary = await generate_basic_summary(
                article["title"],
                article.get("raw_content"),
            )
            article["summary"] = summary
            summarized_count += 1
        except Exception:
            logger.warning(
                "Failed to summarize article '%s', storing without summary",
                article["title"],
            )
            article["summary"] = None
    logger.info("Summarized %d article(s)", summarized_count)

    # Stage 6: Persist articles
    logger.info("Stage 6/7: Persisting articles to database")
    _persist_articles(client, filtered, today)
    logger.info("Persisted %d article(s) for newsletter date %s", len(filtered), today)

    result = PipelineResult(
        articles_collected=len(articles),
        articles_scored=articles_scored,
        articles_filtered=len(filtered),
        articles_summarized=summarized_count,
        newsletter_date=today,
    )
    logger.info("Daily pipeline complete: %s", result)
    return result


def _load_user_interests(
    client: Client,
) -> tuple[int | None, list[dict[str, Any]]]:
    """Load top 20 interest keywords by weight for the default user.

    Args:
        client: Supabase client instance.

    Returns:
        Tuple of (user_id, interests). user_id is None if the default user
        is not found.
    """
    response = (
        client.table("users")
        .select("id")
        .eq("email", "default@curately.local")
        .execute()
    )
    users = cast(list[dict[str, Any]], response.data)
    if not users:
        logger.warning("Default user not found, returning empty interests")
        return None, []

    user_id: int = users[0]["id"]
    response = (
        client.table("user_interests")
        .select("keyword, weight")
        .eq("user_id", user_id)
        .order("weight", desc=True)
        .limit(20)
        .execute()
    )
    return user_id, cast(list[dict[str, Any]], response.data)


def _filter_articles(
    articles: list[dict[str, Any]],
    threshold: float,
    max_count: int,
) -> list[dict[str, Any]]:
    """Filter articles by relevance threshold and select top N.

    Args:
        articles: Scored articles with relevance_score field.
        threshold: Minimum relevance score to include.
        max_count: Maximum number of articles to return.

    Returns:
        Top articles sorted by relevance score descending.
    """
    above_threshold = [
        a for a in articles if a.get("relevance_score", 0.0) >= threshold
    ]
    above_threshold.sort(key=lambda a: a.get("relevance_score", 0.0), reverse=True)
    return above_threshold[:max_count]


def _persist_articles(
    client: Client,
    articles: list[dict[str, Any]],
    newsletter_date: str,
) -> None:
    """Upsert filtered articles into the database.

    Inserts new articles or updates existing ones based on source_url.
    Sets newsletter_date, summary, relevance_score, categories, and keywords.

    Args:
        client: Supabase client instance.
        articles: Filtered and summarized articles.
        newsletter_date: ISO date string for the newsletter edition.
    """
    for article in articles:
        row = {
            "source_feed": article["source_feed"],
            "source_url": article["source_url"],
            "title": article["title"],
            "author": article.get("author"),
            "published_at": (
                article["published_at"].isoformat()
                if article.get("published_at")
                else None
            ),
            "raw_content": article.get("raw_content"),
            "summary": article.get("summary"),
            "relevance_score": article.get("relevance_score"),
            "categories": article.get("categories", []),
            "keywords": article.get("keywords", []),
            "newsletter_date": newsletter_date,
        }
        client.table("articles").upsert(row, on_conflict="source_url").execute()
