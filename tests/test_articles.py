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


# --- GET /api/articles/bookmarked ---


@patch("backend.routers.articles.get_supabase_client")
def test_list_bookmarked_articles_ordered_by_recent(mock_get_client: MagicMock) -> None:
    """Verify bookmarked articles are sorted by bookmark time, newest first.

    Mock: two bookmark interactions with different created_at timestamps,
    two matching articles returned in id-ascending order by Supabase.
    Expects: articles reordered so that the more recently bookmarked article comes first.
    """
    mock_client = MagicMock()

    # interactions table: select("article_id, created_at").eq(user_id).eq(type).order(created_at desc)
    mock_interactions = MagicMock()
    mock_interactions.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {"article_id": 2, "created_at": "2026-02-20T12:00:00+00:00"},
            {"article_id": 1, "created_at": "2026-02-19T08:00:00+00:00"},
        ]
    )

    # articles table: select(columns).in_(id, [...]).execute() — returns in id order
    mock_articles = MagicMock()
    mock_articles.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": 1,
                "source_feed": "Feed A",
                "source_url": "https://example.com/1",
                "title": "Older Bookmark",
                "author": "Author A",
                "published_at": "2026-02-18T10:00:00+00:00",
                "summary": "Summary 1",
                "detailed_summary": None,
                "relevance_score": 0.8,
                "categories": ["tech"],
                "keywords": ["python"],
                "newsletter_date": "2026-02-18",
            },
            {
                "id": 2,
                "source_feed": "Feed B",
                "source_url": "https://example.com/2",
                "title": "Newer Bookmark",
                "author": "Author B",
                "published_at": "2026-02-19T10:00:00+00:00",
                "summary": "Summary 2",
                "detailed_summary": None,
                "relevance_score": 0.7,
                "categories": ["devops"],
                "keywords": ["k8s"],
                "newsletter_date": "2026-02-19",
            },
        ]
    )

    # _attach_interaction_flags needs interactions table for flag lookup
    mock_flag_interactions = MagicMock()
    mock_flag_interactions.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {"article_id": 1, "type": "bookmark"},
            {"article_id": 2, "type": "bookmark"},
        ]
    )

    call_count = {"interactions": 0}

    def route_table(name: str) -> MagicMock:
        if name == "interactions":
            call_count["interactions"] += 1
            # First call: fetch bookmark article_ids (ordered)
            # Second call: _attach_interaction_flags
            if call_count["interactions"] == 1:
                return mock_interactions
            return mock_flag_interactions
        if name == "articles":
            return mock_articles
        return MagicMock()

    mock_client.table.side_effect = route_table
    mock_get_client.return_value = mock_client

    response = client.get("/api/articles/bookmarked")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Most recently bookmarked article should come first
    assert data[0]["id"] == 2
    assert data[0]["title"] == "Newer Bookmark"
    assert data[1]["id"] == 1
    assert data[1]["title"] == "Older Bookmark"
