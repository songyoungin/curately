"""Article detail router tests."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE_ARTICLE_DETAIL = {
    "id": 1,
    "source_feed": "TechCrunch",
    "source_url": "https://example.com/article-1",
    "title": "Test Article",
    "author": "Author A",
    "published_at": "2026-02-16T10:00:00+00:00",
    "raw_content": "<p>Full content here</p>",
    "summary": "A test summary",
    "detailed_summary": "Detailed summary with background and takeaways.",
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
    interactions: list[dict[str, object]] | None = None,
) -> MagicMock:
    """Build a mock Supabase client routing table() calls by table name.

    Args:
        article: Article row or None for not-found.
        user: User row for default user lookup.
        interactions: Interaction rows for the article.
    """
    mock_articles_table = MagicMock()
    mock_users_table = MagicMock()
    mock_interactions_table = MagicMock()

    # articles table: select(*).eq(id).execute()
    article_data = [article] if article is not None else []
    mock_articles_table.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=article_data)
    )

    # users table: select(id).eq(email).execute()
    user_data = [user] if user is not None else []
    mock_users_table.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=user_data)
    )

    # interactions table: select(type).eq(user_id).eq(article_id).execute()
    interaction_data = interactions if interactions is not None else []
    mock_interactions_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=interaction_data
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


# --- GET /api/articles/{article_id} ---


@patch("backend.routers.articles.get_supabase_client")
def test_get_article_success(mock_get_client: MagicMock) -> None:
    """Verify article detail is returned with interaction flags.

    Mock: article exists, default user exists, no interactions.
    Expects: 200 status, full article detail, flags default to false.
    """
    mock_get_client.return_value = _make_mock_client(
        article=SAMPLE_ARTICLE_DETAIL,
        user={"id": 1},
        interactions=[],
    )

    response = client.get("/api/articles/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Test Article"
    assert data["raw_content"] == "<p>Full content here</p>"
    assert data["detailed_summary"] == "Detailed summary with background and takeaways."
    assert data["is_liked"] is False
    assert data["is_bookmarked"] is False


@patch("backend.routers.articles.get_supabase_client")
def test_get_article_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 when article does not exist.

    Mock: articles table returns empty for the requested ID.
    Expects: 404 status.
    """
    mock_get_client.return_value = _make_mock_client(article=None)

    response = client.get("/api/articles/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


@patch("backend.routers.articles.get_supabase_client")
def test_get_article_with_interactions(mock_get_client: MagicMock) -> None:
    """Verify interaction flags reflect user's like and bookmark.

    Mock: article exists, user has both like and bookmark interactions.
    Expects: 200 status, is_liked=True, is_bookmarked=True.
    """
    mock_get_client.return_value = _make_mock_client(
        article=SAMPLE_ARTICLE_DETAIL,
        user={"id": 1},
        interactions=[{"type": "like"}, {"type": "bookmark"}],
    )

    response = client.get("/api/articles/1")

    assert response.status_code == 200
    data = response.json()
    assert data["is_liked"] is True
    assert data["is_bookmarked"] is True
