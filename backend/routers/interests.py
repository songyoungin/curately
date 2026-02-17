"""Interest profile route handlers."""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import APIRouter, Depends

from backend.auth import get_current_user_id
from backend.schemas.interests import UserInterestResponse
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interests", tags=["interests"])


@router.get("", response_model=list[UserInterestResponse])
async def list_interests(
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """Return the authenticated user's interest profile sorted by weight descending."""
    client = get_supabase_client()

    response = (
        client.table("user_interests")
        .select("*")
        .eq("user_id", user_id)
        .order("weight", desc=True)
        .execute()
    )
    return cast(list[dict[str, Any]], response.data)
