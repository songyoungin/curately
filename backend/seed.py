"""Feed seeding logic."""

import logging
from typing import Any, cast

from supabase import Client

from backend.config import get_settings

logger = logging.getLogger(__name__)


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
