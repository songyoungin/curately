"""Daily pipeline orchestrator service.

Runs the full article collection, scoring, filtering, summarization,
and persistence pipeline. Designed to be invoked by the scheduler
or triggered manually via the API.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any, TypedDict, cast

from supabase import Client

from backend.config import Settings, get_settings
from backend.seed import DEFAULT_USER_EMAIL
from backend.services.collector import collect_articles
from backend.services.scorer import score_articles
from backend.services.summarizer import generate_basic_summary
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class PipelineResult(TypedDict):
    """Statistics returned after a pipeline run."""

    articles_collected: int
    articles_scored: int
    articles_filtered: int
    articles_saved: int
    newsletter_date: str


async def run_daily_pipeline() -> PipelineResult:
    """Execute the full daily newsletter pipeline.

    Stages:
        1. Collect — fetch new articles from active RSS feeds
        2. Load Interests — retrieve default user interest profile
        3. Score — evaluate article relevance via Gemini
        4. Filter — remove low-scoring articles, keep top N
        5. Summarize — generate Korean summaries for each article
        6. Persist — save articles to the database with today's date

    Returns:
        PipelineResult with counts for each stage and the newsletter date.
    """
    settings = get_settings()
    client = get_supabase_client()
    newsletter_date = datetime.now(tz=UTC).date().isoformat()

    logger.info("Starting daily pipeline for %s", newsletter_date)

    # Stage 1: Collect articles from RSS feeds
    collected = await _stage_collect(client)
    if not collected:
        logger.info("No articles collected, pipeline finished early")
        return PipelineResult(
            articles_collected=0,
            articles_scored=0,
            articles_filtered=0,
            articles_saved=0,
            newsletter_date=newsletter_date,
        )

    # Stage 2: Load user interests
    interests = _stage_load_interests(client)

    # Stage 3: Score articles against interests
    scored = await _stage_score(collected, interests, settings)

    # Stage 4: Filter by threshold and limit
    filtered = _stage_filter(scored, settings)

    # Stage 5: Summarize each article
    summarized = await _stage_summarize(filtered)

    # Stage 6: Persist to database
    saved_count = _stage_persist(client, summarized, newsletter_date)

    result = PipelineResult(
        articles_collected=len(collected),
        articles_scored=len(scored),
        articles_filtered=len(filtered),
        articles_saved=saved_count,
        newsletter_date=newsletter_date,
    )
    logger.info(
        "Pipeline complete: collected=%d, scored=%d, filtered=%d, saved=%d",
        result["articles_collected"],
        result["articles_scored"],
        result["articles_filtered"],
        result["articles_saved"],
    )
    return result


async def _stage_collect(client: Client) -> list[dict[str, Any]]:
    """Stage 1: Collect new articles from active feeds."""
    logger.info("Stage 1: Collecting articles from RSS feeds")
    try:
        articles = await collect_articles(client)
        logger.info("Collected %d article(s)", len(articles))
        return articles
    except Exception:
        logger.exception("Article collection failed")
        return []


def _stage_load_interests(client: Client) -> list[dict[str, Any]]:
    """Stage 2: Load the default user's interest keywords.

    Retrieves the top 20 interests by weight (descending) for the
    default MVP user.
    """
    logger.info("Stage 2: Loading user interests")
    try:
        user_result = (
            client.table("users")
            .select("id")
            .eq("email", DEFAULT_USER_EMAIL)
            .execute()
        )
        users = cast(list[dict[str, Any]], user_result.data)
        if not users:
            logger.warning("Default user not found, proceeding without interests")
            return []

        user_id = users[0]["id"]
        interests_result = (
            client.table("user_interests")
            .select("keyword, weight")
            .eq("user_id", user_id)
            .order("weight", desc=True)
            .limit(20)
            .execute()
        )
        interests = cast(list[dict[str, Any]], interests_result.data)
        logger.info("Loaded %d interest(s)", len(interests))
        return interests
    except Exception:
        logger.exception("Failed to load interests")
        return []


async def _stage_score(
    articles: list[dict[str, Any]],
    interests: list[dict[str, Any]],
    settings: Settings,
) -> list[dict[str, Any]]:
    """Stage 3: Score articles against user interests.

    Merges scoring results (relevance_score, categories, keywords)
    back into article dicts.
    """
    logger.info("Stage 3: Scoring %d article(s)", len(articles))
    try:
        score_results = await score_articles(articles, interests, settings)
    except Exception:
        logger.exception("Scoring failed, assigning zero scores")
        score_results = [
            {"index": i, "relevance_score": 0.0, "categories": [], "keywords": []}
            for i in range(len(articles))
        ]

    # Merge scores back into article dicts
    scored_articles: list[dict[str, Any]] = []
    for idx, article in enumerate(articles):
        merged = dict(article)
        if idx < len(score_results):
            result = score_results[idx]
            merged["relevance_score"] = result.get("relevance_score", 0.0)
            merged["categories"] = result.get("categories", [])
            merged["keywords"] = result.get("keywords", [])
        else:
            merged["relevance_score"] = 0.0
            merged["categories"] = []
            merged["keywords"] = []
        scored_articles.append(merged)

    logger.info("Scored %d article(s)", len(scored_articles))
    return scored_articles


def _stage_filter(
    articles: list[dict[str, Any]],
    settings: Settings,
) -> list[dict[str, Any]]:
    """Stage 4: Filter articles by relevance threshold and cap count.

    Removes articles below the configured threshold, sorts by score
    descending, and limits to max_articles_per_newsletter.
    """
    threshold = settings.pipeline.relevance_threshold
    max_articles = settings.pipeline.max_articles_per_newsletter

    logger.info(
        "Stage 4: Filtering (threshold=%.2f, max=%d)", threshold, max_articles
    )

    above_threshold = [
        a for a in articles if a.get("relevance_score", 0.0) >= threshold
    ]
    above_threshold.sort(key=lambda a: a.get("relevance_score", 0.0), reverse=True)
    filtered = above_threshold[:max_articles]

    logger.info(
        "Filtered to %d article(s) (from %d above threshold out of %d total)",
        len(filtered),
        len(above_threshold),
        len(articles),
    )
    return filtered


async def _stage_summarize(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stage 5: Generate Korean summaries for each article."""
    logger.info("Stage 5: Summarizing %d article(s)", len(articles))
    summarized: list[dict[str, Any]] = []

    for article in articles:
        title = article.get("title", "")
        content = article.get("raw_content")
        try:
            summary = await generate_basic_summary(title, content)
            article_with_summary = dict(article)
            article_with_summary["summary"] = summary
            summarized.append(article_with_summary)
        except Exception:
            logger.exception("Failed to summarize article: %s", title)
            article_with_summary = dict(article)
            article_with_summary["summary"] = ""
            summarized.append(article_with_summary)

    logger.info("Summarized %d article(s)", len(summarized))
    return summarized


def _stage_persist(
    client: Client,
    articles: list[dict[str, Any]],
    newsletter_date: str,
) -> int:
    """Stage 6: Insert articles into the database.

    Sets newsletter_date on each article and inserts into the
    articles table. Uses upsert-style individual inserts to handle
    potential duplicates gracefully.

    Returns:
        Number of articles successfully saved.
    """
    logger.info("Stage 6: Persisting %d article(s)", len(articles))
    saved = 0

    for article in articles:
        row = {
            "source_feed": article.get("source_feed", ""),
            "source_url": article.get("source_url", ""),
            "title": article.get("title", ""),
            "author": article.get("author"),
            "published_at": (
                article["published_at"].isoformat()
                if article.get("published_at")
                else None
            ),
            "raw_content": article.get("raw_content"),
            "summary": article.get("summary"),
            "relevance_score": article.get("relevance_score"),
            "categories": json.dumps(article.get("categories", [])),
            "keywords": json.dumps(article.get("keywords", [])),
            "newsletter_date": newsletter_date,
        }
        try:
            client.table("articles").insert(row).execute()
            saved += 1
        except Exception:
            logger.exception(
                "Failed to persist article: %s", article.get("source_url", "unknown")
            )

    logger.info("Saved %d article(s) to database", saved)
    return saved
