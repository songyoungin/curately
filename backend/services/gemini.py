"""Shared Gemini API utilities.

Provides a common async retry wrapper and client factory used
by digest, rewind, and other services that call Gemini.
"""

from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_RETRY_DELAY = 1.0


def create_gemini_client(settings: Settings | None = None) -> genai.Client:
    """Create a Gemini client from application settings."""
    if settings is None:
        settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


async def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
    config: types.GenerateContentConfig | None = None,
) -> str:
    """Call the Gemini API (async) with exponential backoff retry.

    Uses client.aio.models.generate_content for non-blocking calls.
    Retries up to 3 times with exponential backoff (1s, 2s, 4s).

    Args:
        client: Gemini API client.
        model: Model name (e.g., "gemini-2.5-flash").
        prompt: Prompt text.
        config: Generation config (e.g., JSON response mode).

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
