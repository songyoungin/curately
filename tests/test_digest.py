"""Digest service tests."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.digest import (
    _NO_ARTICLES_DIGEST,
    _parse_digest_response,
    generate_daily_digest,
    persist_digest,
)

SAMPLE_ARTICLES = [
    {
        "id": 101,
        "title": "AI Agents in Production",
        "summary": "Teams are shipping agentic workflows.",
        "categories": ["AI/ML"],
        "keywords": ["agents", "llm"],
        "relevance_score": 0.92,
        "source_url": "https://example.com/a",
    },
    {
        "id": 102,
        "title": "Kubernetes Runtime Updates",
        "summary": "Runtime improvements reduce startup latency.",
        "categories": ["DevOps"],
        "keywords": ["kubernetes"],
        "relevance_score": 0.76,
        "source_url": "https://example.com/b",
    },
    {
        "id": 103,
        "title": "Postgres 17 Performance",
        "summary": "Parallel query planner saw meaningful gains.",
        "categories": ["Backend"],
        "keywords": ["postgres"],
        "relevance_score": 0.67,
        "source_url": "https://example.com/c",
    },
]


def _make_service_supabase_mock(
    *,
    articles: list[dict] | None = None,
    upsert_result: list[dict] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for digest service tests."""
    mock_articles = MagicMock()
    mock_digests = MagicMock()

    article_data = articles if articles is not None else []
    mock_articles.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=article_data
    )

    ups_data = upsert_result if upsert_result is not None else [{"id": 1}]
    mock_digests.upsert.return_value.execute.return_value = MagicMock(data=ups_data)

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "articles":
            return mock_articles
        if name == "digests":
            return mock_digests
        return MagicMock()

    mock_client.table.side_effect = route_table
    return mock_client


def _make_settings() -> MagicMock:
    """Create a mock Settings object for digest tests."""
    settings = MagicMock()
    settings.gemini_api_key = "test-api-key"
    settings.gemini.model = "gemini-2.5-flash"
    return settings


@pytest.mark.asyncio
@patch("backend.services.gemini.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.digest.create_gemini_client")
@patch("backend.services.digest.get_settings")
async def test_generate_digest_happy_path(
    mock_get_settings: MagicMock,
    mock_create_gemini: MagicMock,
    _mock_sleep: AsyncMock,
) -> None:
    """Generate digest with valid Gemini JSON and mapped article IDs."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    gemini_response = {
        "headline": "AI and infrastructure are converging today.",
        "sections": [
            {
                "theme": "AI/ML",
                "title": "Agent transition",
                "body": "Teams are moving agent workflows into production.",
                "article_ids": [1, 3],
            }
        ],
        "key_takeaways": ["AI adoption is accelerating."],
        "connections": "AI demand is directly connected to infrastructure spend.",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(gemini_response)
    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_service_supabase_mock(articles=SAMPLE_ARTICLES)

    digest, article_ids = await generate_daily_digest(
        supabase,
        digest_date="2026-02-18",
        settings=settings,
    )

    assert digest["headline"] == gemini_response["headline"]
    assert digest["sections"][0]["article_ids"] == [101, 103]
    assert digest["key_takeaways"] == ["AI adoption is accelerating."]
    assert article_ids == [101, 102, 103]
    mock_gemini.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
@patch("backend.services.digest.create_gemini_client")
async def test_generate_digest_no_articles(mock_create_gemini: MagicMock) -> None:
    """Return empty digest and skip Gemini call when no articles exist."""
    supabase = _make_service_supabase_mock(articles=[])

    digest, article_ids = await generate_daily_digest(
        supabase,
        digest_date="2026-02-18",
        settings=_make_settings(),
    )

    assert digest == _NO_ARTICLES_DIGEST
    assert article_ids == []
    mock_create_gemini.assert_not_called()


@pytest.mark.asyncio
@patch("backend.services.gemini.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.digest.create_gemini_client")
@patch("backend.services.digest.get_settings")
async def test_generate_digest_gemini_failure(
    mock_get_settings: MagicMock,
    mock_create_gemini: MagicMock,
    _mock_sleep: AsyncMock,
) -> None:
    """Return fallback digest when Gemini fails after retries."""
    settings = _make_settings()
    mock_get_settings.return_value = settings

    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("Gemini unavailable")
    )
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_service_supabase_mock(articles=SAMPLE_ARTICLES)

    digest, article_ids = await generate_daily_digest(
        supabase,
        digest_date="2026-02-18",
        settings=settings,
    )

    assert digest == _NO_ARTICLES_DIGEST
    assert article_ids == [101, 102, 103]


@pytest.mark.asyncio
@patch("backend.services.digest.create_gemini_client")
async def test_generate_digest_malformed_json(mock_create_gemini: MagicMock) -> None:
    """Return fallback digest when Gemini returns malformed JSON."""
    mock_response = MagicMock()
    mock_response.text = "not json"
    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_service_supabase_mock(articles=SAMPLE_ARTICLES)

    digest, article_ids = await generate_daily_digest(
        supabase,
        digest_date="2026-02-18",
        settings=_make_settings(),
    )

    assert digest == _NO_ARTICLES_DIGEST
    assert article_ids == [101, 102, 103]


def test_parse_digest_response_partial() -> None:
    """Fill defaults for missing or malformed digest response fields."""
    partial = json.dumps(
        {
            "sections": [{"title": "Section title"}],
            "key_takeaways": ["Takeaway 1", 2],
        }
    )

    digest = _parse_digest_response(partial)

    assert digest["headline"] == ""
    assert digest["connections"] == ""
    assert len(digest["sections"]) == 1
    assert digest["sections"][0]["theme"] == ""
    assert digest["sections"][0]["title"] == "Section title"
    assert digest["sections"][0]["body"] == ""
    assert digest["sections"][0]["article_ids"] == []
    assert digest["key_takeaways"] == ["Takeaway 1", "2"]


@pytest.mark.asyncio
@patch("backend.services.digest.create_gemini_client")
async def test_article_index_to_id_mapping(mock_create_gemini: MagicMock) -> None:
    """Map Gemini 1-based article indices to DB article IDs."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "headline": "Summary",
            "sections": [
                {
                    "theme": "AI/ML",
                    "title": "Theme",
                    "body": "Body",
                    "article_ids": [1, 3, 99],
                }
            ],
            "key_takeaways": [],
            "connections": "",
        }
    )

    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_service_supabase_mock(articles=SAMPLE_ARTICLES)

    digest, _article_ids = await generate_daily_digest(
        supabase,
        digest_date="2026-02-18",
        settings=_make_settings(),
    )

    assert digest["sections"][0]["article_ids"] == [101, 103]


@pytest.mark.asyncio
async def test_persist_digest_upsert() -> None:
    """Persist digest with upsert and return inserted ID."""
    supabase = _make_service_supabase_mock(upsert_result=[{"id": 42}])

    digest_id = await persist_digest(
        supabase,
        digest_date="2026-02-18",
        content={
            "headline": "Headline",
            "sections": [],
            "key_takeaways": [],
            "connections": "",
        },
        article_ids=[101, 102],
    )

    assert digest_id == 42

    upsert_call = supabase.table("digests").upsert.call_args
    row = upsert_call.args[0]
    assert row["digest_date"] == "2026-02-18"
    assert row["article_ids"] == [101, 102]
    assert row["article_count"] == 2
    assert isinstance(row["updated_at"], str)
    assert datetime.fromisoformat(row["updated_at"]) is not None
    assert upsert_call.kwargs["on_conflict"] == "digest_date"
