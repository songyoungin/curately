"""Newsletter router tests."""

from datetime import date
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

SAMPLE_ARTICLE_2 = {
    "id": 2,
    "source_feed": "Hacker News",
    "source_url": "https://example.com/article-2",
    "title": "Another Article",
    "author": "Author B",
    "published_at": "2026-02-15T08:00:00+00:00",
    "summary": "Another summary",
    "relevance_score": 0.65,
    "categories": ["dev"],
    "keywords": ["python"],
    "newsletter_date": "2026-02-15",
}


def _make_mock_client(
    *,
    newsletter_dates: list[dict[str, str]] | None = None,
    articles: list[dict[str, object]] | None = None,
    user: dict[str, object] | None = None,
    interactions: list[dict[str, object]] | None = None,
) -> MagicMock:
    """Build a mock Supabase client routing table() calls by table name.

    Args:
        newsletter_dates: Rows for articles.select("newsletter_date").
        articles: Rows for articles.select(columns).eq().order().execute().
        user: Row for users.select("id").eq().execute().
        interactions: Rows for interactions.select().eq().in_().execute().
    """
    mock_articles_table = MagicMock()
    mock_users_table = MagicMock()
    mock_interactions_table = MagicMock()

    # articles table: list_newsletters path (select -> not_.is_ -> execute)
    if newsletter_dates is not None:
        mock_articles_table.select.return_value.not_.is_.return_value.execute.return_value = MagicMock(
            data=newsletter_dates
        )

    # articles table: get_newsletter_by_date path (select -> eq -> order -> execute)
    article_data = articles if articles is not None else []
    mock_articles_table.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=article_data
    )

    # users table
    user_data = [user] if user is not None else []
    mock_users_table.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=user_data)
    )

    # interactions table
    interaction_data = interactions if interactions is not None else []
    mock_interactions_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
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


# --- GET /api/newsletters ---


@patch("backend.routers.newsletters.get_supabase_client")
def test_list_newsletters_returns_editions(mock_get_client: MagicMock) -> None:
    """Verify paginated edition list is returned sorted by date desc.

    Mock: articles table returns rows with two distinct newsletter_dates.
    Expects: 200 status, 2 editions sorted by date descending.
    """
    mock_get_client.return_value = _make_mock_client(
        newsletter_dates=[
            {"newsletter_date": "2026-02-15"},
            {"newsletter_date": "2026-02-16"},
            {"newsletter_date": "2026-02-16"},
        ]
    )

    response = client.get("/api/newsletters")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["date"] == "2026-02-16"
    assert data[0]["article_count"] == 2
    assert data[1]["date"] == "2026-02-15"
    assert data[1]["article_count"] == 1


@patch("backend.routers.newsletters.get_supabase_client")
def test_list_newsletters_empty(mock_get_client: MagicMock) -> None:
    """Verify empty list when no articles have newsletter_date.

    Mock: articles table returns empty list.
    Expects: 200 status, empty list.
    """
    mock_get_client.return_value = _make_mock_client(newsletter_dates=[])

    response = client.get("/api/newsletters")

    assert response.status_code == 200
    assert response.json() == []


@patch("backend.routers.newsletters.get_supabase_client")
def test_list_newsletters_pagination(mock_get_client: MagicMock) -> None:
    """Verify pagination with limit and offset params.

    Mock: articles table returns rows with 3 distinct newsletter_dates.
    Expects: 200 status, correct subset returned.
    """
    mock_get_client.return_value = _make_mock_client(
        newsletter_dates=[
            {"newsletter_date": "2026-02-14"},
            {"newsletter_date": "2026-02-15"},
            {"newsletter_date": "2026-02-16"},
        ]
    )

    response = client.get("/api/newsletters?limit=1&offset=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-02-15"


# --- GET /api/newsletters/today ---


@patch("backend.routers.newsletters.today_kst")
@patch("backend.routers.newsletters.get_supabase_client")
def test_get_today_newsletter(
    mock_get_client: MagicMock, mock_today_kst: MagicMock
) -> None:
    """Verify today's newsletter returns articles with interaction flags.

    Mock: KST today returns fixed date, articles for that date exist,
          default user exists, no interactions.
    Expects: 200 status, newsletter with articles, flags default to false.
    """
    mock_today_kst.return_value = date(2026, 2, 16)
    mock_get_client.return_value = _make_mock_client(
        articles=[SAMPLE_ARTICLE],
        user={"id": 1},
        interactions=[],
    )

    response = client.get("/api/newsletters/today")

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-02-16"
    assert data["article_count"] == 1
    assert data["articles"][0]["title"] == "Test Article"
    assert data["articles"][0]["is_liked"] is False
    assert data["articles"][0]["is_bookmarked"] is False


@patch("backend.routers.newsletters.today_kst")
@patch("backend.routers.newsletters.get_supabase_client")
def test_get_today_newsletter_empty(
    mock_get_client: MagicMock, mock_today_kst: MagicMock
) -> None:
    """Verify 404 when no articles for today.

    Mock: KST today returns fixed date, no articles for that date.
    Expects: 404 status.
    """
    mock_today_kst.return_value = date(2026, 2, 16)
    mock_get_client.return_value = _make_mock_client(articles=[])

    response = client.get("/api/newsletters/today")

    assert response.status_code == 404


# --- GET /api/newsletters/{date} ---


@patch("backend.routers.newsletters.get_supabase_client")
def test_get_newsletter_by_date(mock_get_client: MagicMock) -> None:
    """Verify specific date's newsletter returns articles with interaction flags.

    Mock: articles for date exist, user has a like interaction on the article.
    Expects: 200 status, newsletter with is_liked=True.
    """
    mock_get_client.return_value = _make_mock_client(
        articles=[SAMPLE_ARTICLE],
        user={"id": 1},
        interactions=[{"article_id": 1, "type": "like"}],
    )

    response = client.get("/api/newsletters/2026-02-16")

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-02-16"
    assert data["article_count"] == 1
    assert data["articles"][0]["is_liked"] is True
    assert data["articles"][0]["is_bookmarked"] is False


@patch("backend.routers.newsletters.get_supabase_client")
def test_get_newsletter_by_date_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 when no articles for the given date.

    Mock: articles table returns empty for the requested date.
    Expects: 404 status.
    """
    mock_get_client.return_value = _make_mock_client(articles=[])

    response = client.get("/api/newsletters/2020-01-01")

    assert response.status_code == 404
    assert "No newsletter found" in response.json()["detail"]
