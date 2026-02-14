"""Article route handlers."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/articles", tags=["articles"])
