"""Daily digest generation service using Gemini API."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict, cast

from google.genai import types
from supabase import Client

from backend.config import Settings, get_settings
from backend.services.gemini import call_gemini_with_retry, create_gemini_client

logger = logging.getLogger(__name__)


class DigestSection(TypedDict):
    """Single thematic section within a digest."""

    theme: str
    title: str
    body: str
    article_ids: list[int]


class DigestContent(TypedDict):
    """Full structured digest content returned by Gemini."""

    headline: str
    sections: list[DigestSection]
    key_takeaways: list[str]
    connections: str


_NO_ARTICLES_DIGEST = DigestContent(
    headline="",
    sections=[],
    key_takeaways=[],
    connections="",
)


_DIGEST_PROMPT = """\
You are a senior tech editor writing a daily briefing for a Korean tech professional.
You are given today's {article_count} curated articles, ranked by personal relevance score.

## Today's Articles

{articles_section}

## Instructions

Write a daily digest that SYNTHESIZES these articles into a cohesive briefing.
DO NOT simply restate each article's summary. Instead:
- Identify 2-5 common themes across articles
- Group related articles into thematic sections
- Draw connections between articles within each theme
- Tell a story about what matters today

Output a JSON object with these fields:

1. "headline": A single compelling sentence capturing today's dominant narrative.
   - Max 100 characters. Write in Korean.

2. "sections": An array of 2-5 thematic sections. Each section:
   - "theme": Category label (e.g., "AI/ML", "DevOps", "Backend")
   - "title": One-line section heading in Korean
   - "body": 3-5 sentence narrative synthesis in Korean (NOT a list of per-article summaries)
   - "article_ids": List of article index numbers (1-based) covered in this section

3. "key_takeaways": An array of 3-5 bullet points in Korean. These are the
   "if you read nothing else" items. Each should be a complete, standalone sentence.

4. "connections": 2-3 sentences in Korean identifying cross-theme patterns
   and relationships between the sections.

IMPORTANT:
- article_ids must use the index numbers [1], [2], etc. from the article list above.
- Every article should appear in at least one section.
- Write entirely in Korean except for technical terms.
- Be insightful, not repetitive.

Respond ONLY with the JSON object."""


def _build_digest_prompt(articles: list[dict[str, Any]]) -> str:
    """Build the Gemini prompt for digest generation."""
    article_lines = []
    for i, article in enumerate(articles):
        title = article.get("title", "Untitled")
        summary = article.get("summary") or "(no summary)"
        score = article.get("relevance_score", 0.0)
        categories = article.get("categories") or []
        keywords = article.get("keywords") or []
        article_lines.append(
            f'[{i + 1}] (relevance: {score:.2f}) "{title}"\n'
            f"    Summary: {summary}\n"
            f"    Categories: {', '.join(categories) if categories else 'N/A'}\n"
            f"    Keywords: {', '.join(keywords) if keywords else 'N/A'}"
        )
    articles_section = "\n\n".join(article_lines)

    return _DIGEST_PROMPT.format(
        article_count=len(articles),
        articles_section=articles_section,
    )


def _parse_digest_response(text: str) -> DigestContent:
    """Parse Gemini response text into DigestContent."""
    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError, TypeError:
        logger.warning("Failed to parse digest response JSON, using fallback")
        return _NO_ARTICLES_DIGEST

    headline = data.get("headline")
    if not isinstance(headline, str):
        headline = ""

    raw_sections = data.get("sections")
    sections: list[DigestSection] = []
    if isinstance(raw_sections, list):
        for section in raw_sections:
            if not isinstance(section, dict):
                continue
            raw_article_ids = section.get("article_ids") or []
            sections.append(
                DigestSection(
                    theme=str(section.get("theme", "")),
                    title=str(section.get("title", "")),
                    body=str(section.get("body", "")),
                    article_ids=[
                        int(article_id)
                        for article_id in raw_article_ids
                        if isinstance(article_id, int | float)
                    ],
                )
            )

    raw_takeaways = data.get("key_takeaways")
    key_takeaways: list[str] = []
    if isinstance(raw_takeaways, list):
        key_takeaways = [str(item) for item in raw_takeaways]

    connections = data.get("connections")
    if not isinstance(connections, str):
        connections = ""

    return DigestContent(
        headline=headline,
        sections=sections,
        key_takeaways=key_takeaways,
        connections=connections,
    )


async def generate_daily_digest(
    client: Client,
    digest_date: str,
    settings: Settings | None = None,
) -> tuple[DigestContent, list[int]]:
    """Generate a synthesized daily digest from the day's newsletter articles."""
    if settings is None:
        settings = get_settings()

    result = (
        client.table("articles")
        .select("id, title, summary, categories, keywords, relevance_score, source_url")
        .eq("newsletter_date", digest_date)
        .order("relevance_score", desc=True)
        .execute()
    )
    articles = cast(list[dict[str, Any]], result.data)

    if not articles:
        logger.info("No articles found for %s, returning empty digest", digest_date)
        return _NO_ARTICLES_DIGEST, []

    logger.info(
        "Generating digest for %s with %d article(s)", digest_date, len(articles)
    )

    index_to_id: dict[int, int] = {}
    for i, article in enumerate(articles):
        index_to_id[i + 1] = article["id"]
    all_article_ids = [article["id"] for article in articles]

    prompt = _build_digest_prompt(articles)
    gemini_client = create_gemini_client(settings)

    try:
        response_text = await call_gemini_with_retry(
            gemini_client,
            settings.gemini.model,
            prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        digest = _parse_digest_response(response_text)
    except Exception:
        logger.exception("Gemini digest generation failed for %s", digest_date)
        return _NO_ARTICLES_DIGEST, all_article_ids

    for section in digest["sections"]:
        section["article_ids"] = [
            index_to_id[idx] for idx in section["article_ids"] if idx in index_to_id
        ]

    return digest, all_article_ids


async def persist_digest(
    client: Client,
    digest_date: str,
    content: DigestContent,
    article_ids: list[int],
) -> int:
    """Upsert a digest row by digest_date and return the persisted row ID."""
    row: dict[str, Any] = {
        "digest_date": digest_date,
        "content": dict(content),
        "article_ids": article_ids,
        "article_count": len(article_ids),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = client.table("digests").upsert(row, on_conflict="digest_date").execute()
    inserted = cast(list[dict[str, Any]], result.data)
    digest_id: int = inserted[0]["id"]
    logger.info(
        "Persisted digest %d for date %s (%d articles)",
        digest_id,
        digest_date,
        len(article_ids),
    )
    return digest_id
