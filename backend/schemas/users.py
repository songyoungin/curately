"""User schemas."""

from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    """User profile returned by the API."""

    id: int
    email: str
    name: str | None = None
    picture_url: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None
