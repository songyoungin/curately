"""Summarizer service tests."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from backend.services.summarizer import (
    _fallback_detailed_summary,
    _parse_detailed_summary,
    _truncate_content,
    generate_basic_summary,
    generate_detailed_summary,
)


# --- Fixtures ---

_SAMPLE_TITLE = "OpenAI Releases GPT-5 with Multimodal Capabilities"
_SAMPLE_CONTENT = "OpenAI has announced the release of GPT-5, featuring..."

_BASIC_SUMMARY_RESPONSE = (
    "OpenAI가 멀티모달 기능을 갖춘 GPT-5를 출시했습니다. "
    "이번 모델은 텍스트, 이미지, 오디오를 동시에 처리할 수 있어 "
    "기술 전문가들에게 큰 영향을 미칠 것으로 보입니다."
)

_DETAILED_SUMMARY_RESPONSE = json.dumps(
    {
        "background": "OpenAI가 GPT-5를 출시하며 AI 업계에 큰 변화를 예고했습니다.",
        "takeaways": [
            "멀티모달 처리 능력이 대폭 향상되었습니다.",
            "추론 성능이 이전 모델 대비 크게 개선되었습니다.",
            "API 가격이 인하되어 접근성이 높아졌습니다.",
        ],
        "keywords": ["GPT-5", "multimodal", "LLM", "OpenAI"],
    },
    ensure_ascii=False,
)


def _make_gemini_response(text: str) -> MagicMock:
    """Gemini API 응답 객체를 모사하는 MagicMock을 생성한다."""
    response = MagicMock()
    response.text = text
    return response


def _make_settings_mock() -> MagicMock:
    """Settings mock을 생성한다. gemini.model과 gemini_api_key를 포함."""
    settings = MagicMock()
    settings.gemini.model = "gemini-2.5-flash"
    settings.gemini_api_key = "test-api-key"
    return settings


# --- _truncate_content ---


def test_truncate_content_short() -> None:
    """짧은 콘텐츠는 그대로 반환된다."""
    assert _truncate_content("short text") == "short text"


def test_truncate_content_none() -> None:
    """None 입력은 빈 문자열로 반환된다."""
    assert _truncate_content(None) == ""


def test_truncate_content_empty() -> None:
    """빈 문자열은 그대로 반환된다."""
    assert _truncate_content("") == ""


def test_truncate_content_long() -> None:
    """최대 길이를 초과하는 콘텐츠는 잘리고 '...'이 추가된다."""
    long_text = "x" * 20_000
    result = _truncate_content(long_text)
    assert len(result) == 15_003  # 15000 + "..."
    assert result.endswith("...")


# --- _parse_detailed_summary ---


def test_parse_detailed_summary_valid_json() -> None:
    """유효한 JSON 응답이 DetailedSummary로 올바르게 파싱된다."""
    result = _parse_detailed_summary(_DETAILED_SUMMARY_RESPONSE)
    assert (
        result["background"]
        == "OpenAI가 GPT-5를 출시하며 AI 업계에 큰 변화를 예고했습니다."
    )
    assert len(result["takeaways"]) == 3
    assert len(result["keywords"]) == 4
    assert "GPT-5" in result["keywords"]


def test_parse_detailed_summary_malformed_json() -> None:
    """잘못된 JSON 응답은 폴백으로 처리된다.

    검증: background에 원본 텍스트, takeaways/keywords는 빈 리스트.
    """
    result = _parse_detailed_summary("This is not valid JSON at all")
    assert result["background"] == "This is not valid JSON at all"
    assert result["takeaways"] == []
    assert result["keywords"] == []


def test_parse_detailed_summary_missing_fields() -> None:
    """일부 필드가 누락된 JSON도 기본값으로 처리된다.

    검증: 누락된 필드는 빈 문자열/리스트로 대체.
    """
    partial = json.dumps({"background": "Some background"})
    result = _parse_detailed_summary(partial)
    assert result["background"] == "Some background"
    assert result["takeaways"] == []
    assert result["keywords"] == []


def test_parse_detailed_summary_wrong_types() -> None:
    """필드 타입이 잘못된 JSON도 안전하게 처리된다.

    검증: 타입이 맞지 않는 값은 str 변환 또는 빈 리스트로 대체.
    """
    wrong_types = json.dumps(
        {"background": 123, "takeaways": "not a list", "keywords": None}
    )
    result = _parse_detailed_summary(wrong_types)
    assert result["background"] == "123"
    assert result["takeaways"] == []
    assert result["keywords"] == []


# --- _fallback_detailed_summary ---


def test_fallback_detailed_summary() -> None:
    """폴백 함수가 원본 텍스트를 background에 넣어 반환한다."""
    result = _fallback_detailed_summary("  some raw text  ")
    assert result["background"] == "some raw text"
    assert result["takeaways"] == []
    assert result["keywords"] == []


def test_fallback_detailed_summary_empty() -> None:
    """빈 텍스트의 폴백은 빈 background를 반환한다."""
    result = _fallback_detailed_summary("")
    assert result["background"] == ""


# --- generate_basic_summary ---


@pytest.mark.asyncio
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_basic_summary_success(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """Gemini API가 정상 응답을 반환하면 한국어 요약 텍스트를 반환한다.

    Mock: Gemini generate_content → 한국어 요약 텍스트.
    검증: 반환된 요약이 strip된 응답 텍스트와 일치.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        _BASIC_SUMMARY_RESPONSE
    )
    mock_get_client.return_value = mock_client

    result = await generate_basic_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    assert result == _BASIC_SUMMARY_RESPONSE
    mock_client.models.generate_content.assert_called_once()


@pytest.mark.asyncio
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_basic_summary_empty_content(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """콘텐츠가 None이어도 정상적으로 요약을 생성한다.

    Mock: Gemini generate_content → 한국어 요약 텍스트.
    검증: content=None이어도 프롬프트에 '(no content)' 대체 후 호출 성공.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        _BASIC_SUMMARY_RESPONSE
    )
    mock_get_client.return_value = mock_client

    result = await generate_basic_summary(_SAMPLE_TITLE, None)

    assert result == _BASIC_SUMMARY_RESPONSE
    call_args = mock_client.models.generate_content.call_args
    assert "(no content)" in call_args.kwargs["contents"]


@pytest.mark.asyncio
@patch("backend.services.summarizer.asyncio.sleep", return_value=None)
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_basic_summary_api_error_retry(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """API 에러 발생 시 재시도 후 성공하면 결과를 반환한다.

    Mock: 첫 번째 호출 RuntimeError, 두 번째 호출 성공.
    검증: 2회 호출, sleep 1회, 최종 결과 반환.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        RuntimeError("API error"),
        _make_gemini_response(_BASIC_SUMMARY_RESPONSE),
    ]
    mock_get_client.return_value = mock_client

    result = await generate_basic_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    assert result == _BASIC_SUMMARY_RESPONSE
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


@pytest.mark.asyncio
@patch("backend.services.summarizer.asyncio.sleep", return_value=None)
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_basic_summary_all_retries_fail(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """모든 재시도가 실패하면 마지막 예외가 발생한다.

    Mock: 3회 모두 RuntimeError.
    검증: RuntimeError 발생, 3회 호출, sleep 2회.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API error")
    mock_get_client.return_value = mock_client

    with pytest.raises(RuntimeError, match="API error"):
        await generate_basic_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    assert mock_client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


# --- generate_detailed_summary ---


@pytest.mark.asyncio
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_detailed_summary_success(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """정상 JSON 응답이 DetailedSummary 구조로 파싱된다.

    Mock: Gemini generate_content → JSON 문자열 (background, takeaways, keywords).
    검증: 반환값이 DetailedSummary 구조이고 각 필드가 올바름.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        _DETAILED_SUMMARY_RESPONSE
    )
    mock_get_client.return_value = mock_client

    result = await generate_detailed_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    assert isinstance(result, dict)
    assert "background" in result
    assert "takeaways" in result
    assert "keywords" in result
    assert len(result["takeaways"]) == 3
    assert len(result["keywords"]) == 4


@pytest.mark.asyncio
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_detailed_summary_malformed_response(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """Gemini가 잘못된 JSON을 반환하면 폴백으로 처리한다.

    Mock: Gemini generate_content → 유효하지 않은 JSON 텍스트.
    검증: background에 원본 텍스트, takeaways/keywords 빈 리스트.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        "Not valid JSON response from Gemini"
    )
    mock_get_client.return_value = mock_client

    result = await generate_detailed_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    assert result["background"] == "Not valid JSON response from Gemini"
    assert result["takeaways"] == []
    assert result["keywords"] == []


@pytest.mark.asyncio
@patch("backend.services.summarizer.asyncio.sleep", return_value=None)
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_detailed_summary_api_error_retry(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """상세 요약 생성에서도 API 에러 시 재시도가 동작한다.

    Mock: 첫 번째 호출 RuntimeError, 두 번째 호출 정상 JSON.
    검증: 2회 호출, 재시도 후 정상 결과 반환.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        RuntimeError("API error"),
        _make_gemini_response(_DETAILED_SUMMARY_RESPONSE),
    ]
    mock_get_client.return_value = mock_client

    result = await generate_detailed_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    assert len(result["takeaways"]) == 3
    assert mock_client.models.generate_content.call_count == 2


# --- Security: API key not logged ---


@pytest.mark.asyncio
@patch("backend.services.summarizer.asyncio.sleep", return_value=None)
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_summarizer_api_key_not_logged(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
    mock_sleep: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """API 에러 로깅 시 API 키가 로그에 노출되지 않는다.

    Mock: Gemini API 호출 3회 모두 실패 (RuntimeError).
    검증: 로그 메시지에 API 키 문자열이 포함되지 않음.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API error")
    mock_get_client.return_value = mock_client

    with caplog.at_level(logging.WARNING, logger="backend.services.summarizer"):
        with pytest.raises(RuntimeError):
            await generate_basic_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT)

    for record in caplog.records:
        assert "test-api-key" not in record.getMessage()


# --- Long content truncation ---


@pytest.mark.asyncio
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_basic_summary_long_content(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """매우 긴 콘텐츠는 잘려서 프롬프트에 포함된다.

    Mock: Gemini generate_content 정상 응답.
    검증: 15,000자 초과 콘텐츠가 잘려서 프롬프트에 전달됨.
    """
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        _BASIC_SUMMARY_RESPONSE
    )
    mock_get_client.return_value = mock_client

    long_content = "A" * 20_000
    result = await generate_basic_summary(_SAMPLE_TITLE, long_content)

    assert result == _BASIC_SUMMARY_RESPONSE
    call_args = mock_client.models.generate_content.call_args
    prompt = call_args.kwargs["contents"]
    # Content in prompt should be truncated
    assert "..." in prompt
    assert len(prompt) < 20_000
