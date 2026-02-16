"""Interest profile route handlers."""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import APIRouter

from backend.schemas.interests import UserInterestResponse
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interests", tags=["interests"])


@router.get("", response_model=list[UserInterestResponse])
async def list_interests() -> list[dict[str, Any]]:
    """Return the default user's interest profile sorted by weight descending."""
    client = get_supabase_client()

    # Resolve default user ID
    user_resp = (
        client.table("users")
        .select("id")
        .eq("email", "default@curately.local")
        .execute()
    )
    users = cast(list[dict[str, Any]], user_resp.data)
    if not users:
        return []

    user_id = users[0]["id"]

    response = (
        client.table("user_interests")
        .select("*")
        .eq("user_id", user_id)
        .order("weight", desc=True)
        .execute()
    )
    return cast(list[dict[str, Any]], response.data)
