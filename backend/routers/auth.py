"""Authentication route handlers."""

from typing import Any, cast

from fastapi import APIRouter, Depends

from backend.auth import get_current_user_id
from backend.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def get_me(user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    """Return the current authenticated user's info.

    Args:
        user_id: Injected by the JWT auth dependency.

    Returns:
        The user row from the database.
    """
    client = get_supabase_client()
    result = client.table("users").select("*").eq("id", user_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    return rows[0]
