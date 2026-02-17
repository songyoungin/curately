"""MVP default user and feed seeding logic."""

import logging
from typing import Any, cast

from supabase import Client

from backend.config import get_settings

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
        first_row: dict[str, Any] = result.data[0]  # type: ignore[assignment]
        logger.info("Default user already exists (id=%s)", first_row["id"])
        return

    client.table("users").insert(
        {"email": DEFAULT_USER_EMAIL, "name": DEFAULT_USER_NAME}
    ).execute()
    logger.info("Default user created: %s", DEFAULT_USER_EMAIL)


async def seed_default_feeds(client: Client) -> None:
    """Seed default feeds from config.yaml into the database.

    Reads the configured feeds from settings and inserts any that do not
    already exist (matched by URL). Skips feeds that are already present.
    """
    settings = get_settings()

    if not settings.feeds:
        logger.info("No feeds configured in config.yaml")
        return

    for feed_config in settings.feeds:
        result = client.table("feeds").select("id").eq("url", feed_config.url).execute()
        existing_rows = cast(list[dict[str, Any]], result.data)

        if existing_rows:
            logger.debug(
                "Feed already exists: %s (%s)", feed_config.name, feed_config.url
            )
            continue

        client.table("feeds").insert(
            {"name": feed_config.name, "url": feed_config.url}
        ).execute()
        logger.info("Seeded feed: %s (%s)", feed_config.name, feed_config.url)
