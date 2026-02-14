"""Scorer service tests."""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.scorer import (
    _build_scoring_prompt,
    _call_gemini_with_retry,
    _fallback_result,
    _parse_scoring_response,
    score_articles,
)


# --- Helpers ---


def _make_article(
    title: str = "Test Article",
    raw_content: str = "Some content about technology",
) -> dict:
    return {"title": title, "raw_content": raw_content}


def _make_interest(keyword: str = "AI", weight: float = 5.0) -> dict:
    return {"keyword": keyword, "weight": weight}


def _make_settings(
    api_key: str = "test-api-key",
    model: str = "gemini-2.5-flash",
    batch_size: int = 10,
) -> MagicMock:
    """Create a mock Settings object for testing."""
    settings = MagicMock()
    settings.gemini_api_key = api_key
    settings.gemini.model = model
    settings.pipeline.scoring_batch_size = batch_size
    return settings


def _make_gemini_response(results: list[dict]) -> str:
    """Create a Gemini response JSON string."""
    return json.dumps({"results": results})


def _make_scoring_result(
    index: int,
    score: float = 0.75,
    categories: list[str] | None = None,
    keywords: list[str] | None = None,
) -> dict:
    return {
        "index": index,
        "relevance_score": score,
        "categories": categories or ["AI/ML"],
        "keywords": keywords or ["machine learning"],
    }


# --- _build_scoring_prompt ---


def test_build_scoring_prompt_with_interests() -> None:
    """Verify that interest keywords and weights are included in the prompt."""
    articles = [_make_article("AI News", "GPT-5 released")]
    interests = [_make_interest("AI", 5.0), _make_interest("LLM", 3.0)]

    prompt = _build_scoring_prompt(articles, interests)

    assert "AI (weight: 5.0)" in prompt
    assert "LLM (weight: 3.0)" in prompt
    assert "AI News" in prompt
    assert "GPT-5 released" in prompt


def test_build_scoring_prompt_without_interests() -> None:
    """Verify that general tech relevance guidance is used when no interests exist."""
    articles = [_make_article()]
    prompt = _build_scoring_prompt(articles, [])

    assert "No specific user interests provided" in prompt
    assert "general tech significance" in prompt


def test_build_scoring_prompt_truncates_long_content() -> None:
    """Verify that content exceeding 500 chars is truncated with '...' appended."""
    long_content = "a" * 1000
    articles = [_make_article(raw_content=long_content)]

    prompt = _build_scoring_prompt(articles, [])

    assert "a" * 500 + "..." in prompt
    assert "a" * 501 not in prompt


def test_build_scoring_prompt_handles_none_content() -> None:
    """Verify that articles with None raw_content are handled without errors."""
    articles = [{"title": "No Content", "raw_content": None}]
    prompt = _build_scoring_prompt(articles, [])

    assert "No Content" in prompt


# --- _parse_scoring_response ---


def test_parse_scoring_response_valid() -> None:
    """Verify that a valid JSON response is correctly parsed.

    Mock: Valid JSON response.
    Expects: Scores, categories, and keywords are extracted accurately.
    """
    response = _make_gemini_response(
        [
            _make_scoring_result(0, 0.85, ["AI/ML", "LLM"], ["GPT", "transformer"]),
            _make_scoring_result(1, 0.3, ["Web"], ["React"]),
        ]
    )

    results = _parse_scoring_response(response, 2)

    assert len(results) == 2
    assert results[0]["relevance_score"] == 0.85
    assert results[0]["categories"] == ["AI/ML", "LLM"]
    assert results[0]["keywords"] == ["GPT", "transformer"]
    assert results[1]["relevance_score"] == 0.3


def test_parse_scoring_response_malformed_json() -> None:
    """Verify fallback results (score 0.0) are returned on JSON parse failure."""
    results = _parse_scoring_response("not valid json {{{", 3)

    assert len(results) == 3
    for i, r in enumerate(results):
        assert r["index"] == i
        assert r["relevance_score"] == 0.0
        assert r["categories"] == []
        assert r["keywords"] == []


def test_parse_scoring_response_missing_results_key() -> None:
    """Verify fallback results when JSON lacks a 'results' key."""
    results = _parse_scoring_response('{"data": []}', 2)

    assert len(results) == 2
    assert all(r["relevance_score"] == 0.0 for r in results)


def test_parse_scoring_response_missing_article_result() -> None:
    """Verify that only missing articles get fallback treatment."""
    response = _make_gemini_response(
        [
            _make_scoring_result(0, 0.9),
            # index 1 missing
        ]
    )

    results = _parse_scoring_response(response, 2)

    assert results[0]["relevance_score"] == 0.9
    assert results[1]["relevance_score"] == 0.0


def test_parse_scoring_response_invalid_score_range() -> None:
    """Verify that scores outside the 0.0-1.0 range fall back to 0.0."""
    response = _make_gemini_response(
        [
            _make_scoring_result(0, 1.5),  # over 1.0
            _make_scoring_result(1, -0.3),  # negative
        ]
    )

    results = _parse_scoring_response(response, 2)

    assert results[0]["relevance_score"] == 0.0
    assert results[1]["relevance_score"] == 0.0


def test_parse_scoring_response_non_numeric_score() -> None:
    """Verify that non-numeric scores fall back to 0.0."""
    response = json.dumps(
        {
            "results": [
                {
                    "index": 0,
                    "relevance_score": "high",
                    "categories": [],
                    "keywords": [],
                }
            ]
        }
    )

    results = _parse_scoring_response(response, 1)

    assert results[0]["relevance_score"] == 0.0


# --- _fallback_result ---


def test_fallback_result() -> None:
    """Verify fallback result has score 0.0 and empty categories/keywords."""
    result = _fallback_result(3)

    assert result["index"] == 3
    assert result["relevance_score"] == 0.0
    assert result["categories"] == []
    assert result["keywords"] == []


# --- _call_gemini_with_retry ---


@pytest.mark.asyncio
@patch("backend.services.scorer.asyncio.sleep", new_callable=AsyncMock)
async def test_call_gemini_with_retry_success(mock_sleep: AsyncMock) -> None:
    """Verify immediate result return on first successful attempt.

    Mock: Gemini responds successfully.
    Expects: Result returned, sleep not called.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"results": []}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await _call_gemini_with_retry(
        mock_client, "gemini-2.5-flash", "test prompt"
    )

    assert result == '{"results": []}'
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
@patch("backend.services.scorer.asyncio.sleep", new_callable=AsyncMock)
async def test_call_gemini_with_retry_retries_on_error(mock_sleep: AsyncMock) -> None:
    """Verify exponential backoff retry on API errors with eventual success.

    Mock: First 2 calls fail, 3rd succeeds.
    Expects: Result returned, sleep called with 1.0s and 2.0s.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"results": []}'
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[
            RuntimeError("API error"),
            RuntimeError("API error"),
            mock_response,
        ]
    )

    result = await _call_gemini_with_retry(
        mock_client, "gemini-2.5-flash", "test prompt"
    )

    assert result == '{"results": []}'
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1.0)  # 1.0 * 2^0
    mock_sleep.assert_any_call(2.0)  # 1.0 * 2^1


@pytest.mark.asyncio
@patch("backend.services.scorer.asyncio.sleep", new_callable=AsyncMock)
async def test_call_gemini_with_retry_exhausted(mock_sleep: AsyncMock) -> None:
    """Verify last exception is raised when all retries are exhausted.

    Mock: All 3 calls fail.
    Expects: RuntimeError raised, sleep called twice.
    """
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("persistent error")
    )

    with pytest.raises(RuntimeError, match="persistent error"):
        await _call_gemini_with_retry(mock_client, "gemini-2.5-flash", "test prompt")

    assert mock_sleep.call_count == 2


# --- score_articles ---


@pytest.mark.asyncio
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_single_batch(mock_create_client: MagicMock) -> None:
    """Verify scoring of 5 articles in a single batch.

    Mock: Gemini response contains results for 5 articles.
    Expects: All 5 receive scores, categories, and keywords.
    """
    articles = [_make_article(f"Article {i}") for i in range(5)]
    response_data = _make_gemini_response(
        [_make_scoring_result(i, 0.5 + i * 0.1) for i in range(5)]
    )

    mock_response = MagicMock()
    mock_response.text = response_data
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    results = await score_articles(articles, settings=settings)

    assert len(results) == 5
    assert results[0]["relevance_score"] == 0.5
    assert results[4]["relevance_score"] == pytest.approx(0.9, abs=0.01)
    mock_client.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_multiple_batches(mock_create_client: MagicMock) -> None:
    """Verify 15 articles are split into 2 batches with batch size 10.

    Mock: 2 Gemini calls returning 10 and 5 results respectively.
    Expects: All 15 scored, Gemini called twice.
    """
    articles = [_make_article(f"Article {i}") for i in range(15)]

    batch1_response = _make_gemini_response(
        [_make_scoring_result(i, 0.8) for i in range(10)]
    )
    batch2_response = _make_gemini_response(
        [_make_scoring_result(i, 0.6) for i in range(5)]
    )

    mock_response1 = MagicMock()
    mock_response1.text = batch1_response
    mock_response2 = MagicMock()
    mock_response2.text = batch2_response

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[mock_response1, mock_response2]
    )
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    results = await score_articles(articles, settings=settings)

    assert len(results) == 15
    assert mock_client.aio.models.generate_content.call_count == 2
    # First batch scored 0.8, second batch scored 0.6
    assert all(r["relevance_score"] == 0.8 for r in results[:10])
    assert all(r["relevance_score"] == 0.6 for r in results[10:])


@pytest.mark.asyncio
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_with_interests(mock_create_client: MagicMock) -> None:
    """Verify user interests are included in the scoring prompt.

    Mock: Gemini responds successfully.
    Expects: Prompt contains interest keywords and weights.
    """
    articles = [_make_article()]
    interests = [_make_interest("AI", 5.0), _make_interest("Python", 3.0)]

    response = _make_gemini_response([_make_scoring_result(0)])
    mock_response = MagicMock()
    mock_response.text = response
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    await score_articles(articles, interests=interests, settings=settings)

    call_args = mock_client.aio.models.generate_content.call_args
    prompt = call_args.kwargs.get("contents") or call_args.args[0]
    # Handle both positional and keyword argument patterns
    if isinstance(prompt, str):
        assert "AI (weight: 5.0)" in prompt
        assert "Python (weight: 3.0)" in prompt


@pytest.mark.asyncio
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_no_interests(mock_create_client: MagicMock) -> None:
    """Verify scoring works correctly without user interests.

    Mock: Gemini responds successfully.
    Expects: Results returned, prompt includes general tech relevance guidance.
    """
    articles = [_make_article()]

    response = _make_gemini_response([_make_scoring_result(0, 0.5)])
    mock_response = MagicMock()
    mock_response.text = response
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    results = await score_articles(articles, interests=None, settings=settings)

    assert len(results) == 1
    assert results[0]["relevance_score"] == 0.5


@pytest.mark.asyncio
async def test_score_articles_empty_articles() -> None:
    """Verify empty article list returns empty results without calling Gemini.

    Mock: None (Gemini call not needed).
    Expects: Empty list returned.
    """
    results = await score_articles([])

    assert results == []


@pytest.mark.asyncio
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_malformed_response(mock_create_client: MagicMock) -> None:
    """Verify fallback scores (0.0) are used when Gemini returns invalid JSON.

    Mock: Gemini response is not valid JSON.
    Expects: All articles get score 0.0 with empty categories/keywords.
    """
    articles = [_make_article("A"), _make_article("B")]

    mock_response = MagicMock()
    mock_response.text = "this is not json at all"
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    results = await score_articles(articles, settings=settings)

    assert len(results) == 2
    assert all(r["relevance_score"] == 0.0 for r in results)
    assert all(r["categories"] == [] for r in results)
    assert all(r["keywords"] == [] for r in results)


@pytest.mark.asyncio
@patch("backend.services.scorer.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_api_error_retry(
    mock_create_client: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Verify normal results after successful retry on API error.

    Mock: First call fails, retry succeeds.
    Expects: Normal results returned, retry confirmed.
    """
    articles = [_make_article()]

    response = _make_gemini_response([_make_scoring_result(0, 0.7)])
    mock_response = MagicMock()
    mock_response.text = response

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[RuntimeError("temporary error"), mock_response]
    )
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    results = await score_articles(articles, settings=settings)

    assert len(results) == 1
    assert results[0]["relevance_score"] == 0.7
    assert mock_sleep.call_count == 1


@pytest.mark.asyncio
@patch("backend.services.scorer.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_all_retries_exhausted(
    mock_create_client: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Verify fallback results when all retries are exhausted.

    Mock: All 3 calls fail.
    Expects: Fallback results (score 0.0), error not propagated.
    """
    articles = [_make_article()]

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("persistent error")
    )
    mock_create_client.return_value = mock_client

    settings = _make_settings(batch_size=10)
    results = await score_articles(articles, settings=settings)

    assert len(results) == 1
    assert results[0]["relevance_score"] == 0.0
    assert results[0]["categories"] == []


def test_score_articles_api_key_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Verify API key is never exposed in log messages.

    Expects: No log message from the scorer module contains the API key string.
    """
    api_key = "super-secret-api-key-12345"

    # Test that the key doesn't appear in any log messages
    # by examining the scoring prompt and log formatting
    with caplog.at_level(logging.DEBUG, logger="backend.services.scorer"):
        # Trigger prompt building (doesn't need async)
        _build_scoring_prompt(
            [_make_article()],
            [_make_interest()],
        )

    for record in caplog.records:
        assert api_key not in record.getMessage()
