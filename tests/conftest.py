"""Shared test fixtures.

Provides a global auth dependency override so protected endpoints
can be tested without real JWT tokens.
"""

from collections.abc import Iterator

import pytest

from backend.auth import get_current_user_id
from backend.main import app

MOCK_USER_ID = 1


async def _mock_get_current_user_id() -> int:
    """Return a fixed user ID for testing."""
    return MOCK_USER_ID


@pytest.fixture(autouse=True)
def override_auth_dependency() -> Iterator[None]:
    """Override the auth dependency for all tests.

    Tests in test_auth.py that need real JWT behavior should
    create their own FastAPI app instance instead of using the global app.
    """
    app.dependency_overrides[get_current_user_id] = _mock_get_current_user_id
    yield
    app.dependency_overrides.pop(get_current_user_id, None)
