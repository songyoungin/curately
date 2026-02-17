"""Pipeline router endpoint tests."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@patch("backend.routers.pipeline.get_settings")
def test_trigger_pipeline_rejects_invalid_token(
    mock_get_settings: MagicMock,
) -> None:
    """Return 401 when pipeline token is configured and request token is missing."""
    settings = MagicMock()
    settings.pipeline_trigger_token = "expected-token"
    mock_get_settings.return_value = settings

    response = client.post("/api/pipeline/run")

    assert response.status_code == 401


@patch("backend.routers.pipeline.get_settings")
@patch("backend.routers.pipeline.run_daily_pipeline", new_callable=AsyncMock)
@patch("backend.routers.pipeline.get_supabase_client")
def test_trigger_pipeline_accepts_valid_token(
    mock_get_client: MagicMock,
    mock_run_pipeline: AsyncMock,
    mock_get_settings: MagicMock,
) -> None:
    """Return 200 when request token matches configured token."""
    settings = MagicMock()
    settings.pipeline_trigger_token = "expected-token"
    mock_get_settings.return_value = settings
    mock_get_client.return_value = MagicMock()
    mock_run_pipeline.return_value = {
        "articles_collected": 1,
        "articles_scored": 1,
        "articles_filtered": 1,
        "articles_summarized": 1,
        "newsletter_date": "2026-02-17",
    }

    response = client.post(
        "/api/pipeline/run",
        headers={"X-Pipeline-Token": "expected-token"},
    )

    assert response.status_code == 200


@patch("backend.routers.pipeline.get_settings")
@patch(
    "backend.routers.pipeline.run_weekly_rewind_for_all_users", new_callable=AsyncMock
)
def test_trigger_weekly_rewind_requires_valid_token(
    mock_run_rewind: AsyncMock,
    mock_get_settings: MagicMock,
) -> None:
    """Return 204 and trigger rewind when request token is valid."""
    settings = MagicMock()
    settings.pipeline_trigger_token = "expected-token"
    mock_get_settings.return_value = settings

    response = client.post(
        "/api/pipeline/rewind/run",
        headers={"X-Pipeline-Token": "expected-token"},
    )

    assert response.status_code == 204
    mock_run_rewind.assert_awaited_once()
