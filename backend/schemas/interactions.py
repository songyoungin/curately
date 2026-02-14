"""Interaction schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InteractionResponse(BaseModel):
    """Interaction state returned after a toggle."""

    article_id: int
    type: Literal["like", "bookmark"]
    active: bool
    created_at: datetime | None = None
