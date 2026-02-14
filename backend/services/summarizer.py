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
    """Gemini API 클라이언트를 생성한다."""
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _truncate_content(content: str | None) -> str:
    """콘텐츠를 최대 길이로 자른다.

    Args:
        content: 원본 텍스트. None이면 빈 문자열 반환.

    Returns:
        최대 길이 이내로 잘린 텍스트.
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
    """Gemini API를 지수 백오프 재시도로 호출한다.

    Args:
        client: Gemini API 클라이언트.
        model: 사용할 모델 이름.
        contents: 프롬프트 텍스트.
        config: 생성 설정 (JSON 응답 등).

    Returns:
        Gemini 응답 텍스트.

    Raises:
        Exception: 모든 재시도 실패 시 마지막 예외.
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
    """기사의 기본 요약(한국어 2~3문장)을 생성한다.

    Args:
        title: 기사 제목.
        content: 기사 본문 또는 설명.

    Returns:
        한국어 요약 텍스트.
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
    """기사의 상세 분석(배경, 핵심 포인트, 키워드)을 생성한다.

    Args:
        title: 기사 제목.
        content: 기사 본문 또는 설명.

    Returns:
        background, takeaways, keywords를 포함한 딕셔너리.
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
    """Gemini 응답 텍스트를 DetailedSummary로 파싱한다.

    Args:
        text: Gemini가 반환한 JSON 문자열.

    Returns:
        파싱된 DetailedSummary. 파싱 실패 시 기본값 반환.
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
    """JSON 파싱 실패 시 원본 텍스트를 background에 넣어 반환한다."""
    return DetailedSummary(
        background=text.strip() if text else "",
        takeaways=[],
        keywords=[],
    )
