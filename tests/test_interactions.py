"""Interaction toggle endpoint tests (like and bookmark)."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE_ARTICLE = {
    "id": 1,
    "source_feed": "TechCrunch",
    "source_url": "https://example.com/article-1",
    "title": "Test Article",
    "author": "Author A",
    "published_at": "2026-02-16T10:00:00+00:00",
    "raw_content": "<p>Full content here</p>",
    "summary": "A test summary",
    "detailed_summary": None,
    "relevance_score": 0.85,
    "categories": ["tech"],
    "keywords": ["ai", "ml"],
    "newsletter_date": "2026-02-16",
    "created_at": "2026-02-16T06:00:00+00:00",
    "updated_at": "2026-02-16T06:00:00+00:00",
}


def _make_mock_client(
    *,
    article: dict[str, object] | None = None,
    user: dict[str, object] | None = None,
    existing_interaction: dict[str, object] | None = None,
    insert_row: dict[str, object] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for interaction toggle tests.

    Args:
        article: Article row returned by articles.select(*).eq(id).execute().
        user: User row for default user lookup.
        existing_interaction: Existing interaction row (None = no prior interaction).
        insert_row: Row returned after INSERT into interactions.
    """
    mock_articles_table = MagicMock()
    mock_users_table = MagicMock()
    mock_interactions_table = MagicMock()

    # articles.select(*).eq(id).execute()
    article_data = [article] if article is not None else []
    mock_articles_table.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=article_data)
    )

    # users.select(id).eq(email).execute()
    user_data = [user] if user is not None else []
    mock_users_table.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=user_data)
    )

    # interactions.select(id).eq(user_id).eq(article_id).eq(type).execute()
    interaction_data = [existing_interaction] if existing_interaction else []
    mock_interactions_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=interaction_data
    )

    # interactions.delete().eq(id).execute()
    mock_interactions_table.delete.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )

    # interactions.insert().execute()
    insert_data = (
        [insert_row] if insert_row else [{"created_at": "2026-02-16T12:00:00+00:00"}]
    )
    mock_interactions_table.insert.return_value.execute.return_value = MagicMock(
        data=insert_data
    )

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "articles":
            return mock_articles_table
        if name == "users":
            return mock_users_table
        if name == "interactions":
            return mock_interactions_table
        return MagicMock()

    mock_client.table.side_effect = route_table
    return mock_client


# --- POST /api/articles/{article_id}/like ---


@patch("backend.routers.articles.get_settings")
@patch("backend.routers.articles.get_supabase_client")
def test_like_creates_interaction(
    mock_get_client: MagicMock, mock_get_settings: MagicMock
) -> None:
    """Verify first like creates interaction and returns active=true.

    Mock: article exists, user exists, no prior like interaction.
    Expects: 200 status, active=true, update_interests_on_like called.
    """
    mock_get_client.return_value = _make_mock_client(
        article=SAMPLE_ARTICLE,
        user={"id": 1},
        existing_interaction=None,
    )
    mock_get_settings.return_value = MagicMock()

    with patch(
        "backend.services.interests.update_interests_on_like",
        new_callable=AsyncMock,
    ) as mock_update:
        response = client.post("/api/articles/1/like")

    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == 1
    assert data["type"] == "like"
    assert data["active"] is True
    mock_update.assert_called_once()


@patch("backend.routers.articles.get_settings")
@patch("backend.routers.articles.get_supabase_client")
def test_like_removes_interaction(
    mock_get_client: MagicMock, mock_get_settings: MagicMock
) -> None:
    """Verify second like removes interaction and returns active=false.

    Mock: article exists, user exists, prior like interaction exists.
    Expects: 200 status, active=false, remove_interests_on_unlike called.
    """
    mock_get_client.return_value = _make_mock_client(
        article=SAMPLE_ARTICLE,
        user={"id": 1},
        existing_interaction={"id": 42},
    )
    mock_get_settings.return_value = MagicMock()

    with patch(
        "backend.services.interests.remove_interests_on_unlike",
        new_callable=AsyncMock,
    ) as mock_remove:
        response = client.post("/api/articles/1/like")

    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == 1
    assert data["type"] == "like"
    assert data["active"] is False
    mock_remove.assert_called_once()


@patch("backend.routers.articles.get_supabase_client")
def test_like_article_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 when article does not exist.

    Mock: articles table returns empty for the requested ID.
    Expects: 404 status.
    """
    mock_get_client.return_value = _make_mock_client(article=None)

    response = client.post("/api/articles/999/like")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


# --- POST /api/articles/{article_id}/bookmark ---


@patch("backend.routers.articles.get_supabase_client")
def test_bookmark_creates_interaction(mock_get_client: MagicMock) -> None:
    """Verify first bookmark creates interaction and returns active=true.

    Mock: article exists, user exists, no prior bookmark.
    Expects: 200 status, active=true, background task scheduled.
    """
    mock_get_client.return_value = _make_mock_client(
        article=SAMPLE_ARTICLE,
        user={"id": 1},
        existing_interaction=None,
    )

    with patch(
        "backend.routers.articles._generate_and_store_detailed_summary",
    ):
        response = client.post("/api/articles/1/bookmark")

    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == 1
    assert data["type"] == "bookmark"
    assert data["active"] is True


@patch("backend.routers.articles.get_supabase_client")
def test_bookmark_removes_interaction(mock_get_client: MagicMock) -> None:
    """Verify second bookmark removes interaction and returns active=false.

    Mock: article exists, user exists, prior bookmark exists.
    Expects: 200 status, active=false.
    """
    mock_get_client.return_value = _make_mock_client(
        article=SAMPLE_ARTICLE,
        user={"id": 1},
        existing_interaction={"id": 55},
    )

    response = client.post("/api/articles/1/bookmark")

    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == 1
    assert data["type"] == "bookmark"
    assert data["active"] is False


@patch("backend.routers.articles.get_supabase_client")
def test_bookmark_article_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 when article does not exist.

    Mock: articles table returns empty for the requested ID.
    Expects: 404 status.
    """
    mock_get_client.return_value = _make_mock_client(article=None)

    response = client.post("/api/articles/999/bookmark")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"
