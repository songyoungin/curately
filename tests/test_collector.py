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
    """Create a dict mimicking a feedparser entry."""
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
    """Create a Supabase client mock.

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
    """Verify valid struct_time is converted to UTC datetime."""
    st = time.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
    entry = {"published_parsed": st}
    result = _parse_published_date(entry)
    assert result is not None
    assert result.tzinfo == UTC
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_parse_published_date_none() -> None:
    """Verify None is returned when published_parsed is missing."""
    assert _parse_published_date({}) is None


def test_parse_published_date_invalid() -> None:
    """Verify None is returned for invalid values."""
    entry = {"published_parsed": "not-a-struct-time"}
    assert _parse_published_date(entry) is None


# --- _entries_to_articles ---


def test_entries_to_articles_maps_fields() -> None:
    """Verify feedparser entry fields are correctly mapped to article dicts."""
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
    """Verify entries without a link are skipped."""
    entries = [{"title": "No Link"}]
    assert _entries_to_articles(entries, "Feed") == []


def test_entries_to_articles_skips_missing_title() -> None:
    """Verify entries without a title are skipped."""
    entries = [{"link": "https://example.com/x"}]
    assert _entries_to_articles(entries, "Feed") == []


def test_entries_to_articles_uses_description_fallback() -> None:
    """Verify description is used as fallback when summary is absent."""
    entry = _make_entry(summary=None)
    entry.pop("summary", None)
    entry["description"] = "fallback content"
    result = _entries_to_articles([entry], "Feed")
    assert result[0]["raw_content"] == "fallback content"


# --- _deduplicate ---


def test_deduplicate_removes_existing() -> None:
    """Verify articles with URLs already in the database are removed."""
    client = _make_supabase_mock(existing_urls=["https://example.com/1"])
    articles = [
        {"source_url": "https://example.com/1", "title": "Old"},
        {"source_url": "https://example.com/2", "title": "New"},
    ]
    result = _deduplicate(client, articles)
    assert len(result) == 1
    assert result[0]["source_url"] == "https://example.com/2"


def test_deduplicate_keeps_all_when_none_exist() -> None:
    """Verify all articles are kept when none exist in the database."""
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
    """Verify full collection flow: fetch feeds -> HTTP fetch -> parse -> deduplicate."""
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
    """Verify empty list is returned when no active feeds exist."""
    client = _make_supabase_mock(feeds=[])
    result = await collect_articles(client)
    assert result == []


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_handles_timeout(
    mock_async_client_cls: MagicMock,
) -> None:
    """Verify timed-out feeds are skipped while remaining feeds are processed."""
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
    """Verify feeds with HTTP errors are skipped while remaining are processed."""
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
    """Verify articles with URLs already in the database are excluded from results."""
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


EMPTY_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
  </channel>
</rss>"""


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_empty_feed(
    mock_async_client_cls: MagicMock,
) -> None:
    """Verify empty list is returned when a feed has no entries.

    Mock: httpx response succeeds, RSS has no items.
    Expects: Empty list returned, last_fetched_at updated.
    """
    feeds = [_make_feed(1, "Empty Feed", "https://empty.com/rss")]
    client = _make_supabase_mock(feeds=feeds, existing_urls=[])

    mock_response = MagicMock()
    mock_response.text = EMPTY_RSS_XML
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_async_client_cls.return_value = mock_http

    result = await collect_articles(client)
    assert result == []


@pytest.mark.asyncio
@patch("backend.services.collector.httpx.AsyncClient")
async def test_collect_articles_network_error(
    mock_async_client_cls: MagicMock,
) -> None:
    """Verify ConnectError feed is skipped and remaining feeds are processed.

    Mock: First feed raises ConnectError, second feed responds normally.
    Expects: Failed feed skipped, remaining articles collected.
    """
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
            raise httpx.ConnectError("Connection refused")
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
async def test_collect_articles_malformed_rss(
    mock_async_client_cls: MagicMock,
) -> None:
    """Verify invalid RSS responses (e.g., HTML) are treated as empty entries.

    Mock: httpx response succeeds, body is HTML (not RSS).
    Expects: Empty list returned.
    """
    feeds = [_make_feed(1, "Malformed Feed", "https://malformed.com/rss")]
    client = _make_supabase_mock(feeds=feeds, existing_urls=[])

    mock_response = MagicMock()
    mock_response.text = "<html><body>Not a feed</body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_async_client_cls.return_value = mock_http

    result = await collect_articles(client)
    assert result == []
