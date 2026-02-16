"""Bookmarked articles list endpoint tests."""

from unittest.mock import MagicMock, patch

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
    "summary": "A test summary",
    "relevance_score": 0.85,
    "categories": ["tech"],
    "keywords": ["ai", "ml"],
    "newsletter_date": "2026-02-16",
}


def _make_mock_client(
    *,
    user: dict[str, object] | None = None,
    bookmark_rows: list[dict[str, object]] | None = None,
    articles: list[dict[str, object]] | None = None,
    all_interactions: list[dict[str, object]] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for bookmarked articles tests.

    Args:
        user: User row for default user lookup.
        bookmark_rows: Bookmark interaction rows (article_id list).
        articles: Article rows fetched by article IDs.
        all_interactions: All interactions for _attach_interaction_flags.
    """
    mock_users_table = MagicMock()
    mock_interactions_table = MagicMock()
    mock_articles_table = MagicMock()

    # users.select(id).eq(email).execute()
    user_data = [user] if user is not None else []
    mock_users_table.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=user_data)
    )

    # interactions.select(article_id).eq(user_id).eq(type=bookmark).execute()
    bookmark_data = bookmark_rows if bookmark_rows is not None else []
    mock_interactions_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=bookmark_data
    )

    # interactions.select(article_id, type).eq(user_id).in_(article_id).execute()
    # (used by _attach_interaction_flags)
    interaction_data = all_interactions if all_interactions is not None else []
    mock_interactions_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=interaction_data
    )

    # articles.select(columns).in_(id, ids).execute()
    article_data = articles if articles is not None else []
    mock_articles_table.select.return_value.in_.return_value.execute.return_value = (
        MagicMock(data=article_data)
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


# --- GET /api/articles/bookmarked ---


@patch("backend.routers.articles.get_supabase_client")
def test_bookmarked_returns_articles(mock_get_client: MagicMock) -> None:
    """Verify bookmarked articles are returned with interaction flags.

    Mock: user exists, one bookmark interaction, matching article found.
    Expects: 200 status, one article with is_bookmarked=true.
    """
    mock_get_client.return_value = _make_mock_client(
        user={"id": 1},
        bookmark_rows=[{"article_id": 1}],
        articles=[SAMPLE_ARTICLE],
        all_interactions=[{"article_id": 1, "type": "bookmark"}],
    )

    response = client.get("/api/articles/bookmarked")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["title"] == "Test Article"
    assert data[0]["is_bookmarked"] is True


@patch("backend.routers.articles.get_supabase_client")
def test_bookmarked_empty(mock_get_client: MagicMock) -> None:
    """Verify empty list when user has no bookmarks.

    Mock: user exists, no bookmark interactions.
    Expects: 200 status, empty list.
    """
    mock_get_client.return_value = _make_mock_client(
        user={"id": 1},
        bookmark_rows=[],
    )

    response = client.get("/api/articles/bookmarked")

    assert response.status_code == 200
    assert response.json() == []
