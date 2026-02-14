"""RSS feed collector service.

Fetches articles from active RSS feeds, parses them with feedparser,
and deduplicates against existing articles in the database.
"""

import logging
from calendar import timegm
from datetime import UTC, datetime

import feedparser
import httpx
from supabase import Client

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10.0


async def collect_articles(client: Client) -> list[dict]:
    """모든 활성 피드에서 새 기사를 수집한다.

    Args:
        client: Supabase client instance.

    Returns:
        DB에 아직 존재하지 않는 새 기사 딕셔너리 목록.
    """
    feeds = _get_active_feeds(client)
    if not feeds:
        logger.info("No active feeds found")
        return []

    logger.info("Fetching %d active feed(s)", len(feeds))
    raw_articles: list[dict] = []

    async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as http_client:
        for feed in feeds:
            feed_name = feed["name"]
            feed_url = feed["url"]
            try:
                entries = await _fetch_and_parse_feed(http_client, feed_url)
                articles = _entries_to_articles(entries, feed_name)
                raw_articles.extend(articles)
                _update_last_fetched(client, feed["id"])
            except httpx.TimeoutException:
                logger.warning("Timeout fetching feed '%s' (%s)", feed_name, feed_url)
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HTTP %d from feed '%s' (%s)",
                    exc.response.status_code,
                    feed_name,
                    feed_url,
                )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Network error fetching feed '%s' (%s): %s",
                    feed_name,
                    feed_url,
                    exc,
                )

    if not raw_articles:
        logger.info("No articles fetched from any feed")
        return []

    new_articles = _deduplicate(client, raw_articles)
    logger.info(
        "Collected %d new article(s) out of %d total",
        len(new_articles),
        len(raw_articles),
    )
    return new_articles


def _get_active_feeds(client: Client) -> list[dict]:
    """활성 상태인 피드 목록을 조회한다."""
    response = (
        client.table("feeds").select("id, name, url").eq("is_active", True).execute()
    )
    return response.data


async def _fetch_and_parse_feed(
    http_client: httpx.AsyncClient, url: str
) -> list[feedparser.FeedParserDict]:
    """단일 피드를 가져와 파싱한다.

    Args:
        http_client: httpx async client.
        url: RSS feed URL.

    Returns:
        파싱된 feedparser 엔트리 목록.
    """
    resp = await http_client.get(url)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.text)
    return parsed.entries


def _parse_published_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """feedparser 엔트리에서 발행일을 추출한다."""
    published_parsed = entry.get("published_parsed")
    if published_parsed is None:
        return None
    try:
        timestamp = timegm(published_parsed)
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except ValueError, OverflowError, OSError, TypeError, AttributeError:
        return None


def _entries_to_articles(
    entries: list[feedparser.FeedParserDict], feed_name: str
) -> list[dict]:
    """feedparser 엔트리 목록을 기사 딕셔너리 목록으로 변환한다."""
    articles: list[dict] = []
    for entry in entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue

        articles.append(
            {
                "source_feed": feed_name,
                "source_url": link,
                "title": title,
                "author": entry.get("author"),
                "published_at": _parse_published_date(entry),
                "raw_content": entry.get("summary") or entry.get("description"),
            }
        )
    return articles


def _deduplicate(client: Client, articles: list[dict]) -> list[dict]:
    """DB에 이미 존재하는 기사를 제외한다."""
    urls = [a["source_url"] for a in articles]
    response = (
        client.table("articles").select("source_url").in_("source_url", urls).execute()
    )
    existing_urls = {row["source_url"] for row in response.data}
    return [a for a in articles if a["source_url"] not in existing_urls]


def _update_last_fetched(client: Client, feed_id: int) -> None:
    """피드의 마지막 수집 시각을 갱신한다."""
    now = datetime.now(tz=UTC).isoformat()
    client.table("feeds").update({"last_fetched_at": now}).eq("id", feed_id).execute()
