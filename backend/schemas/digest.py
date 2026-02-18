"""Digest response schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class DigestSectionResponse(BaseModel):
    """Single thematic section within a digest."""

    theme: str
    title: str
    body: str
    article_ids: list[int]


class DigestContentResponse(BaseModel):
    """Structured digest content."""

    headline: str
    sections: list[DigestSectionResponse]
    key_takeaways: list[str]
    connections: str


class DigestResponse(BaseModel):
    """Full digest API response."""

    id: int
    digest_date: date
    content: DigestContentResponse
    article_ids: list[int]
    article_count: int
    created_at: datetime
    updated_at: datetime
