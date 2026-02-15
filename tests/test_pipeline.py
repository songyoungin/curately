"""Pipeline orchestrator and endpoint tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.pipeline import run_daily_pipeline

client = TestClient(app)


# --- Helpers ---


def _make_article(
    index: int,
    title: str = "Article",
    source_url: str | None = None,
    raw_content: str = "Some content about technology.",
) -> dict:
    """Create a sample article dict as returned by the collector."""
    return {
        "source_feed": "Test Feed",
        "source_url": source_url or f"https://example.com/article-{index}",
        "title": f"{title} {index}",
        "author": f"Author {index}",
        "published_at": None,
        "raw_content": raw_content,
    }


def _make_score_result(index: int, score: float) -> dict:
    """Create a sample scoring result dict."""
    return {
        "index": index,
        "relevance_score": score,
        "categories": ["AI/ML", "Web"],
        "keywords": ["python", "llm", "api"],
    }


def _make_supabase_mock(
    user_id: int = 1,
    interests: list[dict] | None = None,
    has_user: bool = True,
) -> MagicMock:
    """Create a Supabase client mock for pipeline tests.

    Mocks:
        - users.select().eq().execute() -> user row with given id
        - user_interests.select().eq().order().limit().execute() -> interests
        - articles.insert().execute() -> success
    """
    mock_client = MagicMock()

    # users table
    users_chain = MagicMock()
    user_data = [{"id": user_id}] if has_user else []
    users_chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=user_data
    )

    # user_interests table
    interests_chain = MagicMock()
    interests_data = interests if interests is not None else []
    interests_chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=interests_data
    )

    # articles table
    articles_chain = MagicMock()
    articles_chain.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

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


# --- Tests ---


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.get_supabase_client")
@patch("backend.services.pipeline.get_settings")
async def test_run_daily_pipeline_full_flow(
    mock_settings: MagicMock,
    mock_get_client: MagicMock,
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify full happy path: collect -> score -> filter -> summarize -> persist.

    Mock: 3 articles collected, all scored above threshold, summaries generated.
    Expects: All 3 articles saved, result stats match.
    """
    # Setup settings
    settings = MagicMock()
    settings.pipeline.relevance_threshold = 0.3
    settings.pipeline.max_articles_per_newsletter = 20
    settings.pipeline.scoring_batch_size = 10
    mock_settings.return_value = settings

    # Setup Supabase mock
    mock_client = _make_supabase_mock(
        interests=[
            {"keyword": "python", "weight": 5.0},
            {"keyword": "ai", "weight": 3.0},
        ]
    )
    mock_get_client.return_value = mock_client

    # Setup collector
    articles = [_make_article(i) for i in range(3)]
    mock_collect.return_value = articles

    # Setup scorer
    mock_score.return_value = [
        _make_score_result(0, 0.9),
        _make_score_result(1, 0.7),
        _make_score_result(2, 0.5),
    ]

    # Setup summarizer
    mock_summarize.return_value = "Test summary text."

    result = await run_daily_pipeline()

    assert result["articles_collected"] == 3
    assert result["articles_scored"] == 3
    assert result["articles_filtered"] == 3
    assert result["articles_saved"] == 3
    assert result["newsletter_date"] == datetime.now(tz=UTC).date().isoformat()

    # Verify collector was called
    mock_collect.assert_awaited_once()

    # Verify scorer was called with articles and interests
    mock_score.assert_awaited_once()
    score_call_args = mock_score.call_args
    assert len(score_call_args[0][0]) == 3  # 3 articles passed

    # Verify summarizer was called for each article
    assert mock_summarize.await_count == 3

    # Verify persist: articles.insert was called 3 times
    articles_chain = mock_client.table("articles")
    assert articles_chain.insert.call_count == 3


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.get_supabase_client")
@patch("backend.services.pipeline.get_settings")
async def test_pipeline_filters_below_threshold(
    mock_settings: MagicMock,
    mock_get_client: MagicMock,
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify articles below the relevance threshold are excluded.

    Mock: 3 articles, 1 below threshold (0.2).
    Expects: Only 2 articles pass filtering, 2 saved.
    """
    settings = MagicMock()
    settings.pipeline.relevance_threshold = 0.3
    settings.pipeline.max_articles_per_newsletter = 20
    settings.pipeline.scoring_batch_size = 10
    mock_settings.return_value = settings

    mock_client = _make_supabase_mock()
    mock_get_client.return_value = mock_client

    articles = [_make_article(i) for i in range(3)]
    mock_collect.return_value = articles

    mock_score.return_value = [
        _make_score_result(0, 0.8),
        _make_score_result(1, 0.2),  # Below threshold
        _make_score_result(2, 0.6),
    ]

    mock_summarize.return_value = "Summary text."

    result = await run_daily_pipeline()

    assert result["articles_collected"] == 3
    assert result["articles_scored"] == 3
    assert result["articles_filtered"] == 2
    assert result["articles_saved"] == 2

    # Only 2 articles should be summarized
    assert mock_summarize.await_count == 2


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.get_supabase_client")
@patch("backend.services.pipeline.get_settings")
async def test_pipeline_limits_to_max_articles(
    mock_settings: MagicMock,
    mock_get_client: MagicMock,
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify only top N articles by score are kept after filtering.

    Mock: 25 articles all above threshold, max_articles_per_newsletter=20.
    Expects: Only 20 articles pass filtering.
    """
    settings = MagicMock()
    settings.pipeline.relevance_threshold = 0.3
    settings.pipeline.max_articles_per_newsletter = 20
    settings.pipeline.scoring_batch_size = 10
    mock_settings.return_value = settings

    mock_client = _make_supabase_mock()
    mock_get_client.return_value = mock_client

    articles = [_make_article(i) for i in range(25)]
    mock_collect.return_value = articles

    # All articles score above threshold (0.4 to 0.89)
    mock_score.return_value = [_make_score_result(i, 0.4 + i * 0.02) for i in range(25)]

    mock_summarize.return_value = "Summary text."

    result = await run_daily_pipeline()

    assert result["articles_collected"] == 25
    assert result["articles_scored"] == 25
    assert result["articles_filtered"] == 20
    assert result["articles_saved"] == 20

    # Only 20 articles should be summarized
    assert mock_summarize.await_count == 20


@pytest.mark.asyncio
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.get_supabase_client")
@patch("backend.services.pipeline.get_settings")
async def test_pipeline_no_articles_collected(
    mock_settings: MagicMock,
    mock_get_client: MagicMock,
    mock_collect: AsyncMock,
) -> None:
    """Verify pipeline returns early when no articles are collected.

    Mock: Collector returns empty list.
    Expects: All counts are zero, no scoring/summarization occurs.
    """
    settings = MagicMock()
    mock_settings.return_value = settings

    mock_client = _make_supabase_mock()
    mock_get_client.return_value = mock_client

    mock_collect.return_value = []

    result = await run_daily_pipeline()

    assert result["articles_collected"] == 0
    assert result["articles_scored"] == 0
    assert result["articles_filtered"] == 0
    assert result["articles_saved"] == 0
    assert result["newsletter_date"] == datetime.now(tz=UTC).date().isoformat()


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.get_supabase_client")
@patch("backend.services.pipeline.get_settings")
async def test_pipeline_no_interests(
    mock_settings: MagicMock,
    mock_get_client: MagicMock,
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify pipeline works when no user interests are found.

    Mock: Empty interests list, 2 articles collected.
    Expects: Scoring still proceeds with empty interests.
    """
    settings = MagicMock()
    settings.pipeline.relevance_threshold = 0.3
    settings.pipeline.max_articles_per_newsletter = 20
    settings.pipeline.scoring_batch_size = 10
    mock_settings.return_value = settings

    mock_client = _make_supabase_mock(interests=[])
    mock_get_client.return_value = mock_client

    articles = [_make_article(i) for i in range(2)]
    mock_collect.return_value = articles

    mock_score.return_value = [
        _make_score_result(0, 0.5),
        _make_score_result(1, 0.6),
    ]

    mock_summarize.return_value = "Summary."

    result = await run_daily_pipeline()

    assert result["articles_collected"] == 2
    assert result["articles_scored"] == 2
    assert result["articles_filtered"] == 2

    # Scorer should be called with empty interests list
    score_call_args = mock_score.call_args
    assert score_call_args[0][1] == []  # interests argument


@pytest.mark.asyncio
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.get_supabase_client")
@patch("backend.services.pipeline.get_settings")
async def test_pipeline_sets_newsletter_date(
    mock_settings: MagicMock,
    mock_get_client: MagicMock,
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
) -> None:
    """Verify newsletter_date is set to today's date on persisted articles.

    Mock: 1 article collected, scored above threshold.
    Expects: Insert row includes newsletter_date matching today.
    """
    settings = MagicMock()
    settings.pipeline.relevance_threshold = 0.3
    settings.pipeline.max_articles_per_newsletter = 20
    settings.pipeline.scoring_batch_size = 10
    mock_settings.return_value = settings

    mock_client = _make_supabase_mock()
    mock_get_client.return_value = mock_client

    articles = [_make_article(0)]
    mock_collect.return_value = articles

    mock_score.return_value = [_make_score_result(0, 0.8)]
    mock_summarize.return_value = "Summary."

    result = await run_daily_pipeline()

    today = datetime.now(tz=UTC).date().isoformat()
    assert result["newsletter_date"] == today

    # Check the persisted row has the correct newsletter_date
    articles_chain = mock_client.table("articles")
    insert_call = articles_chain.insert.call_args
    inserted_row = insert_call[0][0]
    assert inserted_row["newsletter_date"] == today


@patch("backend.routers.pipeline.run_daily_pipeline", new_callable=AsyncMock)
def test_trigger_pipeline_endpoint(mock_pipeline: AsyncMock) -> None:
    """Verify POST /api/pipeline/run returns correct response shape.

    Mock: run_daily_pipeline returns sample result.
    Expects: 200 status, response includes all expected fields.
    """
    mock_pipeline.return_value = {
        "articles_collected": 10,
        "articles_scored": 10,
        "articles_filtered": 5,
        "articles_saved": 5,
        "newsletter_date": "2026-02-15",
    }

    response = client.post("/api/pipeline/run")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Pipeline completed successfully"
    assert data["articles_collected"] == 10
    assert data["articles_scored"] == 10
    assert data["articles_filtered"] == 5
    assert data["articles_saved"] == 5
    assert data["newsletter_date"] == "2026-02-15"
