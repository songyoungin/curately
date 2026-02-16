"""Pipeline orchestrator service tests."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.pipeline import (
    _filter_articles,
    run_daily_pipeline,
)


# --- Helpers ---


def _make_article(
    title: str = "Test Article",
    source_url: str = "https://example.com/1",
    source_feed: str = "Test Feed",
    raw_content: str = "Some tech content",
    relevance_score: float | None = None,
) -> dict:
    """Create a mock article dict."""
    article: dict = {
        "title": title,
        "source_url": source_url,
        "source_feed": source_feed,
        "raw_content": raw_content,
        "author": "Author",
        "published_at": None,
    }
    if relevance_score is not None:
        article["relevance_score"] = relevance_score
    return article


def _make_score_result(
    index: int,
    score: float = 0.8,
    categories: list[str] | None = None,
    keywords: list[str] | None = None,
) -> dict:
    """Create a mock scoring result."""
    return {
        "index": index,
        "relevance_score": score,
        "categories": categories or ["AI/ML"],
        "keywords": keywords or ["machine learning"],
    }


def _make_settings(
    threshold: float = 0.3,
    max_articles: int = 20,
    batch_size: int = 10,
) -> MagicMock:
    """Create a mock Settings object."""
    settings = MagicMock()
    settings.pipeline.relevance_threshold = threshold
    settings.pipeline.max_articles_per_newsletter = max_articles
    settings.pipeline.scoring_batch_size = batch_size
    settings.gemini_api_key = "test-key"
    settings.gemini.model = "gemini-2.5-flash"
    return settings


def _make_supabase_mock(
    user_id: int = 1,
    interests: list[dict] | None = None,
) -> MagicMock:
    """Create a Supabase client mock for pipeline tests.

    Mocks:
        - users.select().eq().execute() -> user with given ID
        - user_interests.select().eq().order().limit().execute() -> interests
        - articles.upsert().execute() -> None
    """
    mock_client = MagicMock()
    interests_data = interests or []

    users_chain = MagicMock()
    users_chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": user_id}]
    )

    interests_chain = MagicMock()
    interests_chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=interests_data
    )

    articles_chain = MagicMock()
    articles_chain.upsert.return_value.execute.return_value = MagicMock()

    def table_router(name: str) -> MagicMock:
        if name == "users":
            return users_chain
        if name == "user_interests":
            return interests_chain
        if name == "articles":
            return articles_chain
        return MagicMock()

    mock_client.table.side_effect = table_router
    return mock_client


# --- _filter_articles ---


def test_filter_articles_excludes_below_threshold() -> None:
    """Verify articles below the relevance threshold are excluded."""
    articles = [
        _make_article("High", relevance_score=0.8),
        _make_article("Low", relevance_score=0.1),
        _make_article("Medium", relevance_score=0.5),
    ]
    result = _filter_articles(articles, threshold=0.3, max_count=20)
    assert len(result) == 2
    assert all(a["relevance_score"] >= 0.3 for a in result)


def test_filter_articles_sorts_by_score_desc() -> None:
    """Verify articles are sorted by relevance score descending."""
    articles = [
        _make_article("Low", relevance_score=0.4),
        _make_article("High", relevance_score=0.9),
        _make_article("Medium", relevance_score=0.6),
    ]
    result = _filter_articles(articles, threshold=0.3, max_count=20)
    scores = [a["relevance_score"] for a in result]
    assert scores == sorted(scores, reverse=True)


def test_filter_articles_limits_to_max_count() -> None:
    """Verify at most max_count articles are returned."""
    articles = [
        _make_article(
            f"Article {i}",
            source_url=f"https://example.com/{i}",
            relevance_score=0.5 + i * 0.01,
        )
        for i in range(10)
    ]
    result = _filter_articles(articles, threshold=0.3, max_count=3)
    assert len(result) == 3


def test_filter_articles_empty_when_all_below_threshold() -> None:
    """Verify empty list when all articles are below threshold."""
    articles = [
        _make_article("A", relevance_score=0.1),
        _make_article("B", relevance_score=0.2),
    ]
    result = _filter_articles(articles, threshold=0.3, max_count=20)
    assert result == []


# --- run_daily_pipeline ---


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_happy_path(
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify full pipeline happy path with 3 articles, 2 above threshold.

    Mocks: collector returns 3 articles, scorer returns scores (0.8, 0.2, 0.6),
           summarizer returns summary text.
    Expects: 2 articles filtered (above 0.3), 2 summarized, 2 persisted.
    """
    articles = [
        _make_article("Art 1", source_url="https://example.com/1"),
        _make_article("Art 2", source_url="https://example.com/2"),
        _make_article("Art 3", source_url="https://example.com/3"),
    ]
    mock_collect.return_value = articles
    mock_score.return_value = [
        _make_score_result(0, 0.8),
        _make_score_result(1, 0.2),
        _make_score_result(2, 0.6),
    ]
    mock_summarize.return_value = "Test summary"

    client = _make_supabase_mock()
    settings = _make_settings(threshold=0.3, max_articles=20)

    result = await run_daily_pipeline(client, settings)

    assert result["articles_collected"] == 3
    assert result["articles_scored"] == 3
    assert result["articles_filtered"] == 2
    assert result["articles_summarized"] == 2
    assert result["newsletter_date"] == date.today().isoformat()

    # Verify persist was called for 2 articles
    upsert_calls = client.table("articles").upsert.call_args_list
    assert len(upsert_calls) == 2


@pytest.mark.asyncio
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_empty_collection(mock_collect: AsyncMock) -> None:
    """Verify pipeline returns zeros when no articles are collected.

    Mocks: collector returns empty list.
    Expects: All counts are zero, scorer/summarizer not called.
    """
    mock_collect.return_value = []

    client = _make_supabase_mock()
    settings = _make_settings()

    result = await run_daily_pipeline(client, settings)

    assert result["articles_collected"] == 0
    assert result["articles_scored"] == 0
    assert result["articles_filtered"] == 0
    assert result["articles_summarized"] == 0


@pytest.mark.asyncio
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_scoring_failure(
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
) -> None:
    """Verify pipeline handles scoring failure gracefully.

    Mocks: collector returns 2 articles, scorer raises RuntimeError.
    Expects: articles_collected=2, articles_scored=0, pipeline aborts.
    """
    mock_collect.return_value = [
        _make_article("Art 1", source_url="https://example.com/1"),
    ]
    mock_score.side_effect = RuntimeError("Gemini API down")

    client = _make_supabase_mock()
    settings = _make_settings()

    result = await run_daily_pipeline(client, settings)

    assert result["articles_collected"] == 1
    assert result["articles_scored"] == 0
    assert result["articles_filtered"] == 0
    assert result["articles_summarized"] == 0


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_summarization_failure(
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify articles are persisted without summary on summarization failure.

    Mocks: collector returns 1 article, scorer returns score 0.8,
           summarizer raises RuntimeError.
    Expects: article persisted, articles_summarized=0, summary=None.
    """
    articles = [_make_article("Art 1", source_url="https://example.com/1")]
    mock_collect.return_value = articles
    mock_score.return_value = [_make_score_result(0, 0.8)]
    mock_summarize.side_effect = RuntimeError("Summary failed")

    client = _make_supabase_mock()
    settings = _make_settings(threshold=0.3)

    result = await run_daily_pipeline(client, settings)

    assert result["articles_collected"] == 1
    assert result["articles_scored"] == 1
    assert result["articles_filtered"] == 1
    assert result["articles_summarized"] == 0

    # Article should still be persisted
    upsert_calls = client.table("articles").upsert.call_args_list
    assert len(upsert_calls) == 1
    row = upsert_calls[0].args[0]
    assert row["summary"] is None


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_filtering_threshold_and_top_n(
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify filtering respects both threshold and max_count.

    Mocks: 5 articles scored [0.9, 0.7, 0.5, 0.3, 0.1],
           threshold=0.3, max_articles=2.
    Expects: 2 articles returned (top 2 of 4 above threshold).
    """
    articles = [
        _make_article(f"Art {i}", source_url=f"https://example.com/{i}")
        for i in range(5)
    ]
    mock_collect.return_value = articles
    mock_score.return_value = [
        _make_score_result(0, 0.9),
        _make_score_result(1, 0.7),
        _make_score_result(2, 0.5),
        _make_score_result(3, 0.3),
        _make_score_result(4, 0.1),
    ]
    mock_summarize.return_value = "Summary"

    client = _make_supabase_mock()
    settings = _make_settings(threshold=0.3, max_articles=2)

    result = await run_daily_pipeline(client, settings)

    assert result["articles_filtered"] == 2
    assert result["articles_summarized"] == 2


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_newsletter_date_is_today(
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify newsletter_date in result and persisted rows matches today's date.

    Mocks: 1 article collected and scored above threshold.
    Expects: newsletter_date equals today's ISO date string.
    """
    articles = [_make_article("Art 1", source_url="https://example.com/1")]
    mock_collect.return_value = articles
    mock_score.return_value = [_make_score_result(0, 0.8)]
    mock_summarize.return_value = "Summary"

    client = _make_supabase_mock()
    settings = _make_settings()

    result = await run_daily_pipeline(client, settings)

    expected_date = date.today().isoformat()
    assert result["newsletter_date"] == expected_date

    # Verify persisted row has correct newsletter_date
    upsert_calls = client.table("articles").upsert.call_args_list
    assert len(upsert_calls) == 1
    row = upsert_calls[0].args[0]
    assert row["newsletter_date"] == expected_date
