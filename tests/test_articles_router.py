"""Article detail router tests."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE_ARTICLE = {
    "id": 1,
    "source_feed": "TechCrunch",
    "source_url": "https://techcrunch.com/article-1",
    "title": "AI Advances in 2026",
    "author": "John Doe",
    "published_at": "2026-02-15T08:00:00+00:00",
    "raw_content": "Full article content here.",
    "summary": "AI is making big strides in 2026.",
    "detailed_summary": "Detailed summary with background and takeaways.",
    "relevance_score": 0.85,
    "categories": ["AI", "Technology"],
    "keywords": ["ai", "machine-learning"],
    "newsletter_date": "2026-02-15",
    "created_at": "2026-02-15T06:00:00+00:00",
    "updated_at": "2026-02-15T06:00:00+00:00",
}


def _make_table_side_effect(
    articles_mock: MagicMock,
    users_mock: MagicMock | None = None,
    interactions_mock: MagicMock | None = None,
) -> MagicMock:
    """Build a side_effect function for mock_client.table() calls.

    Routes table() calls to the correct mock based on the table name.

    Args:
        articles_mock: Mock for the articles table.
        users_mock: Mock for the users table (optional).
        interactions_mock: Mock for the interactions table (optional).

    Returns:
        A callable that dispatches based on table name.
    """

    def side_effect(name: str) -> MagicMock:
        if name == "articles":
            return articles_mock
        elif name == "users":
            return users_mock or MagicMock()
        elif name == "interactions":
            return interactions_mock or MagicMock()
        return MagicMock()

    mock = MagicMock(side_effect=side_effect)
    return mock


# --- GET /api/articles/{article_id} ---


@patch("backend.routers.articles.get_supabase_client")
def test_get_article_detail(mock_get_client: MagicMock) -> None:
    """Verify full article detail is returned with all fields.

    Mock: articles table returns one article, user exists, no interactions.
    Expects: 200 status, all fields present including detailed_summary.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_ARTICLE.copy()]
    )

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    interactions_mock = MagicMock()
    interactions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(
        articles_mock, users_mock, interactions_mock
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/articles/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "AI Advances in 2026"
    assert data["source_feed"] == "TechCrunch"
    assert data["source_url"] == "https://techcrunch.com/article-1"
    assert data["author"] == "John Doe"
    assert data["summary"] == "AI is making big strides in 2026."
    assert data["detailed_summary"] == "Detailed summary with background and takeaways."
    assert data["relevance_score"] == 0.85
    assert data["categories"] == ["AI", "Technology"]
    assert data["keywords"] == ["ai", "machine-learning"]
    assert data["newsletter_date"] == "2026-02-15"
    assert data["is_liked"] is False
    assert data["is_bookmarked"] is False


@patch("backend.routers.articles.get_supabase_client")
def test_get_article_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 is returned for a non-existent article.

    Mock: articles table returns empty data.
    Expects: 404 status.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(articles_mock)
    mock_get_client.return_value = mock_client

    response = client.get("/api/articles/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


@patch("backend.routers.articles.get_supabase_client")
def test_get_article_with_interactions(mock_get_client: MagicMock) -> None:
    """Verify is_liked and is_bookmarked are set correctly from interactions.

    Mock: articles table returns one article, user has liked and bookmarked it.
    Expects: 200 status, is_liked=True, is_bookmarked=True.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_ARTICLE.copy()]
    )

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    interactions_mock = MagicMock()
    interactions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {"type": "like"},
            {"type": "bookmark"},
        ]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(
        articles_mock, users_mock, interactions_mock
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/articles/1")

    assert response.status_code == 200
    data = response.json()
    assert data["is_liked"] is True
    assert data["is_bookmarked"] is True
