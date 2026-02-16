"""Weekly rewind report generation service using Gemini API.

Collects liked articles from the past week, sends them to Gemini
with the previous report for comparative analysis, and persists
structured results (hot_topics, trend_changes, suggestions).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta
from typing import Any, TypedDict, cast

from google import genai
from google.genai import types
from supabase import Client

from backend.config import Settings, get_settings
from backend.services.scorer import create_gemini_client

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_RETRY_DELAY = 1.0


class RewindReport(TypedDict):
    """Structured weekly rewind report returned by Gemini."""

    hot_topics: list[str]
    trend_changes: dict[str, list[str]]
    suggestions: list[str]


_REWIND_PROMPT = """\
You are an AI tech newsletter analyst. Analyze the user's reading activity \
from the past week and produce a weekly "rewind" report.

## This Week's Liked Articles ({article_count} articles)

{articles_section}

{previous_report_section}

## Instructions

Based on the liked articles above, produce a JSON report with these fields:

1. "hot_topics": A list of 3-5 dominant themes/topics from this week's likes. \
Each should be a concise label (e.g., "LLM Agents", "Kubernetes Security").

2. "trend_changes": An object with two lists:
   - "rising": Topics with increased engagement compared to previous weeks \
(or new topics if no previous report).
   - "declining": Topics that appeared in previous reports but are absent this week. \
If there is no previous report, return an empty list.

3. "suggestions": A list of 2-4 recommended keywords or RSS feed topics \
the user might want to track based on their reading patterns.

Respond ONLY with the JSON object."""

_NO_ACTIVITY_REPORT = RewindReport(
    hot_topics=[],
    trend_changes={"rising": [], "declining": []},
    suggestions=[],
)


async def generate_rewind_report(
    client: Client,
    user_id: int,
    settings: Settings | None = None,
) -> RewindReport:
    """Generate a weekly rewind report for the given user.

    Fetches liked articles from the past 7 days and the most recent
    previous report, then asks Gemini for a comparative analysis.

    Args:
        client: Supabase client instance.
        user_id: ID of the user.
        settings: Application settings. Uses defaults if None.

    Returns:
        Structured rewind report with hot_topics, trend_changes, and suggestions.
    """
    if settings is None:
        settings = get_settings()

    # Fetch liked articles from last 7 days
    articles = _fetch_liked_articles(client, user_id, days=7)
    if not articles:
        logger.info("No liked articles for user %d, returning empty report", user_id)
        return _NO_ACTIVITY_REPORT

    logger.info(
        "Generating rewind report for user %d with %d liked article(s)",
        user_id,
        len(articles),
    )

    # Fetch previous report for comparison
    previous = _fetch_previous_report(client, user_id)

    # Build prompt and call Gemini
    prompt = _build_rewind_prompt(articles, previous)
    gemini_client = create_gemini_client(settings)

    try:
        response_text = await _call_gemini_with_retry(
            gemini_client,
            settings.gemini.model,
            prompt,
        )
        report = _parse_rewind_response(response_text)
    except Exception:
        logger.exception("Gemini rewind analysis failed for user %d", user_id)
        return _NO_ACTIVITY_REPORT

    return report


async def persist_rewind_report(
    client: Client,
    user_id: int,
    report: RewindReport,
    period_start: date,
    period_end: date,
) -> int:
    """Store a rewind report in the database.

    Args:
        client: Supabase client instance.
        user_id: ID of the user.
        report: Generated rewind report.
        period_start: Start date of the reporting period.
        period_end: End date of the reporting period.

    Returns:
        ID of the inserted report row.
    """
    row: dict[str, Any] = {
        "user_id": user_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "report_content": dict(report),
        "hot_topics": report["hot_topics"],
        "trend_changes": report["trend_changes"],
    }
    result = client.table("rewind_reports").insert(row).execute()
    inserted = cast(list[dict[str, Any]], result.data)
    report_id: int = inserted[0]["id"]
    logger.info(
        "Persisted rewind report %d for user %d (period %s to %s)",
        report_id,
        user_id,
        period_start,
        period_end,
    )
    return report_id


def _fetch_liked_articles(
    client: Client,
    user_id: int,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Fetch articles liked by the user within the given number of days.

    Args:
        client: Supabase client instance.
        user_id: ID of the user.
        days: Number of days to look back.

    Returns:
        List of article dicts with title, categories, and keywords.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    # Get liked article IDs
    interaction_resp = (
        client.table("interactions")
        .select("article_id")
        .eq("user_id", user_id)
        .eq("type", "like")
        .gte("created_at", cutoff)
        .execute()
    )
    rows = cast(list[dict[str, Any]], interaction_resp.data)
    article_ids = [row["article_id"] for row in rows]

    if not article_ids:
        return []

    # Fetch article details
    articles_resp = (
        client.table("articles")
        .select("id, title, categories, keywords")
        .in_("id", article_ids)
        .execute()
    )
    return cast(list[dict[str, Any]], articles_resp.data)


def _fetch_previous_report(
    client: Client,
    user_id: int,
) -> dict[str, Any] | None:
    """Fetch the most recent rewind report for comparison.

    Args:
        client: Supabase client instance.
        user_id: ID of the user.

    Returns:
        Previous report dict or None if no prior report exists.
    """
    response = (
        client.table("rewind_reports")
        .select("hot_topics, trend_changes, period_start, period_end")
        .eq("user_id", user_id)
        .order("period_end", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data)
    if not rows:
        return None
    return rows[0]


def _build_rewind_prompt(
    articles: list[dict[str, Any]],
    previous_report: dict[str, Any] | None,
) -> str:
    """Build the Gemini prompt for rewind analysis.

    Args:
        articles: Liked articles with title, categories, and keywords.
        previous_report: Previous report for comparison, or None.

    Returns:
        Formatted prompt string.
    """
    article_lines = []
    for i, article in enumerate(articles):
        title = article.get("title", "Untitled")
        categories = article.get("categories") or []
        keywords = article.get("keywords") or []
        article_lines.append(
            f"[{i + 1}] {title}\n"
            f"    Categories: {', '.join(categories) if categories else 'N/A'}\n"
            f"    Keywords: {', '.join(keywords) if keywords else 'N/A'}"
        )
    articles_section = "\n\n".join(article_lines)

    if previous_report:
        hot_topics = previous_report.get("hot_topics") or []
        trend_changes = previous_report.get("trend_changes") or {}
        period = (
            f"{previous_report.get('period_start', '?')} "
            f"to {previous_report.get('period_end', '?')}"
        )
        previous_report_section = (
            f"## Previous Report ({period})\n\n"
            f"Hot Topics: {', '.join(hot_topics) if hot_topics else 'None'}\n"
            f"Rising: {', '.join(trend_changes.get('rising', []))}\n"
            f"Declining: {', '.join(trend_changes.get('declining', []))}"
        )
    else:
        previous_report_section = (
            "## Previous Report\n\n"
            "No previous report available. This is the first rewind analysis."
        )

    return _REWIND_PROMPT.format(
        article_count=len(articles),
        articles_section=articles_section,
        previous_report_section=previous_report_section,
    )


async def _call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
) -> str:
    """Call the Gemini API with exponential backoff retry.

    Args:
        client: Gemini API client.
        model: Model name to use.
        prompt: Prompt text.

    Returns:
        Gemini response text.

    Raises:
        Exception: Last exception when all retries are exhausted.
    """
    last_exception: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return response.text or ""
        except Exception as exc:
            last_exception = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_RETRY_DELAY * (2**attempt)
                logger.warning(
                    "Gemini rewind call failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Gemini rewind call failed after %d attempts: %s",
                    _MAX_RETRIES,
                    type(exc).__name__,
                )
    raise last_exception  # type: ignore[misc]


def _parse_rewind_response(text: str) -> RewindReport:
    """Parse Gemini response text into a RewindReport.

    Args:
        text: JSON string returned by Gemini.

    Returns:
        Parsed RewindReport. Returns fallback values on parse failure.
    """
    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError, TypeError:
        logger.warning("Failed to parse rewind response JSON, using fallback")
        return _NO_ACTIVITY_REPORT

    hot_topics = data.get("hot_topics")
    if not isinstance(hot_topics, list):
        hot_topics = []

    trend_changes = data.get("trend_changes")
    if not isinstance(trend_changes, dict):
        trend_changes = {"rising": [], "declining": []}
    else:
        if not isinstance(trend_changes.get("rising"), list):
            trend_changes["rising"] = []
        if not isinstance(trend_changes.get("declining"), list):
            trend_changes["declining"] = []

    suggestions = data.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []

    return RewindReport(
        hot_topics=[str(t) for t in hot_topics],
        trend_changes={
            "rising": [str(t) for t in trend_changes["rising"]],
            "declining": [str(t) for t in trend_changes["declining"]],
        },
        suggestions=[str(s) for s in suggestions],
    )
