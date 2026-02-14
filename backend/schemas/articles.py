"""Article schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class ArticleListItem(BaseModel):
    """Article summary for list views (Today page, Archive)."""

    id: int
    source_feed: str
    source_url: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    summary: str | None = None
    relevance_score: float | None = None
    categories: list[str] = []
    keywords: list[str] = []
    newsletter_date: date | None = None
    is_liked: bool = False
    is_bookmarked: bool = False


class ArticleDetail(BaseModel):
    """Full article detail including detailed summary."""

    id: int
    source_feed: str
    source_url: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    raw_content: str | None = None
    summary: str | None = None
    detailed_summary: str | None = None
    relevance_score: float | None = None
    categories: list[str] = []
    keywords: list[str] = []
    newsletter_date: date | None = None
    is_liked: bool = False
    is_bookmarked: bool = False
    created_at: datetime
    updated_at: datetime


class NewsletterResponse(BaseModel):
    """Newsletter edition with its articles."""

    date: date
    article_count: int
    articles: list[ArticleListItem] = []


class NewsletterListItem(BaseModel):
    """Newsletter edition summary for the list endpoint."""

    date: date
    article_count: int
