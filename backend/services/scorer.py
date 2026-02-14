"""Article relevance scoring service using Gemini 2.5 Flash.

Scores articles against user interest profiles in batches,
extracting relevance scores, categories, and keywords.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import types

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds
_MAX_CONTENT_LENGTH = 500


def create_gemini_client(settings: Settings | None = None) -> genai.Client:
    """Create a Gemini client from application settings.

    Args:
        settings: Application settings. Uses defaults if None.

    Returns:
        Initialized Gemini client.
    """
    if settings is None:
        settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _build_scoring_prompt(
    articles: list[dict[str, Any]],
    interests: list[dict[str, Any]],
) -> str:
    """Build a prompt for batch article relevance scoring.

    Args:
        articles: List of article dicts containing title and raw_content.
        interests: List of interest dicts containing keyword and weight.

    Returns:
        Formatted prompt string to send to Gemini.
    """
    if interests:
        interest_lines = [
            f"- {i['keyword']} (weight: {i['weight']:.1f})" for i in interests
        ]
        interest_section = (
            "User Interest Profile (keywords with importance weights):\n"
            + "\n".join(interest_lines)
        )
    else:
        interest_section = (
            "No specific user interests provided. "
            "Score based on general tech significance and novelty."
        )

    article_entries = []
    for idx, article in enumerate(articles):
        title = article.get("title", "")
        content = article.get("raw_content") or ""
        if len(content) > _MAX_CONTENT_LENGTH:
            content = content[:_MAX_CONTENT_LENGTH] + "..."
        article_entries.append(f"[Article {idx}]\nTitle: {title}\nContent: {content}")

    articles_section = "\n\n".join(article_entries)

    return f"""You are a tech article relevance scorer. Evaluate how relevant each article is to the user's interest profile.

{interest_section}

Articles to score:

{articles_section}

For each article, provide:
1. relevance_score: float between 0.0 and 1.0
2. categories: 2-3 broad tech categories (e.g., "AI/ML", "Web Development", "Security")
3. keywords: 3-5 specific technical terms extracted from the article

Scoring guidelines:
- 0.8-1.0: Highly relevant to multiple user interests
- 0.5-0.7: Moderately relevant to at least one interest
- 0.2-0.4: Tangentially related to user interests
- 0.0-0.1: Not relevant to user interests

Respond with JSON in this exact format:
{{
  "results": [
    {{
      "index": 0,
      "relevance_score": 0.85,
      "categories": ["AI/ML", "LLM"],
      "keywords": ["GPT-5", "multimodal", "reasoning"]
    }}
  ]
}}

IMPORTANT:
- Return results for ALL {len(articles)} articles in ascending index order
- Each result must include the article index
- Categories should be broad tech domains
- Keywords should be specific technical terms from the article content"""


def _fallback_result(index: int) -> dict[str, Any]:
    """Return a default scoring result for when parsing fails.

    Args:
        index: Article index within the batch.

    Returns:
        Default result with score 0.0 and empty categories/keywords.
    """
    return {
        "index": index,
        "relevance_score": 0.0,
        "categories": [],
        "keywords": [],
    }


def _parse_scoring_response(
    response_text: str,
    batch_size: int,
) -> list[dict[str, Any]]:
    """Parse the Gemini scoring response JSON.

    Args:
        response_text: JSON text returned from Gemini.
        batch_size: Expected number of results.

    Returns:
        List of scoring results containing score, categories, and keywords.
    """
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError, TypeError:
        logger.warning("Failed to parse scoring response as JSON, using fallback")
        return [_fallback_result(i) for i in range(batch_size)]

    results_raw = data.get("results")
    if not isinstance(results_raw, list):
        logger.warning("Scoring response missing 'results' array, using fallback")
        return [_fallback_result(i) for i in range(batch_size)]

    results: list[dict[str, Any]] = []
    for i in range(batch_size):
        matched = next((r for r in results_raw if r.get("index") == i), None)
        if matched is None:
            results.append(_fallback_result(i))
            continue

        score = matched.get("relevance_score", 0.0)
        if not isinstance(score, (int, float)) or score < 0.0 or score > 1.0:
            score = 0.0

        categories = matched.get("categories", [])
        if not isinstance(categories, list):
            categories = []

        keywords = matched.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []

        results.append(
            {
                "index": i,
                "relevance_score": float(score),
                "categories": [str(c) for c in categories],
                "keywords": [str(k) for k in keywords],
            }
        )

    return results


async def _call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
) -> str:
    """Call the Gemini API with retry and exponential backoff.

    Args:
        client: Google GenAI client.
        model: Gemini model name.
        prompt: Prompt text.

    Returns:
        Gemini response text.

    Raises:
        Exception: When all retries are exhausted.
    """
    last_error: Exception | None = None

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
            last_error = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_DELAY * (2**attempt)
                logger.warning(
                    "Gemini API call failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Gemini API call failed after %d attempts: %s",
                    _MAX_RETRIES,
                    type(exc).__name__,
                )

    raise last_error  # type: ignore[misc]


async def score_articles(
    articles: list[dict[str, Any]],
    interests: list[dict[str, Any]] | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Score article relevance against user interests using Gemini.

    Splits articles into batches, sends each to Gemini for scoring,
    and returns relevance scores, categories, and keywords per article.

    Args:
        articles: List of article dicts containing title and raw_content.
        interests: List of interest dicts with keyword and weight. Defaults to empty.
        settings: Application settings. Uses defaults if None.

    Returns:
        List of scoring result dicts per article, each containing
        relevance_score (0.0-1.0), categories (list[str]), and keywords (list[str]).
    """
    if not articles:
        return []

    if settings is None:
        settings = get_settings()

    if interests is None:
        interests = []

    client = create_gemini_client(settings)
    batch_size = settings.pipeline.scoring_batch_size

    logger.info(
        "Scoring %d article(s) in batches of %d",
        len(articles),
        batch_size,
    )

    all_results: list[dict[str, Any]] = []

    for batch_start in range(0, len(articles), batch_size):
        batch = articles[batch_start : batch_start + batch_size]
        prompt = _build_scoring_prompt(batch, interests)

        try:
            response_text = await _call_gemini_with_retry(
                client,
                settings.gemini.model,
                prompt,
            )
            results = _parse_scoring_response(response_text, len(batch))
        except Exception:
            logger.error(
                "Scoring batch starting at index %d failed, using fallback scores",
                batch_start,
            )
            results = [_fallback_result(i) for i in range(len(batch))]

        all_results.extend(results)

    logger.info("Scoring complete: %d article(s) scored", len(all_results))
    return all_results
