"""Article summarizer service using Gemini API.

Generates basic Korean summaries (2-3 sentences) for newsletter articles
and detailed analyses (background, takeaways, keywords) for bookmarked articles.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TypedDict

from google import genai
from google.genai import types

from backend.config import get_settings

logger = logging.getLogger(__name__)

_MAX_CONTENT_LENGTH = 15_000
_MAX_RETRIES = 3
_BASE_RETRY_DELAY = 1.0


class DetailedSummary(TypedDict):
    """Structured detailed summary returned by Gemini."""

    background: str
    takeaways: list[str]
    keywords: list[str]


_BASIC_SUMMARY_PROMPT = """\
You are a tech newsletter editor writing for Korean tech professionals.
Given the article title and content below, write a concise summary in Korean (2-3 sentences).
Focus on the key takeaways and why this matters to tech professionals.

Title: {title}

Content:
{content}

Write the summary in Korean. Output ONLY the summary text, nothing else."""

_DETAILED_SUMMARY_PROMPT = """\
You are a tech newsletter editor writing for Korean tech professionals.
Given the article title and content below, produce a detailed analysis in Korean.

Title: {title}

Content:
{content}

Respond with a JSON object containing exactly these fields:
- "background": 2-3 sentences explaining the context/background of this article in Korean.
- "takeaways": a list of 3-5 key points in Korean.
- "keywords": a list of 3-5 related technical keywords (can be English or Korean).

Output ONLY the JSON object, nothing else."""


def _get_client() -> genai.Client:
    """Create a Gemini API client."""
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _truncate_content(content: str | None) -> str:
    """Truncate content to the maximum allowed length.

    Args:
        content: Original text. Returns empty string if None.

    Returns:
        Text truncated to within the maximum length.
    """
    if not content:
        return ""
    if len(content) <= _MAX_CONTENT_LENGTH:
        return content
    return content[:_MAX_CONTENT_LENGTH] + "..."


async def _call_gemini_with_retry(
    client: genai.Client,
    model: str,
    contents: str,
    config: types.GenerateContentConfig | None = None,
) -> str:
    """Call the Gemini API with exponential backoff retry.

    Args:
        client: Gemini API client.
        model: Model name to use.
        contents: Prompt text.
        config: Generation config (e.g., JSON response mode).

    Returns:
        Gemini response text.

    Raises:
        Exception: Last exception when all retries are exhausted.
    """
    last_exception: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            last_exception = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_RETRY_DELAY * (2**attempt)
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
    raise last_exception  # type: ignore[misc]


async def generate_basic_summary(title: str, content: str | None) -> str:
    """Generate a basic Korean summary (2-3 sentences) for an article.

    Args:
        title: Article title.
        content: Article body or description.

    Returns:
        Korean summary text.
    """
    settings = get_settings()
    client = _get_client()
    truncated = _truncate_content(content)

    prompt = _BASIC_SUMMARY_PROMPT.format(
        title=title, content=truncated or "(no content)"
    )

    text = await _call_gemini_with_retry(
        client=client,
        model=settings.gemini.model,
        contents=prompt,
    )
    return text.strip()


async def generate_detailed_summary(title: str, content: str | None) -> DetailedSummary:
    """Generate a detailed analysis (background, key takeaways, keywords) for an article.

    Args:
        title: Article title.
        content: Article body or description.

    Returns:
        Dict containing background, takeaways, and keywords.
    """
    settings = get_settings()
    client = _get_client()
    truncated = _truncate_content(content)

    prompt = _DETAILED_SUMMARY_PROMPT.format(
        title=title, content=truncated or "(no content)"
    )

    text = await _call_gemini_with_retry(
        client=client,
        model=settings.gemini.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    return _parse_detailed_summary(text)


def _parse_detailed_summary(text: str) -> DetailedSummary:
    """Parse Gemini response text into a DetailedSummary.

    Args:
        text: JSON string returned by Gemini.

    Returns:
        Parsed DetailedSummary. Returns fallback values on parse failure.
    """
    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError, TypeError:
        logger.warning("Failed to parse detailed summary JSON, using fallback")
        return _fallback_detailed_summary(text)

    background = data.get("background")
    takeaways = data.get("takeaways")
    keywords = data.get("keywords")

    if not isinstance(background, str):
        background = str(background) if background else ""
    if not isinstance(takeaways, list):
        takeaways = []
    if not isinstance(keywords, list):
        keywords = []

    return DetailedSummary(
        background=background,
        takeaways=[str(t) for t in takeaways],
        keywords=[str(k) for k in keywords],
    )


def _fallback_detailed_summary(text: str) -> DetailedSummary:
    """Return a fallback summary with the raw text as background."""
    return DetailedSummary(
        background=text.strip() if text else "",
        takeaways=[],
        keywords=[],
    )
