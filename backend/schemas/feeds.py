"""Feed schemas."""

from datetime import datetime

from pydantic import BaseModel


class FeedCreate(BaseModel):
    """Request body for creating a new feed."""

    name: str
    url: str


class FeedUpdate(BaseModel):
    """Request body for toggling a feed's active status."""

    is_active: bool


class FeedResponse(BaseModel):
    """Feed returned by the API."""

    id: int
    name: str
    url: str
    is_active: bool
    last_fetched_at: datetime | None = None
    created_at: datetime
