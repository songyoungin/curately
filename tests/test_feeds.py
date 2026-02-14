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
    """피드 목록 조회 시 모든 피드를 반환한다.

    Mock: Supabase feeds.select().order().execute() → 피드 1건.
    검증: 200 상태코드, 피드 목록 반환.
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
    """등록된 피드가 없으면 빈 리스트를 반환한다.

    Mock: Supabase feeds.select().order().execute() → 빈 리스트.
    검증: 200 상태코드, 빈 리스트.
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
    """유효한 피드 생성 시 201과 생성된 피드를 반환한다.

    Mock: _validate_feed_url (통과), Supabase duplicate check (없음), insert.
    검증: 201 상태코드, 피드 데이터, validate 호출.
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
    """잘못된 URL 형식으로 피드 생성 시 400을 반환한다.

    Mock: 없음 (URL 형식 검증은 urlparse 기반 순수 로직).
    검증: 400 상태코드.
    """
    response = client.post("/api/feeds", json={"name": "Bad", "url": "not-a-url"})
    assert response.status_code == 400


def test_create_feed_invalid_url_ftp_scheme() -> None:
    """http/https가 아닌 scheme의 URL은 400을 반환한다.

    Mock: 없음 (URL 형식 검증은 urlparse 기반 순수 로직).
    검증: 400 상태코드.
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
    """이미 존재하는 URL로 피드 생성 시 409를 반환한다.

    Mock: _validate_feed_url (통과), Supabase duplicate check (존재).
    검증: 409 상태코드.
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
    """파싱할 수 없는 RSS URL로 피드 생성 시 422를 반환한다.

    Mock: _validate_feed_url (422 HTTPException 발생).
    검증: 422 상태코드.
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
    """접속 불가능한 URL로 피드 생성 시 422를 반환한다.

    Mock: _validate_feed_url (422 HTTPException 발생 - fetch 실패).
    검증: 422 상태코드.
    """
    response = client.post(
        "/api/feeds",
        json={"name": "Down", "url": "https://unreachable.example.com/rss"},
    )
    assert response.status_code == 422


# --- DELETE /api/feeds/{feed_id} ---


@patch("backend.routers.feeds.get_supabase_client")
def test_delete_feed_success(mock_get_client: MagicMock) -> None:
    """존재하는 피드 삭제 시 204를 반환한다.

    Mock: Supabase select (존재), delete.
    검증: 204 상태코드.
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
    """존재하지 않는 피드 삭제 시 404를 반환한다.

    Mock: Supabase select (없음).
    검증: 404 상태코드.
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
    """피드 활성 상태를 비활성으로 변경 시 업데이트된 피드를 반환한다.

    Mock: Supabase select (존재), update.
    검증: 200 상태코드, is_active=False.
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
    """존재하지 않는 피드 수정 시 404를 반환한다.

    Mock: Supabase select (없음).
    검증: 404 상태코드.
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
