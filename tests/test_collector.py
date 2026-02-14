"""RSS collector service tests."""

import time
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services.collector import (
    _deduplicate,
    _entries_to_articles,
    _parse_published_date,
    collect_articles,
)

# --- Fixtures ---


def _make_feed(
    feed_id: int = 1, name: str = "Test Feed", url: str = "https://example.com/rss"
) -> dict:
    return {"id": feed_id, "name": name, "url": url}


def _make_entry(
    title: str = "Test Article",
    link: str = "https://example.com/article-1",
    author: str = "Author",
    summary: str | None = "Article content",
    published_parsed: time.struct_time | None = None,
) -> dict:
    """feedparser entry를 모사하는 딕셔너리를 생성한다."""
    entry: dict = {
        "title": title,
        "link": link,
        "author": author,
        "summary": summary,
    }
    if published_parsed is not None:
        entry["published_parsed"] = published_parsed
    return entry


def _make_supabase_mock(
    feeds: list[dict] | None = None,
    existing_urls: list[str] | None = None,
) -> MagicMock:
    """Supabase client mock을 생성한다.

    Mocks:
        - feeds.select().eq().execute() -> feeds
        - articles.select().in_().execute() -> existing URLs
        - feeds.update().eq().execute() -> None
    """
    mock_client = MagicMock()

    feeds_data = feeds if feeds is not None else []
    existing_data = [{"source_url": u} for u in (existing_urls or [])]

    # feeds.select().eq().execute()
    feeds_chain = MagicMock()
    feeds_chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=feeds_data
    )
    # feeds.update().eq().execute()
    feeds_chain.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # articles.select().in_().execute()
    articles_chain = MagicMock()
    articles_chain.select.return_value.in_.return_value.execute.return_value = (
        MagicMock(data=existing_data)
    )

    def table_router(name: str) -> MagicMock:
        if name == "feeds":
            return feeds_chain
        if name == "articles":
            return articles_chain
        return MagicMock()

    mock_client.table.side_effect = table_router
    return mock_client


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article One</title>
      <link>https://example.com/1</link>
      <author>Author A</author>
      <description>Content one</description>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Article Two</title>
      <link>https://example.com/2</link>
      <description>Content two</description>
    </item>
  </channel>
</rss>"""


# --- _parse_published_date ---


def test_parse_published_date_valid() -> None:
    """유효한 struct_time이 UTC datetime으로 변환된다."""
    st = time.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
    entry = {"published_parsed": st}
    result = _parse_published_date(entry)
    assert result is not None
    assert result.tzinfo == UTC
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_parse_published_date_none() -> None:
    """published_parsed가 없으면 None을 반환한다."""
    assert _parse_published_date({}) is None


def test_parse_published_date_invalid() -> None:
    """잘못된 값이면 None을 반환한다."""
    entry = {"published_parsed": "not-a-struct-time"}
    assert _parse_published_date(entry) is None


# --- _entries_to_articles ---


def test_entries_to_articles_maps_fields() -> None:
    """feedparser 엔트리 필드가 기사 딕셔너리로 올바르게 매핑된다."""
    entries = [_make_entry()]
    result = _entries_to_articles(entries, "My Feed")

    assert len(result) == 1
    article = result[0]
    assert article["source_feed"] == "My Feed"
    assert article["source_url"] == "https://example.com/article-1"
    assert article["title"] == "Test Article"
    assert article["author"] == "Author"
    assert article["raw_content"] == "Article content"


def test_entries_to_articles_skips_missing_link() -> None:
    """link가 없는 엔트리는 건너뛴다."""
    entries = [{"title": "No Link"}]
    assert _entries_to_articles(entries, "Feed") == []


def test_entries_to_articles_skips_missing_title() -> None:
    """title이 없는 엔트리는 건너뛴다."""
    entries = [{"link": "https://example.com/x"}]
    assert _entries_to_articles(entries, "Feed") == []


def test_entries_to_articles_uses_description_fallback() -> None:
    """summary가 없으면 description을 사용한다."""
    entry = _make_entry(summary=None)
    entry.pop("summary", None)
    entry["description"] = "fallback content"
    result = _entries_to_articles([entry], "Feed")
    assert result[0]["raw_content"] == "fallback content"


# --- _deduplicate ---


def test_deduplicate_removes_existing() -> None:
    """DB에 이미 존재하는 URL의 기사가 제거된다."""
    client = _make_supabase_mock(existing_urls=["https://example.com/1"])
    articles = [
        {"source_url": "https://example.com/1", "title": "Old"},
        {"source_url": "https://example.com/2", "title": "New"},
    ]
    result = _deduplicate(client, articles)
    assert len(result) == 1
    assert result[0]["source_url"] == "https://example.com/2"


def test_deduplicate_keeps_all_when_none_exist() -> None:
    """DB에 없는 기사는 모두 유지된다."""
    client = _make_supabase_mock(existing_urls=[])
    articles = [
        {"source_url": "https://example.com/1", "title": "A"},
        {"source_url": "https://example.com/2", "title": "B"},
    ]
    result = _deduplicate(client, articles)
    assert len(result) == 2


# --- collect_articles ---


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_full_flow(mock_async_client_cls: MagicMock) -> None:
    """전체 수집 흐름: 피드 조회 -> HTTP fetch -> 파싱 -> 중복 제거."""
    feeds = [_make_feed(1, "Feed A", "https://feed-a.com/rss")]
    client = _make_supabase_mock(feeds=feeds, existing_urls=[])

    mock_response = MagicMock()
    mock_response.text = RSS_XML
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_async_client_cls.return_value = mock_http

    result = await collect_articles(client)

    assert len(result) == 2
    assert result[0]["title"] == "Article One"
    assert result[0]["source_feed"] == "Feed A"
    assert result[1]["title"] == "Article Two"


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_no_active_feeds(
    mock_async_client_cls: MagicMock,
) -> None:
    """활성 피드가 없으면 빈 리스트를 반환한다."""
    client = _make_supabase_mock(feeds=[])
    result = await collect_articles(client)
    assert result == []


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_handles_timeout(
    mock_async_client_cls: MagicMock,
) -> None:
    """타임아웃 피드는 건너뛰고 나머지를 계속 처리한다."""
    feeds = [
        _make_feed(1, "Bad Feed", "https://bad.com/rss"),
        _make_feed(2, "Good Feed", "https://good.com/rss"),
    ]
    client = _make_supabase_mock(feeds=feeds, existing_urls=[])

    mock_good_response = MagicMock()
    mock_good_response.text = RSS_XML
    mock_good_response.raise_for_status = MagicMock()

    async def side_effect(url: str, **kwargs: object) -> MagicMock:
        if "bad.com" in url:
            raise httpx.ReadTimeout("timeout")
        return mock_good_response

    mock_http = AsyncMock()
    mock_http.get.side_effect = side_effect
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_async_client_cls.return_value = mock_http

    result = await collect_articles(client)

    assert len(result) == 2
    assert all(a["source_feed"] == "Good Feed" for a in result)


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_handles_http_error(
    mock_async_client_cls: MagicMock,
) -> None:
    """HTTP 에러 피드는 건너뛰고 나머지를 계속 처리한다."""
    feeds = [_make_feed(1, "Error Feed", "https://error.com/rss")]
    client = _make_supabase_mock(feeds=feeds, existing_urls=[])

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_async_client_cls.return_value = mock_http

    result = await collect_articles(client)
    assert result == []


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_deduplicates(
    mock_async_client_cls: MagicMock,
) -> None:
    """DB에 이미 존재하는 기사 URL은 결과에서 제외된다."""
    feeds = [_make_feed(1, "Feed", "https://feed.com/rss")]
    client = _make_supabase_mock(feeds=feeds, existing_urls=["https://example.com/1"])

    mock_response = MagicMock()
    mock_response.text = RSS_XML
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_async_client_cls.return_value = mock_http

    result = await collect_articles(client)

    assert len(result) == 1
    assert result[0]["source_url"] == "https://example.com/2"
