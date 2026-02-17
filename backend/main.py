"""Curately FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    articles,
    auth,
    feeds,
    interests,
    newsletters,
    pipeline,
    rewind,
)
from backend.scheduler import start_scheduler, stop_scheduler
from backend.seed import seed_default_feeds
from backend.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    try:
        client = get_supabase_client()
        await seed_default_feeds(client)
    except Exception:
        logger.warning("Seeding skipped (DB not available)")

    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Curately",
        description="AI-curated personal tech newsletter",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(newsletters.router)
    app.include_router(articles.router)
    app.include_router(feeds.router)
    app.include_router(interests.router)
    app.include_router(rewind.router)
    app.include_router(pipeline.router)

    return app


app = create_app()


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Return application health status."""
    return {"status": "ok"}
