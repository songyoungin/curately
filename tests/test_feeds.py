"""Feed CRUD router tests."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE_FEED = {
    "id": 1,
    "name": "Test Feed",
    "url": "https://example.com/rss",
    "is_active": True,
    "last_fetched_at": None,
    "created_at": "2024-01-01T00:00:00+00:00",
}


# --- GET /api/feeds ---


@patch("backend.routers.feeds.get_supabase_client")
def test_list_feeds_returns_all(mock_get_client: MagicMock) -> None:
    """Verify all feeds are returned when listing.

    Mock: Supabase feeds.select().order().execute() returns 1 feed.
    Expects: 200 status, feed list returned.
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_FEED]
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/feeds")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Feed"
    assert data[0]["url"] == "https://example.com/rss"


@patch("backend.routers.feeds.get_supabase_client")
def test_list_feeds_empty(mock_get_client: MagicMock) -> None:
    """Verify empty list is returned when no feeds are registered.

    Mock: Supabase feeds.select().order().execute() returns empty list.
    Expects: 200 status, empty list.
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/feeds")

    assert response.status_code == 200
    assert response.json() == []


# --- POST /api/feeds ---


@patch("backend.routers.feeds.get_supabase_client")
@patch("backend.routers.feeds._validate_feed_url", new_callable=AsyncMock)
def test_create_feed_success(
    mock_validate: AsyncMock, mock_get_client: MagicMock
) -> None:
    """Verify 201 and created feed are returned on valid feed creation.

    Mock: _validate_feed_url passes, Supabase duplicate check (none), insert.
    Expects: 201 status, feed data, validate called.
    """
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[SAMPLE_FEED])
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client

    response = client.post(
        "/api/feeds", json={"name": "Test Feed", "url": "https://example.com/rss"}
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Test Feed"
    mock_validate.assert_awaited_once_with("https://example.com/rss")


def test_create_feed_invalid_url_format() -> None:
    """Verify 400 is returned for invalid URL format.

    Mock: None (URL format validation uses pure urlparse logic).
    Expects: 400 status.
    """
    response = client.post("/api/feeds", json={"name": "Bad", "url": "not-a-url"})
    assert response.status_code == 400


def test_create_feed_invalid_url_ftp_scheme() -> None:
    """Verify 400 is returned for URLs with non-http/https schemes.

    Mock: None (URL format validation uses pure urlparse logic).
    Expects: 400 status.
    """
    response = client.post(
        "/api/feeds", json={"name": "FTP", "url": "ftp://example.com/feed"}
    )
    assert response.status_code == 400


@patch("backend.routers.feeds.get_supabase_client")
@patch("backend.routers.feeds._validate_feed_url", new_callable=AsyncMock)
def test_create_feed_duplicate_url(
    mock_validate: AsyncMock, mock_get_client: MagicMock
) -> None:
    """Verify 409 is returned when creating a feed with an existing URL.

    Mock: _validate_feed_url passes, Supabase duplicate check (exists).
    Expects: 409 status.
    """
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_FEED]
    )
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client

    response = client.post(
        "/api/feeds", json={"name": "Dup", "url": "https://example.com/rss"}
    )
    assert response.status_code == 409


@patch(
    "backend.routers.feeds._validate_feed_url",
    new_callable=AsyncMock,
    side_effect=HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="URL is not a valid RSS feed",
    ),
)
def test_create_feed_unparseable_rss(mock_validate: AsyncMock) -> None:
    """Verify 422 is returned when RSS URL cannot be parsed.

    Mock: _validate_feed_url raises 422 HTTPException.
    Expects: 422 status.
    """
    response = client.post(
        "/api/feeds", json={"name": "Bad RSS", "url": "https://example.com/page"}
    )
    assert response.status_code == 422


@patch(
    "backend.routers.feeds._validate_feed_url",
    new_callable=AsyncMock,
    side_effect=HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Failed to fetch feed URL",
    ),
)
def test_create_feed_unreachable_url(mock_validate: AsyncMock) -> None:
    """Verify 422 is returned when feed URL is unreachable.

    Mock: _validate_feed_url raises 422 HTTPException (fetch failure).
    Expects: 422 status.
    """
    response = client.post(
        "/api/feeds",
        json={"name": "Down", "url": "https://unreachable.example.com/rss"},
    )
    assert response.status_code == 422


# --- DELETE /api/feeds/{feed_id} ---


@patch("backend.routers.feeds.get_supabase_client")
def test_delete_feed_success(mock_get_client: MagicMock) -> None:
    """Verify 204 is returned when deleting an existing feed.

    Mock: Supabase select (exists), delete.
    Expects: 204 status.
    """
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )
    mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client

    response = client.delete("/api/feeds/1")
    assert response.status_code == 204


@patch("backend.routers.feeds.get_supabase_client")
def test_delete_feed_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 is returned when deleting a non-existent feed.

    Mock: Supabase select (empty).
    Expects: 404 status.
    """
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client

    response = client.delete("/api/feeds/999")
    assert response.status_code == 404


# --- PATCH /api/feeds/{feed_id} ---


@patch("backend.routers.feeds.get_supabase_client")
def test_update_feed_toggle_active(mock_get_client: MagicMock) -> None:
    """Verify updated feed is returned when toggling active status to inactive.

    Mock: Supabase select (exists), update.
    Expects: 200 status, is_active=False.
    """
    updated_feed = {**SAMPLE_FEED, "is_active": False}
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[updated_feed]
    )
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client

    response = client.patch("/api/feeds/1", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@patch("backend.routers.feeds.get_supabase_client")
def test_update_feed_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 is returned when updating a non-existent feed.

    Mock: Supabase select (empty).
    Expects: 404 status.
    """
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client

    response = client.patch("/api/feeds/999", json={"is_active": True})
    assert response.status_code == 404
