"""Interest service and router tests."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.config import InterestsConfig, Settings
from backend.main import app
from backend.services.interests import (
    apply_time_decay,
    remove_interests_on_unlike,
    update_interests_on_like,
)

client = TestClient(app)


def _make_settings(
    *,
    like_weight_increment: float = 1.0,
    decay_factor: float = 0.9,
    decay_interval_days: int = 7,
) -> Settings:
    """Build a Settings object with custom interests config.

    Args:
        like_weight_increment: Weight added per like.
        decay_factor: Multiplier for time decay.
        decay_interval_days: Days before decay applies.
    """
    settings = MagicMock(spec=Settings)
    settings.interests = InterestsConfig(
        like_weight_increment=like_weight_increment,
        decay_factor=decay_factor,
        decay_interval_days=decay_interval_days,
    )
    return settings


# --- update_interests_on_like ---


@pytest.mark.asyncio
async def test_update_interests_on_like_new_keywords() -> None:
    """Verify new keywords are upserted with correct weight.

    Mock: article has keywords ["ai", "ml"], no existing interests.
    Expects: upsert called twice with weight=1.0 for each keyword.
    """
    mock_client = MagicMock()
    # _fetch_article: articles.select(...).eq(id).execute()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1, "keywords": ["ai", "ml"], "source_feed": "TechCrunch"}]
    )
    # _fetch_user_interests_by_keywords: user_interests.select(...).eq().in_().execute()
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[]
    )
    # upsert
    mock_client.table.return_value.upsert.return_value.execute.return_value = (
        MagicMock()
    )

    settings = _make_settings(like_weight_increment=1.0)
    await update_interests_on_like(
        mock_client, user_id=1, article_id=1, settings=settings
    )

    assert mock_client.table.return_value.upsert.call_count == 2


@pytest.mark.asyncio
async def test_update_interests_on_like_increments_existing() -> None:
    """Verify existing keyword weight is incremented.

    Mock: article has keyword ["ai"], existing interest has weight=2.0.
    Expects: upsert called with weight=3.0.
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1, "keywords": ["ai"], "source_feed": "TechCrunch"}]
    )
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"keyword": "ai", "weight": 2.0}]
    )
    mock_client.table.return_value.upsert.return_value.execute.return_value = (
        MagicMock()
    )

    settings = _make_settings(like_weight_increment=1.0)
    await update_interests_on_like(
        mock_client, user_id=1, article_id=1, settings=settings
    )

    upsert_call = mock_client.table.return_value.upsert.call_args
    assert upsert_call[0][0]["weight"] == 3.0


# --- remove_interests_on_unlike ---


@pytest.mark.asyncio
async def test_remove_interests_on_unlike_decrements() -> None:
    """Verify unlike decrements weight for existing keywords.

    Mock: article has keyword ["ai"], existing weight=3.0, decrement=1.0.
    Expects: upsert called with weight=2.0 (not deleted).
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1, "keywords": ["ai"], "source_feed": "TechCrunch"}]
    )
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"keyword": "ai", "weight": 3.0}]
    )
    mock_client.table.return_value.upsert.return_value.execute.return_value = (
        MagicMock()
    )

    settings = _make_settings(like_weight_increment=1.0)
    await remove_interests_on_unlike(
        mock_client, user_id=1, article_id=1, settings=settings
    )

    upsert_call = mock_client.table.return_value.upsert.call_args
    assert upsert_call[0][0]["weight"] == 2.0


@pytest.mark.asyncio
async def test_remove_interests_on_unlike_deletes_at_zero() -> None:
    """Verify unlike removes interest when weight drops to zero.

    Mock: article has keyword ["ai"], existing weight=1.0, decrement=1.0.
    Expects: delete called (not upsert).
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1, "keywords": ["ai"], "source_feed": "TechCrunch"}]
    )
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"keyword": "ai", "weight": 1.0}]
    )
    mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

    settings = _make_settings(like_weight_increment=1.0)
    await remove_interests_on_unlike(
        mock_client, user_id=1, article_id=1, settings=settings
    )

    mock_client.table.return_value.delete.assert_called_once()


# --- apply_time_decay ---


@pytest.mark.asyncio
async def test_apply_time_decay_decays_stale() -> None:
    """Verify stale interests are decayed by the configured factor.

    Mock: one stale interest with weight=5.0, decay_factor=0.9.
    Expects: update called with weight=4.5.
    """
    mock_client = MagicMock()
    stale_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
        data=[{"id": 10, "keyword": "ai", "weight": 5.0, "updated_at": stale_date}]
    )
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    settings = _make_settings(decay_factor=0.9, decay_interval_days=7)
    count = await apply_time_decay(mock_client, user_id=1, settings=settings)

    assert count == 1
    update_call = mock_client.table.return_value.update.call_args
    assert abs(update_call[0][0]["weight"] - 4.5) < 0.001


@pytest.mark.asyncio
async def test_apply_time_decay_removes_below_threshold() -> None:
    """Verify interests below minimum weight are deleted after decay.

    Mock: one stale interest with weight=0.005, decay_factor=0.9.
    Expects: delete called (0.005 * 0.9 = 0.0045 < 0.01 threshold).
    """
    mock_client = MagicMock()
    stale_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
        data=[{"id": 20, "keyword": "old", "weight": 0.005, "updated_at": stale_date}]
    )
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()

    settings = _make_settings(decay_factor=0.9, decay_interval_days=7)
    count = await apply_time_decay(mock_client, user_id=1, settings=settings)

    assert count == 1
    mock_client.table.return_value.delete.assert_called_once()


# --- GET /api/interests ---


@patch("backend.routers.interests.get_supabase_client")
def test_list_interests_returns_sorted(mock_get_client: MagicMock) -> None:
    """Verify interest profile is returned sorted by weight descending.

    Mock: user exists, two interests with different weights.
    Expects: 200 status, interests returned.
    """
    mock_client = MagicMock()
    # users.select(id).eq(email).execute()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )
    # user_interests.select(*).eq(user_id).order(weight).execute()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": 1,
                "keyword": "ai",
                "weight": 5.0,
                "source": "TechCrunch",
                "updated_at": "2026-02-16T10:00:00+00:00",
            },
            {
                "id": 2,
                "keyword": "python",
                "weight": 3.0,
                "source": None,
                "updated_at": "2026-02-15T10:00:00+00:00",
            },
        ]
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/interests")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["keyword"] == "ai"
    assert data[0]["weight"] == 5.0


@patch("backend.routers.interests.get_supabase_client")
def test_list_interests_empty(mock_get_client: MagicMock) -> None:
    """Verify empty list when user has no interests.

    Mock: user exists, no interests in database.
    Expects: 200 status, empty list.
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/interests")

    assert response.status_code == 200
    assert response.json() == []


@patch("backend.routers.interests.get_supabase_client")
def test_list_interests_no_user(mock_get_client: MagicMock) -> None:
    """Verify empty list when default user does not exist.

    Mock: users table returns empty.
    Expects: 200 status, empty list.
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_get_client.return_value = mock_client

    response = client.get("/api/interests")

    assert response.status_code == 200
    assert response.json() == []
