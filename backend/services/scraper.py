"""Scraper service for extracting full content and images from articles.

Uses the Jina Reader API (https://r.jina.ai/) to convert articles to Markdown
and extracts key image URLs for multimodal summaries.
"""

from __future__ import annotations

import logging
import re
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)

_JINA_READER_BASE_URL = "https://r.jina.ai/"
_FETCH_TIMEOUT = 10.0


class ScrapedContent(TypedDict):
    """Result of scraping an article."""

    markdown_text: str
    image_urls: list[str]


def _extract_image_urls(markdown: str) -> list[str]:
    """Extract image URLs from Markdown text using regex.

    Looks for the pattern: ![alt text](image_url)
    """
    # Simple regex to find markdown images
    pattern = r"!\[.*?\]\((.*?)\)"
    urls = re.findall(pattern, markdown)
    return urls


async def scrape_article(url: str) -> ScrapedContent:
    """Scrapes the URL and returns full markdown content and a list of image URLs.

    Args:
        url: The original article URL.

    Returns:
        ScrapedContent dict containing the markdown text and a list of image URLs.
        Returns empty strings/lists if scraping fails.
    """
    jina_url = f"{_JINA_READER_BASE_URL}{url}"

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            response = await client.get(jina_url)
            response.raise_for_status()
            markdown_text = response.text

            image_urls = _extract_image_urls(markdown_text)

            return ScrapedContent(
                markdown_text=markdown_text,
                image_urls=image_urls,
            )
    except httpx.RequestError as exc:
        logger.warning("Network error scraping article %s: %s", url, exc)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %d error scraping article %s",
            exc.response.status_code,
            url,
        )
    except Exception as exc:
        logger.exception("Unexpected error scraping article %s: %s", url, exc)

    return ScrapedContent(markdown_text="", image_urls=[])


async def download_images(urls: list[str], max_images: int = 3) -> list[bytes]:
    """Downloads up to `max_images` from the provided URLs.

    Args:
        urls: List of image URLs to download.
        max_images: Maximum number of images to download.

    Returns:
        List of image byte contents. Failed downloads are skipped.
    """
    images: list[bytes] = []

    # Take only the first max_images URLs
    urls_to_fetch = urls[:max_images]

    if not urls_to_fetch:
        return images

    async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
        for url in urls_to_fetch:
            try:
                response = await client.get(url)
                response.raise_for_status()
                images.append(response.content)
            except httpx.RequestError as exc:
                logger.warning("Network error downloading image %s: %s", url, exc)
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HTTP %d error downloading image %s",
                    exc.response.status_code,
                    url,
                )
            except Exception as exc:
                logger.warning("Unexpected error downloading image %s: %s", url, exc)

    return images
