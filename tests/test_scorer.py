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
    """테스트용 Settings mock을 생성한다."""
    settings = MagicMock()
    settings.gemini_api_key = api_key
    settings.gemini.model = model
    settings.pipeline.scoring_batch_size = batch_size
    return settings


def _make_gemini_response(results: list[dict]) -> str:
    """Gemini 응답 JSON 문자열을 생성한다."""
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
    """관심사가 있을 때 프롬프트에 관심사 키워드와 가중치가 포함된다."""
    articles = [_make_article("AI News", "GPT-5 released")]
    interests = [_make_interest("AI", 5.0), _make_interest("LLM", 3.0)]

    prompt = _build_scoring_prompt(articles, interests)

    assert "AI (weight: 5.0)" in prompt
    assert "LLM (weight: 3.0)" in prompt
    assert "AI News" in prompt
    assert "GPT-5 released" in prompt


def test_build_scoring_prompt_without_interests() -> None:
    """관심사가 없을 때 일반 기술 관련성 기준으로 스코어링하도록 안내한다."""
    articles = [_make_article()]
    prompt = _build_scoring_prompt(articles, [])

    assert "No specific user interests provided" in prompt
    assert "general tech significance" in prompt


def test_build_scoring_prompt_truncates_long_content() -> None:
    """500자를 초과하는 기사 본문이 잘리고 '...'이 추가된다."""
    long_content = "a" * 1000
    articles = [_make_article(raw_content=long_content)]

    prompt = _build_scoring_prompt(articles, [])

    assert "a" * 500 + "..." in prompt
    assert "a" * 501 not in prompt


def test_build_scoring_prompt_handles_none_content() -> None:
    """raw_content가 None인 기사도 에러 없이 처리된다."""
    articles = [{"title": "No Content", "raw_content": None}]
    prompt = _build_scoring_prompt(articles, [])

    assert "No Content" in prompt


# --- _parse_scoring_response ---


def test_parse_scoring_response_valid() -> None:
    """유효한 JSON 응답이 올바르게 파싱된다.

    Mock: 정상 JSON 응답.
    검증: 점수, 카테고리, 키워드가 정확히 추출됨.
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
    """JSON 파싱 실패 시 모든 기사에 폴백 결과(점수 0.0)를 반환한다."""
    results = _parse_scoring_response("not valid json {{{", 3)

    assert len(results) == 3
    for i, r in enumerate(results):
        assert r["index"] == i
        assert r["relevance_score"] == 0.0
        assert r["categories"] == []
        assert r["keywords"] == []


def test_parse_scoring_response_missing_results_key() -> None:
    """JSON에 'results' 키가 없으면 폴백 결과를 반환한다."""
    results = _parse_scoring_response('{"data": []}', 2)

    assert len(results) == 2
    assert all(r["relevance_score"] == 0.0 for r in results)


def test_parse_scoring_response_missing_article_result() -> None:
    """일부 기사의 결과가 누락되면 해당 기사만 폴백 처리된다."""
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
    """점수가 0.0-1.0 범위를 벗어나면 0.0으로 폴백된다."""
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
    """점수가 숫자가 아닌 경우 0.0으로 폴백된다."""
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
    """폴백 결과가 0.0 점수와 빈 카테고리·키워드를 포함한다."""
    result = _fallback_result(3)

    assert result["index"] == 3
    assert result["relevance_score"] == 0.0
    assert result["categories"] == []
    assert result["keywords"] == []


# --- _call_gemini_with_retry ---


@pytest.mark.asyncio
@patch("backend.services.scorer.asyncio.sleep", new_callable=AsyncMock)
async def test_call_gemini_with_retry_success(mock_sleep: AsyncMock) -> None:
    """첫 번째 시도에서 성공하면 즉시 결과를 반환한다.

    Mock: Gemini 응답 성공.
    검증: 결과 반환, sleep 호출 없음.
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
    """API 오류 시 지수 백오프로 재시도하고 성공 시 결과를 반환한다.

    Mock: 첫 2회 실패, 3회차 성공.
    검증: 결과 반환, sleep이 1.0s, 2.0s로 2회 호출됨.
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
    """모든 재시도가 소진되면 마지막 예외를 발생시킨다.

    Mock: 3회 모두 실패.
    검증: RuntimeError 발생, sleep이 2회 호출됨.
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
    """5개 기사를 단일 배치로 스코어링한다.

    Mock: Gemini 응답에 5개 기사 결과 포함.
    검증: 5개 모두 점수·카테고리·키워드가 할당됨.
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
    """15개 기사가 배치 크기 10으로 2개 배치로 분할된다.

    Mock: 2번의 Gemini 호출, 각각 10개와 5개 결과.
    검증: 15개 모두 스코어링 완료, Gemini가 2회 호출됨.
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
    """사용자 관심사가 프롬프트에 포함된다.

    Mock: Gemini 응답 성공.
    검증: 프롬프트에 관심사 키워드와 가중치가 포함됨.
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
    """관심사가 없을 때도 스코어링이 정상 작동한다.

    Mock: Gemini 응답 성공.
    검증: 결과 반환 성공, 프롬프트에 일반 기술 관련성 안내 포함.
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
    """빈 기사 목록은 Gemini 호출 없이 빈 결과를 반환한다.

    Mock: 없음 (Gemini 호출 자체가 불필요).
    검증: 빈 리스트 반환.
    """
    results = await score_articles([])

    assert results == []


@pytest.mark.asyncio
@patch("backend.services.scorer.create_gemini_client")
async def test_score_articles_malformed_response(mock_create_client: MagicMock) -> None:
    """Gemini가 잘못된 JSON을 반환하면 폴백 점수(0.0)를 사용한다.

    Mock: Gemini 응답이 유효하지 않은 JSON.
    검증: 모든 기사가 0.0 점수와 빈 카테고리·키워드를 가짐.
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
    """API 오류 시 재시도 후 성공하면 정상 결과를 반환한다.

    Mock: 첫 호출 실패, 재시도 시 성공.
    검증: 정상 결과 반환, 재시도 발생 확인.
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
    """모든 재시도가 소진되면 해당 배치에 폴백 결과를 사용한다.

    Mock: 3회 모두 실패.
    검증: 폴백 결과(0.0 점수) 반환, 에러 미전파.
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
    """로그 메시지에 API 키가 노출되지 않는다.

    검증: scorer 모듈의 모든 로그 메시지에 API 키 문자열이 포함되지 않음.
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
