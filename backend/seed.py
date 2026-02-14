"""MVP default user seeding logic."""

import logging

from supabase import Client

logger = logging.getLogger(__name__)

DEFAULT_USER_EMAIL = "default@curately.local"
DEFAULT_USER_NAME = "Default User"


async def seed_default_user(client: Client) -> None:
    """Create the default MVP user if it does not exist.

    Checks for the default user by email. If missing, inserts a new row.
    This allows the app to operate without authentication in MVP mode.
    """
    result = (
        client.table("users").select("id").eq("email", DEFAULT_USER_EMAIL).execute()
    )

    if result.data:
        logger.info("Default user already exists (id=%s)", result.data[0]["id"])
        return

    client.table("users").insert(
        {"email": DEFAULT_USER_EMAIL, "name": DEFAULT_USER_NAME}
    ).execute()
    logger.info("Default user created: %s", DEFAULT_USER_EMAIL)
