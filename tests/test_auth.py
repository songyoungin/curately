"""Auth dependency and endpoint tests.

Tests JWT verification with PyJWT: valid, expired, invalid, and missing tokens.
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import get_current_user_id

JWT_SECRET = "test-jwt-secret-for-testing"
MOCK_USER_ROW: dict[str, Any] = {
    "id": 42,
    "email": "test@example.com",
    "name": "test",
    "google_sub": "google-sub-123",
}


def _make_token(
    *,
    email: str = "test@example.com",
    sub: str = "google-sub-123",
    expired: bool = False,
    audience: str = "authenticated",
) -> str:
    """Create a JWT token for testing."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "email": email,
        "sub": sub,
        "aud": audience,
        "iat": now,
        "exp": now - 100 if expired else now + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _make_mock_settings() -> MagicMock:
    """Build mock settings with JWT secret."""
    settings = MagicMock()
    settings.supabase_jwt_secret = JWT_SECRET
    return settings


def _make_mock_client(
    existing_user: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for user upsert operations."""
    mock_client = MagicMock()

    def table_router(table_name: str) -> MagicMock:
        mock_table = MagicMock()
        if table_name == "users":
            # select().eq().execute() -> existing user lookup
            select_chain = MagicMock()
            select_chain.execute.return_value = MagicMock(
                data=[existing_user] if existing_user else []
            )
            eq_chain = MagicMock(return_value=select_chain)
            select_mock = MagicMock(return_value=MagicMock(eq=eq_chain))
            mock_table.select = select_mock

            # insert().execute() -> new user insert
            insert_result = MagicMock(data=[MOCK_USER_ROW])
            mock_table.insert = MagicMock(
                return_value=MagicMock(execute=MagicMock(return_value=insert_result))
            )

            # update().eq().execute() -> user update
            update_chain = MagicMock()
            update_chain.eq = MagicMock(
                return_value=MagicMock(
                    execute=MagicMock(return_value=MagicMock(data=[MOCK_USER_ROW]))
                )
            )
            mock_table.update = MagicMock(return_value=update_chain)

        return mock_table

    mock_client.table = table_router
    return mock_client


def _build_test_app() -> FastAPI:
    """Create a minimal FastAPI app with a protected endpoint."""
    from fastapi import Depends

    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected_endpoint(
        user_id: int = Depends(get_current_user_id),
    ) -> dict[str, int]:
        return {"user_id": user_id}

    return test_app


@patch("backend.auth.get_settings")
@patch("backend.auth.get_supabase_client")
def test_valid_token_returns_user_id(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """Valid JWT with existing user returns the user_id."""
    mock_get_settings.return_value = _make_mock_settings()
    mock_get_client.return_value = _make_mock_client(existing_user=MOCK_USER_ROW)

    app = _build_test_app()
    client = TestClient(app)
    token = _make_token()
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user_id": 42}


@patch("backend.auth.get_settings")
@patch("backend.auth.get_supabase_client")
def test_valid_token_creates_new_user(
    mock_get_client: MagicMock,
    mock_get_settings: MagicMock,
) -> None:
    """Valid JWT with no existing user creates a new user row."""
    mock_get_settings.return_value = _make_mock_settings()
    mock_get_client.return_value = _make_mock_client(existing_user=None)

    app = _build_test_app()
    client = TestClient(app)
    token = _make_token()
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user_id": 42}


@patch("backend.auth.get_settings")
def test_expired_token_returns_401(
    mock_get_settings: MagicMock,
) -> None:
    """Expired JWT returns 401."""
    mock_get_settings.return_value = _make_mock_settings()

    app = _build_test_app()
    client = TestClient(app)
    token = _make_token(expired=True)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@patch("backend.auth.get_settings")
def test_invalid_token_returns_401(
    mock_get_settings: MagicMock,
) -> None:
    """Malformed JWT returns 401."""
    mock_get_settings.return_value = _make_mock_settings()

    app = _build_test_app()
    client = TestClient(app)
    response = client.get(
        "/protected", headers={"Authorization": "Bearer not-a-valid-jwt"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_missing_auth_header_returns_422() -> None:
    """Missing Authorization header returns 422 (FastAPI validation)."""
    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/protected")
    assert response.status_code == 422


@patch("backend.auth.get_settings")
def test_invalid_header_format_returns_401(
    mock_get_settings: MagicMock,
) -> None:
    """Authorization header without 'Bearer ' prefix returns 401."""
    mock_get_settings.return_value = _make_mock_settings()

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": "Token some-token"})
    assert response.status_code == 401
    assert "format" in response.json()["detail"].lower()


@patch("backend.auth.get_settings")
def test_token_missing_email_returns_401(
    mock_get_settings: MagicMock,
) -> None:
    """JWT without email claim returns 401."""
    mock_get_settings.return_value = _make_mock_settings()

    now = int(time.time())
    payload = {
        "sub": "google-sub-123",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "email" in response.json()["detail"].lower()
