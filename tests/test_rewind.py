"""Rewind service and router tests."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.rewind import (
    RewindReport,
    generate_rewind_report,
    persist_rewind_report,
)

client = TestClient(app)

SAMPLE_REPORT = {
    "id": 1,
    "user_id": 1,
    "period_start": "2026-02-09",
    "period_end": "2026-02-16",
    "report_content": {
        "hot_topics": ["LLM Agents", "Kubernetes"],
        "trend_changes": {"rising": ["LLM Agents"], "declining": []},
        "suggestions": ["MLOps", "Edge AI"],
    },
    "hot_topics": ["LLM Agents", "Kubernetes"],
    "trend_changes": {"rising": ["LLM Agents"], "declining": []},
    "created_at": "2026-02-16T06:00:00+00:00",
}

SAMPLE_LIKED_ARTICLES = [
    {
        "id": 10,
        "title": "LLM Agents Are Changing Everything",
        "categories": ["AI/ML"],
        "keywords": ["LLM", "agents"],
    },
    {
        "id": 11,
        "title": "Kubernetes Security Best Practices",
        "categories": ["DevOps"],
        "keywords": ["kubernetes", "security"],
    },
]

SAMPLE_PREVIOUS_REPORT = {
    "hot_topics": ["React Server Components", "LLM"],
    "trend_changes": {"rising": ["LLM"], "declining": ["Blockchain"]},
    "period_start": "2026-02-02",
    "period_end": "2026-02-09",
}

GEMINI_RESPONSE_JSON = json.dumps(
    {
        "overview": "LLM agents and Kubernetes security dominated this week's reading.",
        "hot_topics": ["LLM Agents", "Kubernetes Security"],
        "trend_changes": {
            "rising": ["LLM Agents", "Kubernetes Security"],
            "declining": ["React Server Components"],
        },
        "suggestions": ["MLOps", "Edge AI"],
    }
)


# --- Helpers ---


def _make_supabase_mock(
    *,
    interactions: list[dict] | None = None,
    articles: list[dict] | None = None,
    previous_report: list[dict] | None = None,
    insert_result: list[dict] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for rewind service tests.

    Args:
        interactions: Rows for interactions table (liked article IDs).
        articles: Rows for articles table (article details).
        previous_report: Rows for rewind_reports previous report query.
        insert_result: Rows returned from rewind_reports insert.
    """
    mock_interactions = MagicMock()
    mock_articles = MagicMock()
    mock_rewind_reports = MagicMock()

    # interactions: select -> eq -> eq -> gte -> execute
    interaction_data = interactions if interactions is not None else []
    mock_interactions.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
        data=interaction_data
    )

    # articles: select -> in_ -> execute
    article_data = articles if articles is not None else []
    mock_articles.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=article_data
    )

    # rewind_reports: select -> eq -> order -> limit -> execute (previous report)
    prev_data = previous_report if previous_report is not None else []
    mock_rewind_reports.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=prev_data
    )

    # rewind_reports: insert -> execute
    ins_data = insert_result if insert_result is not None else [{"id": 1}]
    mock_rewind_reports.insert.return_value.execute.return_value = MagicMock(
        data=ins_data
    )

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "interactions":
            return mock_interactions
        if name == "articles":
            return mock_articles
        if name == "rewind_reports":
            return mock_rewind_reports
        return MagicMock()

    mock_client.table.side_effect = route_table
    return mock_client


def _make_settings() -> MagicMock:
    """Create a mock Settings object for rewind tests."""
    settings = MagicMock()
    settings.gemini_api_key = "test-api-key"
    settings.gemini.model = "gemini-2.5-flash"
    return settings


def _make_router_mock_client(
    *,
    user: dict | None = None,
    reports: list[dict] | None = None,
    report_by_id: list[dict] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for router tests.

    Args:
        user: Row for users table lookup.
        reports: Rows for rewind_reports latest query (order -> limit -> execute).
        report_by_id: Rows for rewind_reports by-id query (eq("id") -> execute).
    """
    mock_users = MagicMock()
    mock_rewind_reports = MagicMock()

    # users: select -> eq -> execute
    user_data = [user] if user is not None else []
    mock_users.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=user_data
    )

    # rewind_reports: select -> eq(user_id) -> order -> limit -> execute (latest)
    report_data = reports if reports is not None else []
    mock_rewind_reports.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=report_data
    )

    # rewind_reports: select -> eq(id) -> execute (by ID)
    by_id_data = report_by_id if report_by_id is not None else []
    mock_rewind_reports.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=by_id_data)
    )

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "users":
            return mock_users
        if name == "rewind_reports":
            return mock_rewind_reports
        return MagicMock()

    mock_client.table.side_effect = route_table
    return mock_client


# =============================================================================
# Service tests
# =============================================================================


# --- generate_rewind_report: happy path ---


@pytest.mark.asyncio
@patch("backend.services.rewind.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.rewind.create_gemini_client")
@patch("backend.services.rewind.get_settings")
async def test_generate_rewind_happy_path(
    mock_get_settings: MagicMock,
    mock_create_gemini: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Verify report generation with liked articles and a previous report.

    Mocks: Supabase returns liked articles and previous report,
           Gemini returns valid JSON analysis.
    Expects: Report contains hot_topics, trend_changes, and suggestions.
    """
    settings = _make_settings()
    mock_get_settings.return_value = settings

    mock_response = MagicMock()
    mock_response.text = GEMINI_RESPONSE_JSON
    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_supabase_mock(
        interactions=[{"article_id": 10}, {"article_id": 11}],
        articles=SAMPLE_LIKED_ARTICLES,
        previous_report=[SAMPLE_PREVIOUS_REPORT],
    )

    report = await generate_rewind_report(supabase, user_id=1, settings=settings)

    assert report["hot_topics"] == ["LLM Agents", "Kubernetes Security"]
    assert "rising" in report["trend_changes"]
    assert "declining" in report["trend_changes"]
    assert len(report["suggestions"]) >= 1
    mock_gemini.aio.models.generate_content.assert_called_once()


# --- generate_rewind_report: first report (no previous) ---


@pytest.mark.asyncio
@patch("backend.services.rewind.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.rewind.create_gemini_client")
@patch("backend.services.rewind.get_settings")
async def test_generate_rewind_first_report(
    mock_get_settings: MagicMock,
    mock_create_gemini: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Verify report generation when no previous report exists.

    Mocks: Supabase returns liked articles but no previous report,
           Gemini returns valid JSON analysis.
    Expects: Report generated successfully, prompt mentions first analysis.
    """
    settings = _make_settings()
    mock_get_settings.return_value = settings

    mock_response = MagicMock()
    mock_response.text = GEMINI_RESPONSE_JSON
    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_supabase_mock(
        interactions=[{"article_id": 10}],
        articles=[SAMPLE_LIKED_ARTICLES[0]],
        previous_report=[],
    )

    report = await generate_rewind_report(supabase, user_id=1, settings=settings)

    assert isinstance(report["hot_topics"], list)
    assert len(report["hot_topics"]) > 0

    # Verify prompt included "first rewind analysis" context
    call_args = mock_gemini.aio.models.generate_content.call_args
    prompt = call_args.kwargs.get("contents", "")
    assert "first rewind analysis" in prompt.lower()


# --- generate_rewind_report: no likes this week ---


@pytest.mark.asyncio
@patch("backend.services.rewind.get_settings")
async def test_generate_rewind_no_likes(
    mock_get_settings: MagicMock,
) -> None:
    """Verify empty report when user has no liked articles this week.

    Mocks: Supabase interactions return empty list.
    Expects: Empty report with no hot_topics, empty trend_changes.
    """
    settings = _make_settings()
    mock_get_settings.return_value = settings

    supabase = _make_supabase_mock(interactions=[])

    report = await generate_rewind_report(supabase, user_id=1, settings=settings)

    assert report["hot_topics"] == []
    assert report["trend_changes"] == {"rising": [], "declining": []}
    assert report["suggestions"] == []


@pytest.mark.asyncio
@patch("backend.services.rewind.today_kst", return_value=date(2026, 2, 17))
async def test_generate_rewind_uses_kst_midnight_cutoff(
    _mock_today_kst: MagicMock,
) -> None:
    """Verify liked-article cutoff uses KST day boundary converted to UTC."""
    supabase = _make_supabase_mock(
        interactions=[],
        articles=[],
    )

    await generate_rewind_report(supabase, user_id=1, settings=_make_settings())

    gte_call = supabase.table(
        "interactions"
    ).select.return_value.eq.return_value.eq.return_value.gte.call_args
    assert gte_call is not None
    field_name, cutoff = gte_call.args
    assert field_name == "created_at"
    assert cutoff == "2026-02-09T15:00:00+00:00"


# --- generate_rewind_report: Gemini failure ---


@pytest.mark.asyncio
@patch("backend.services.rewind.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.rewind.create_gemini_client")
@patch("backend.services.rewind.get_settings")
async def test_generate_rewind_gemini_failure(
    mock_get_settings: MagicMock,
    mock_create_gemini: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Verify fallback empty report when Gemini API fails after retries.

    Mocks: Supabase returns liked articles, Gemini raises RuntimeError on all calls.
    Expects: Empty fallback report returned, no exception raised.
    """
    settings = _make_settings()
    mock_get_settings.return_value = settings

    mock_gemini = MagicMock()
    mock_gemini.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("Gemini API unavailable")
    )
    mock_create_gemini.return_value = mock_gemini

    supabase = _make_supabase_mock(
        interactions=[{"article_id": 10}],
        articles=[SAMPLE_LIKED_ARTICLES[0]],
    )

    report = await generate_rewind_report(supabase, user_id=1, settings=settings)

    assert report["hot_topics"] == []
    assert report["trend_changes"] == {"rising": [], "declining": []}
    assert report["suggestions"] == []


# --- persist_rewind_report ---


@pytest.mark.asyncio
async def test_persist_rewind_report_stores_correctly() -> None:
    """Verify report is persisted with correct fields in the database.

    Mocks: Supabase insert returns row with id=42.
    Expects: Returned ID matches, insert called with correct data.
    """
    report: RewindReport = {
        "overview": "LLM agents were the focus this week.",
        "hot_topics": ["LLM Agents"],
        "trend_changes": {"rising": ["LLM Agents"], "declining": []},
        "suggestions": ["MLOps"],
    }

    supabase = _make_supabase_mock(insert_result=[{"id": 42}])

    report_id = await persist_rewind_report(
        supabase,
        user_id=1,
        report=report,
        period_start=date(2026, 2, 9),
        period_end=date(2026, 2, 16),
    )

    assert report_id == 42

    # Verify the insert was called with correct data
    insert_call = supabase.table("rewind_reports").insert.call_args
    row = insert_call.args[0]
    assert row["user_id"] == 1
    assert row["period_start"] == "2026-02-09"
    assert row["period_end"] == "2026-02-16"
    assert row["hot_topics"] == ["LLM Agents"]
    assert row["trend_changes"] == {"rising": ["LLM Agents"], "declining": []}
    assert row["report_content"]["suggestions"] == ["MLOps"]


# =============================================================================
# Router tests
# =============================================================================


# --- GET /api/rewind/latest ---


@patch("backend.routers.rewind.get_supabase_client")
def test_get_latest_rewind_returns_report(mock_get_client: MagicMock) -> None:
    """Verify latest endpoint returns the most recent report.

    Mocks: Supabase returns default user and a report row.
    Expects: 200 status with report data matching the sample.
    """
    mock_get_client.return_value = _make_router_mock_client(
        user={"id": 1},
        reports=[SAMPLE_REPORT],
    )

    response = client.get("/api/rewind/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["period_start"] == "2026-02-09"
    assert data["period_end"] == "2026-02-16"
    assert data["hot_topics"] == ["LLM Agents", "Kubernetes"]


@patch("backend.routers.rewind.get_supabase_client")
def test_get_latest_rewind_404_when_empty(mock_get_client: MagicMock) -> None:
    """Verify 404 when no rewind reports exist for the user.

    Mocks: Supabase returns default user but no reports.
    Expects: 404 status with appropriate detail message.
    """
    mock_get_client.return_value = _make_router_mock_client(
        user={"id": 1},
        reports=[],
    )

    response = client.get("/api/rewind/latest")

    assert response.status_code == 404
    assert "No rewind reports found" in response.json()["detail"]


# --- GET /api/rewind/{report_id} ---


@patch("backend.routers.rewind.get_supabase_client")
def test_get_rewind_by_id_returns_report(mock_get_client: MagicMock) -> None:
    """Verify specific report returned by ID.

    Mocks: Supabase returns report row for given ID.
    Expects: 200 status with correct report data.
    """
    mock_get_client.return_value = _make_router_mock_client(
        report_by_id=[SAMPLE_REPORT],
    )

    response = client.get("/api/rewind/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["hot_topics"] == ["LLM Agents", "Kubernetes"]


@patch("backend.routers.rewind.get_supabase_client")
def test_get_rewind_by_id_404(mock_get_client: MagicMock) -> None:
    """Verify 404 when report ID does not exist.

    Mocks: Supabase returns empty for the given ID.
    Expects: 404 status with detail including the report ID.
    """
    mock_get_client.return_value = _make_router_mock_client(
        report_by_id=[],
    )

    response = client.get("/api/rewind/999")

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


# --- POST /api/rewind/generate ---


@patch("backend.routers.rewind.today_kst")
@patch("backend.routers.rewind.persist_rewind_report", new_callable=AsyncMock)
@patch("backend.routers.rewind.generate_rewind_report", new_callable=AsyncMock)
@patch("backend.routers.rewind.get_supabase_client")
def test_post_generate_rewind_creates_report(
    mock_get_client: MagicMock,
    mock_generate: AsyncMock,
    mock_persist: AsyncMock,
    mock_today_kst: MagicMock,
) -> None:
    """Verify POST endpoint triggers generation and returns new report.

    Mocks: Service generate returns report, persist returns ID=1,
           Supabase returns full report row after persist.
    Expects: 201 status, service called with correct period, report returned.
    """
    mock_today_kst.return_value = date(2026, 2, 17)

    mock_generate.return_value = {
        "overview": "LLM agents were the focus this week.",
        "hot_topics": ["LLM Agents"],
        "trend_changes": {"rising": ["LLM Agents"], "declining": []},
        "suggestions": ["MLOps"],
    }
    mock_persist.return_value = 1

    # Mock client for _get_default_user_id + fetch after persist
    mock_users = MagicMock()
    mock_users.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )

    mock_rewind = MagicMock()
    mock_rewind.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[SAMPLE_REPORT]
    )

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "users":
            return mock_users
        if name == "rewind_reports":
            return mock_rewind
        return MagicMock()

    mock_client.table.side_effect = route_table
    mock_get_client.return_value = mock_client

    response = client.post("/api/rewind/generate")

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["hot_topics"] == ["LLM Agents", "Kubernetes"]

    mock_generate.assert_called_once()
    mock_persist.assert_called_once()
    persist_call = mock_persist.call_args
    assert persist_call is not None
    assert persist_call.args[3] == date(2026, 2, 10)
    assert persist_call.args[4] == date(2026, 2, 17)
