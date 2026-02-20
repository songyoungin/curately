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

_BASIC_SUMMARY_RESPONSE = (  # noqa: korean-ok
    "OpenAI가 멀티모달 기능을 갖춘 GPT-5를 출시했습니다. "  # noqa: korean-ok
    "이번 모델은 텍스트, 이미지, 오디오를 동시에 처리할 수 있어 "  # noqa: korean-ok
    "기술 전문가들에게 큰 영향을 미칠 것으로 보입니다."  # noqa: korean-ok
)

_DETAILED_SUMMARY_RESPONSE = json.dumps(
    {
        "background": "OpenAI가 GPT-5를 출시하며 AI 업계에 큰 변화를 예고했습니다.",  # noqa: korean-ok
        "takeaways": [
            "멀티모달 처리 능력이 대폭 향상되었습니다.",  # noqa: korean-ok
            "추론 성능이 이전 모델 대비 크게 개선되었습니다.",  # noqa: korean-ok
            "API 가격이 인하되어 접근성이 높아졌습니다.",  # noqa: korean-ok
        ],
        "keywords": ["GPT-5", "multimodal", "LLM", "OpenAI"],
    },
    ensure_ascii=False,
)


def _make_gemini_response(text: str) -> MagicMock:
    """Create a MagicMock mimicking a Gemini API response object."""
    response = MagicMock()
    response.text = text
    return response


def _make_settings_mock() -> MagicMock:
    """Create a Settings mock with gemini.model and gemini_api_key."""
    settings = MagicMock()
    settings.gemini.model = "gemini-2.5-flash"
    settings.gemini_api_key = "test-api-key"
    return settings


# --- _truncate_content ---


def test_truncate_content_short() -> None:
    """Verify short content is returned unchanged."""
    assert _truncate_content("short text") == "short text"


def test_truncate_content_none() -> None:
    """Verify None input returns an empty string."""
    assert _truncate_content(None) == ""


def test_truncate_content_empty() -> None:
    """Verify empty string is returned unchanged."""
    assert _truncate_content("") == ""


def test_truncate_content_long() -> None:
    """Verify content exceeding max length is truncated with '...' appended."""
    long_text = "x" * 20_000
    result = _truncate_content(long_text)
    assert len(result) == 15_003  # 15000 + "..."
    assert result.endswith("...")


# --- _parse_detailed_summary ---


def test_parse_detailed_summary_valid_json() -> None:
    """Verify valid JSON response is correctly parsed into DetailedSummary."""
    result = _parse_detailed_summary(_DETAILED_SUMMARY_RESPONSE)
    assert (
        result["background"]
        == "OpenAI가 GPT-5를 출시하며 AI 업계에 큰 변화를 예고했습니다."  # noqa: korean-ok
    )
    assert len(result["takeaways"]) == 3
    assert len(result["keywords"]) == 4
    assert "GPT-5" in result["keywords"]


def test_parse_detailed_summary_malformed_json() -> None:
    """Verify malformed JSON falls back gracefully.

    Expects: background contains raw text, takeaways/keywords are empty lists.
    """
    result = _parse_detailed_summary("This is not valid JSON at all")
    assert result["background"] == "This is not valid JSON at all"
    assert result["takeaways"] == []
    assert result["keywords"] == []


def test_parse_detailed_summary_missing_fields() -> None:
    """Verify JSON with missing fields uses default values.

    Expects: Missing fields are replaced with empty string/list.
    """
    partial = json.dumps({"background": "Some background"})
    result = _parse_detailed_summary(partial)
    assert result["background"] == "Some background"
    assert result["takeaways"] == []
    assert result["keywords"] == []


def test_parse_detailed_summary_wrong_types() -> None:
    """Verify JSON with wrong field types is handled safely.

    Expects: Wrong types are converted to str or replaced with empty list.
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
    """Verify fallback returns raw text as background."""
    result = _fallback_detailed_summary("  some raw text  ")
    assert result["background"] == "some raw text"
    assert result["takeaways"] == []
    assert result["keywords"] == []


def test_fallback_detailed_summary_empty() -> None:
    """Verify fallback with empty text returns empty background."""
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
    """Verify Korean summary text is returned on successful Gemini response.

    Mock: Gemini generate_content returns Korean summary text.
    Expects: Returned summary matches the stripped response text.
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
    """Verify summary is generated normally even with None content.

    Mock: Gemini generate_content returns Korean summary text.
    Expects: Prompt uses '(no content)' placeholder, call succeeds.
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
    """Verify result is returned after successful retry on API error.

    Mock: First call raises RuntimeError, second call succeeds.
    Expects: 2 calls, 1 sleep, final result returned.
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
    """Verify last exception is raised when all retries fail.

    Mock: All 3 calls raise RuntimeError.
    Expects: RuntimeError raised, 3 calls, 2 sleeps.
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
    """Verify valid JSON response is parsed into DetailedSummary structure.

    Mock: Gemini generate_content returns JSON string (background, takeaways, keywords).
    Expects: Return value is a DetailedSummary dict with correct fields.
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
    """Verify fallback handling when Gemini returns invalid JSON.

    Mock: Gemini generate_content returns non-JSON text.
    Expects: background contains raw text, takeaways/keywords are empty lists.
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
    """Verify retry works for detailed summary generation on API error.

    Mock: First call raises RuntimeError, second returns valid JSON.
    Expects: 2 calls, normal result returned after retry.
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
    """Verify API key is never exposed in log messages during error logging.

    Mock: Gemini API call fails 3 times (RuntimeError).
    Expects: No log message contains the API key string.
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
    """Verify very long content is truncated before being sent in the prompt.

    Mock: Gemini generate_content responds normally.
    Expects: Content exceeding 15,000 chars is truncated in the prompt.
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


# --- Multimodal content ---


@pytest.mark.asyncio
@patch("backend.services.summarizer.get_settings")
@patch("backend.services.summarizer._get_client")
async def test_generate_basic_summary_with_images(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """Verify that images are passed correctly to Gemini."""
    mock_get_settings.return_value = _make_settings_mock()
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        _BASIC_SUMMARY_RESPONSE
    )
    mock_get_client.return_value = mock_client

    images = [b"image1", b"image2"]
    result = await generate_basic_summary(_SAMPLE_TITLE, _SAMPLE_CONTENT, images)

    assert result == _BASIC_SUMMARY_RESPONSE
    call_args = mock_client.models.generate_content.call_args
    contents = call_args.kwargs["contents"]

    assert isinstance(contents, list)
    assert len(contents) == 3  # 1 text + 2 images
    assert isinstance(contents[0], str)
    assert _SAMPLE_TITLE in contents[0]

    # We should have created Parts
    assert contents[1].__class__.__name__ == "Part"
    assert contents[2].__class__.__name__ == "Part"
