"""Newsletter API endpoint tests."""

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
    "detailed_summary": None,
    "relevance_score": 0.85,
    "categories": ["AI", "Technology"],
    "keywords": ["ai", "machine-learning"],
    "newsletter_date": "2026-02-15",
    "created_at": "2026-02-15T06:00:00+00:00",
    "updated_at": "2026-02-15T06:00:00+00:00",
}

SAMPLE_ARTICLE_2 = {
    "id": 2,
    "source_feed": "Hacker News",
    "source_url": "https://news.ycombinator.com/item?id=123",
    "title": "Rust for Web Development",
    "author": "Jane Smith",
    "published_at": "2026-02-15T09:00:00+00:00",
    "raw_content": "Rust article content.",
    "summary": "Rust is gaining traction for web development.",
    "detailed_summary": None,
    "relevance_score": 0.72,
    "categories": ["Programming", "Web"],
    "keywords": ["rust", "web"],
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


# --- GET /api/newsletters ---


@patch("backend.routers.newsletters.get_supabase_client")
def test_list_newsletters_returns_editions(mock_get_client: MagicMock) -> None:
    """Verify newsletter list returns dates with article counts.

    Mock: articles table returns rows with newsletter_date values.
    Expects: 200 status, list of date/count pairs.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.not_.is_.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {"newsletter_date": "2026-02-15"},
            {"newsletter_date": "2026-02-15"},
            {"newsletter_date": "2026-02-14"},
            {"newsletter_date": "2026-02-14"},
            {"newsletter_date": "2026-02-14"},
        ]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(articles_mock)
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["date"] == "2026-02-15"
    assert data[0]["article_count"] == 2
    assert data[1]["date"] == "2026-02-14"
    assert data[1]["article_count"] == 3


@patch("backend.routers.newsletters.get_supabase_client")
def test_list_newsletters_empty(mock_get_client: MagicMock) -> None:
    """Verify empty list is returned when no newsletters exist.

    Mock: articles table returns empty data.
    Expects: 200 status, empty list.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.not_.is_.return_value.order.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(articles_mock)
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters")

    assert response.status_code == 200
    assert response.json() == []


@patch("backend.routers.newsletters.get_supabase_client")
def test_list_newsletters_pagination(mock_get_client: MagicMock) -> None:
    """Verify offset and limit pagination parameters work correctly.

    Mock: articles table returns rows for 3 dates.
    Expects: With offset=1&limit=1, returns only the second date.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.not_.is_.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {"newsletter_date": "2026-02-15"},
            {"newsletter_date": "2026-02-14"},
            {"newsletter_date": "2026-02-13"},
        ]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(articles_mock)
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters?offset=1&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-02-14"
    assert data[0]["article_count"] == 1


# --- GET /api/newsletters/today ---


@patch("backend.routers.newsletters.datetime")
@patch("backend.routers.newsletters.get_supabase_client")
def test_today_newsletter_returns_articles(
    mock_get_client: MagicMock, mock_datetime: MagicMock
) -> None:
    """Verify today's newsletter returns articles sorted by relevance.

    Mock: articles table returns 2 articles for today, user exists.
    Expects: 200 status, articles returned with correct count.
    """
    from datetime import date

    mock_datetime.now.return_value.date.return_value = date(2026, 2, 15)

    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_ARTICLE.copy(), SAMPLE_ARTICLE_2.copy()]
    )

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    interactions_mock = MagicMock()
    interactions_mock.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(
        articles_mock, users_mock, interactions_mock
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters/today")

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-02-15"
    assert data["article_count"] == 2
    assert len(data["articles"]) == 2
    assert data["articles"][0]["title"] == "AI Advances in 2026"


@patch("backend.routers.newsletters.datetime")
@patch("backend.routers.newsletters.get_supabase_client")
def test_today_newsletter_empty(
    mock_get_client: MagicMock, mock_datetime: MagicMock
) -> None:
    """Verify 200 with empty articles when no articles exist for today.

    Mock: articles table returns empty data for today's date.
    Expects: 200 status, article_count=0, empty articles list.
    """
    from datetime import date

    mock_datetime.now.return_value.date.return_value = date(2026, 2, 15)

    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(articles_mock)
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters/today")

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-02-15"
    assert data["article_count"] == 0
    assert data["articles"] == []


@patch("backend.routers.newsletters.datetime")
@patch("backend.routers.newsletters.get_supabase_client")
def test_today_newsletter_with_interactions(
    mock_get_client: MagicMock, mock_datetime: MagicMock
) -> None:
    """Verify is_liked and is_bookmarked are set correctly from interactions.

    Mock: articles table returns 1 article, user has liked it.
    Expects: 200 status, article has is_liked=True, is_bookmarked=False.
    """
    from datetime import date

    mock_datetime.now.return_value.date.return_value = date(2026, 2, 15)

    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_ARTICLE.copy()]
    )

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    interactions_mock = MagicMock()
    interactions_mock.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"article_id": 1, "type": "like"}]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(
        articles_mock, users_mock, interactions_mock
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters/today")

    assert response.status_code == 200
    data = response.json()
    assert data["article_count"] == 1
    article = data["articles"][0]
    assert article["is_liked"] is True
    assert article["is_bookmarked"] is False


# --- GET /api/newsletters/{date} ---


@patch("backend.routers.newsletters.get_supabase_client")
def test_date_newsletter_returns_articles(mock_get_client: MagicMock) -> None:
    """Verify specific date's newsletter returns articles.

    Mock: articles table returns articles for 2026-02-14.
    Expects: 200 status, correct date and articles.
    """
    article_for_date = {**SAMPLE_ARTICLE, "newsletter_date": "2026-02-14"}

    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[article_for_date]
    )

    users_mock = MagicMock()
    users_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    interactions_mock = MagicMock()
    interactions_mock.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(
        articles_mock, users_mock, interactions_mock
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters/2026-02-14")

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-02-14"
    assert data["article_count"] == 1
    assert data["articles"][0]["title"] == "AI Advances in 2026"


@patch("backend.routers.newsletters.get_supabase_client")
def test_date_newsletter_not_found(mock_get_client: MagicMock) -> None:
    """Verify 404 is returned when no articles exist for the requested date.

    Mock: articles table returns empty data for 2026-01-01.
    Expects: 404 status.
    """
    articles_mock = MagicMock()
    articles_mock.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[]
    )

    mock_client = MagicMock()
    mock_client.table = _make_table_side_effect(articles_mock)
    mock_get_client.return_value = mock_client

    response = client.get("/api/newsletters/2026-01-01")

    assert response.status_code == 404


def test_date_newsletter_invalid_format() -> None:
    """Verify 422 is returned when date format is invalid.

    Mock: None (validation happens before DB query).
    Expects: 422 status.
    """
    response = client.get("/api/newsletters/not-a-date")

    assert response.status_code == 422
