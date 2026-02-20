import httpx
import pytest
from unittest.mock import AsyncMock, Mock, patch

from backend.services.scraper import download_images, scrape_article


@pytest.fixture
def mock_httpx_client():
    with patch("backend.services.scraper.httpx.AsyncClient") as mock:
        yield mock


@pytest.mark.asyncio
async def test_scrape_article_success(mock_httpx_client):
    # Mocking httpx.AsyncClient().get
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    # Jina returns markdown in text
    mock_response.text = "Title\n\n![img1](http://example.com/1.png)\nSome text\n![img2](http://example.com/2.jpg)"
    mock_client_instance.get.return_value = mock_response

    result = await scrape_article("http://example.com/article")

    assert (
        result["markdown_text"]
        == "Title\n\n![img1](http://example.com/1.png)\nSome text\n![img2](http://example.com/2.jpg)"
    )
    assert result["image_urls"] == [
        "http://example.com/1.png",
        "http://example.com/2.jpg",
    ]
    mock_client_instance.get.assert_called_once_with(
        "https://r.jina.ai/http://example.com/article"
    )


@pytest.mark.asyncio
async def test_scrape_article_network_error(mock_httpx_client):
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
    mock_client_instance.get.side_effect = httpx.RequestError("Network Error")

    result = await scrape_article("http://example.com/article")

    assert result["markdown_text"] == ""
    assert result["image_urls"] == []


@pytest.mark.asyncio
async def test_download_images_success(mock_httpx_client):
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    mock_response1 = Mock()
    mock_response1.raise_for_status = Mock()
    mock_response1.content = b"image1"

    mock_response2 = Mock()
    mock_response2.raise_for_status = Mock()
    mock_response2.content = b"image2"

    mock_client_instance.get.side_effect = [mock_response1, mock_response2]

    images = await download_images(["url1", "url2"], max_images=2)
    assert len(images) == 2
    assert images[0] == b"image1"
    assert images[1] == b"image2"


@pytest.mark.asyncio
async def test_download_images_max_limit(mock_httpx_client):
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.content = b"image"
    mock_client_instance.get.return_value = mock_response

    images = await download_images(["url1", "url2", "url3", "url4"], max_images=2)
    assert len(images) == 2


@pytest.mark.asyncio
async def test_download_images_handles_errors(mock_httpx_client):
    mock_client_instance = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    mock_response1 = Mock()
    mock_response1.raise_for_status = Mock()
    mock_response1.content = b"image1"

    # Second request fails
    mock_client_instance.get.side_effect = [mock_response1, httpx.RequestError("Error")]

    images = await download_images(["url1", "url2"], max_images=2)
    assert len(images) == 1
    assert images[0] == b"image1"
