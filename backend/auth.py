"""JWT verification dependency for Supabase Google OAuth."""

from __future__ import annotations

import logging
from typing import Any, cast

import jwt
from fastapi import Header, HTTPException, status

from backend.config import get_settings
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


async def get_current_user_id(
    authorization: str = Header(...),
) -> int:
    """Extract and verify the JWT from the Authorization header.

    Decodes the Supabase JWT, extracts the user's email and Google sub,
    then upserts into the users table and returns the internal user ID.

    Args:
        authorization: Bearer token from the Authorization header.

    Returns:
        The internal BIGSERIAL user_id from the users table.

    Raises:
        HTTPException: 401 on invalid, expired, or missing token.
    """
    settings = get_settings()

    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET not configured",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    email: str | None = payload.get("email")
    sub: str | None = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim",
        )

    user_id = _upsert_user(email=email, google_sub=sub)
    return user_id


def _upsert_user(*, email: str, google_sub: str | None) -> int:
    """Find or create a user by email, updating google_sub and last_login_at.

    Args:
        email: User email from the JWT.
        google_sub: Google subject identifier from the JWT.

    Returns:
        The user's internal ID.
    """
    client = get_supabase_client()

    result = client.table("users").select("id").eq("email", email).execute()
    rows = cast(list[dict[str, Any]], result.data)

    if rows:
        user_id = int(rows[0]["id"])
        update_data: dict[str, Any] = {"last_login_at": "now()"}
        if google_sub:
            update_data["google_sub"] = google_sub
        client.table("users").update(update_data).eq("id", user_id).execute()
        return user_id

    insert_data: dict[str, Any] = {"email": email, "name": email.split("@")[0]}
    if google_sub:
        insert_data["google_sub"] = google_sub
    insert_result = client.table("users").insert(insert_data).execute()
    new_row = cast(dict[str, Any], insert_result.data[0])
    logger.info("Created new user: %s (id=%s)", email, new_row["id"])
    return int(new_row["id"])
