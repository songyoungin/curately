"""Interest profile schemas."""

from datetime import datetime

from pydantic import BaseModel


class UserInterestResponse(BaseModel):
    """Single interest keyword with its weight."""

    id: int
    keyword: str
    weight: float
    source: str | None = None
    updated_at: datetime
