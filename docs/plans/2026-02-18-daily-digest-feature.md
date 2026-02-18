# Daily Digest Feature Design Document

> **Date**: 2026-02-18
> **Status**: Draft
> **Author**: AI-assisted

## 1. Overview

### Concept

Daily Digest is a synthesized one-page briefing generated from each day's curated articles. While the existing Today page shows individual article cards with per-article summaries, the Digest page provides a **holistic narrative** — a single, readable document that answers: *"What do I absolutely need to know today?"*

Think of it as the difference between browsing headlines (Today page) and reading an executive briefing (Digest page).

### Value Proposition

| Aspect | Today Page (existing) | Digest Page (new) |
|--------|----------------------|-------------------|
| Format | Individual article cards | Single narrative document |
| Content | Per-article 2-3 sentence summaries | Cross-article synthesized briefing |
| Use case | Browse & interact with articles | Quick 2-minute daily read |
| Interaction | Like, bookmark individual articles | Read-only (links back to Today page) |

### Key Design Decisions

1. **Digest is derived from the daily newsletter articles** — it uses the same filtered & scored articles (top 20, relevance >= 0.3) that already exist in the `articles` table with a given `newsletter_date`.
2. **Generated after the daily pipeline** — digest generation runs as Stage 7 of the existing pipeline, after articles are persisted.
3. **Cached in the database** — each digest is generated once and stored; subsequent reads are cheap DB lookups.
4. **One digest per date** — like newsletters, digests are keyed by date. No per-user digest (articles are shared).
5. **Date navigation** — Digest page supports left/right arrow buttons for browsing past digests.
6. **Article linking via Today page filter** — Each digest section links to the Today page with `?articles=` query parameter to show related articles.

---

## 2. Database Schema

### New Table: `digests`

```sql
-- File: docs/migrations/001_create_digests_table.sql
-- Run via Supabase SQL Editor (Dashboard > SQL Editor > New query)

CREATE TABLE digests (
    id              BIGSERIAL PRIMARY KEY,
    digest_date     DATE UNIQUE NOT NULL,
    content         JSONB NOT NULL,
    article_ids     JSONB DEFAULT '[]',
    article_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_digests_date ON digests(digest_date DESC);
```

**Migration instructions**: This project does not use a migration framework. Copy the SQL above into Supabase Dashboard > SQL Editor and execute. The same SQL is also saved at `docs/migrations/001_create_digests_table.sql` for reference.

### `content` JSONB Structure

```json
{
  "headline": "AI 에이전트가 개발 워크플로를 재편하는 가운데 클라우드 비용 급증",
  "sections": [
    {
      "theme": "AI/ML",
      "title": "AI 에이전트, 새로운 개발 도구의 표준으로 부상",
      "body": "오늘의 주요 기사들은 AI 기반 개발 도구의 급격한 성장을 조명합니다. GPT-5 출시 임박 소식과 함께 AI 에이전트의 도구 사용 패턴에 대한 실전 아키텍처가 공유되었으며, LLM 파인튜닝의 접근성도 크게 향상되고 있습니다. 특히 코드 생성과 추론 능력의 비약적 발전이 개발자 생산성에 직접적인 영향을 미칠 것으로 보입니다.",
      "article_ids": [1, 2, 3]
    },
    {
      "theme": "DevOps",
      "title": "Kubernetes 생태계 진화와 IaC 도구 경쟁 심화",
      "body": "Kubernetes 1.33 출시로 사이드카 컨테이너 네이티브 지원이 드디어 실현되었으며, 메모리 사용량과 Pod 시작 시간이 크게 개선되었습니다. 동시에 Terraform과 Pulumi의 경쟁이 격화되면서 IaC 선택지가 다양해지고 있습니다.",
      "article_ids": [5, 6, 7]
    },
    {
      "theme": "Backend",
      "title": "데이터베이스 성능 혁신과 분산 시스템 설계",
      "body": "PostgreSQL 17의 병렬 쿼리 30% 향상과 JSONB 인덱싱 개선은 대규모 데이터 처리에 실질적인 도움이 됩니다. 분산 시스템에서의 Rate Limiter 설계에 대한 심층 분석도 주목할 만합니다.",
      "article_ids": [8, 9]
    }
  ],
  "key_takeaways": [
    "GPT-5 출시가 임박하면서 멀티모달 기능과 코드 생성 능력이 크게 향상될 전망 — API 가격은 40% 인하 예정",
    "AI 에이전트의 프로덕션 적용이 가속화되고 있으며, ReAct + 함수 호출 조합 아키텍처가 가장 높은 성공률을 기록",
    "Kubernetes 1.33의 사이드카 네이티브 지원으로 컨테이너 오케스트레이션의 오랜 숙원이 해결",
    "PostgreSQL 17의 성능 개선이 실무에 즉시 적용 가능한 수준으로 발표"
  ],
  "connections": "AI와 인프라 주제가 깊이 연결되어 있습니다. AI 워크로드 증가(AI/ML 섹션)가 클라우드 인프라 수요를 직접적으로 끌어올리고 있으며, Kubernetes의 성능 개선(DevOps 섹션)은 이러한 AI 워크로드를 효율적으로 처리하기 위한 필수 요소입니다. 또한 PostgreSQL의 JSONB 성능 향상(Backend 섹션)은 AI 메타데이터와 벡터 스토어 관리에 직접적인 이점을 제공합니다."
}
```

**Field descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `headline` | `string` | Single-sentence headline capturing the day's dominant narrative (max ~100 chars, Korean) |
| `sections` | `array` | 2-5 thematic sections, each synthesizing related articles into a cohesive paragraph |
| `sections[].theme` | `string` | Category label matching existing article categories (e.g., "AI/ML", "DevOps") |
| `sections[].title` | `string` | Section heading (one line, Korean) |
| `sections[].body` | `string` | 3-5 sentence synthesis (NOT a concatenation of summaries — a narrative, Korean) |
| `sections[].article_ids` | `array<int>` | **Gemini returns 1-based indices; service maps these to real DB article IDs before persisting** |
| `key_takeaways` | `array<string>` | 3-5 bullet points — the "if you read nothing else" items (Korean) |
| `connections` | `string` | 2-3 sentences identifying cross-theme patterns and relationships (Korean) |

---

## 3. Prerequisite: Shared Gemini Utility

### 3.0 New Module: `backend/services/gemini.py`

Currently, `_call_gemini_with_retry` is duplicated in both `summarizer.py` (sync client) and `rewind.py` (async client). Extract the async version into a shared module.

**Create `backend/services/gemini.py`:**

```python
"""Shared Gemini API utilities.

Provides a common async retry wrapper and client factory used
by digest, rewind, and other services that call Gemini.
"""

from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_RETRY_DELAY = 1.0


def create_gemini_client(settings: Settings | None = None) -> genai.Client:
    """Create a Gemini client from application settings."""
    if settings is None:
        settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


async def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
    config: types.GenerateContentConfig | None = None,
) -> str:
    """Call the Gemini API (async) with exponential backoff retry.

    Uses client.aio.models.generate_content for non-blocking calls.
    Retries up to 3 times with exponential backoff (1s, 2s, 4s).

    Args:
        client: Gemini API client.
        model: Model name (e.g., "gemini-2.5-flash").
        prompt: Prompt text.
        config: Generation config (e.g., JSON response mode).

    Returns:
        Gemini response text.

    Raises:
        Exception: Last exception when all retries are exhausted.
    """
    last_exception: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            last_exception = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _BASE_RETRY_DELAY * (2**attempt)
                logger.warning(
                    "Gemini API call failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Gemini API call failed after %d attempts: %s",
                    _MAX_RETRIES,
                    type(exc).__name__,
                )
    raise last_exception  # type: ignore[misc]
```

**Refactor `backend/services/rewind.py`:**
- Remove `_call_gemini_with_retry` and `_MAX_RETRIES` / `_BASE_RETRY_DELAY`
- Replace `from backend.services.scorer import create_gemini_client` with `from backend.services.gemini import call_gemini_with_retry, create_gemini_client`
- Update calls: `await _call_gemini_with_retry(gemini_client, ...)` → `await call_gemini_with_retry(gemini_client, ...)`

**Update `tests/test_rewind.py` after refactor:**
Existing rewind tests patch `backend.services.rewind.create_gemini_client` and `backend.services.rewind.asyncio.sleep`. After the refactor:
- `create_gemini_client` — still patched at `backend.services.rewind.create_gemini_client` (works because rewind.py imports the name)
- `asyncio.sleep` — must change to `backend.services.gemini.asyncio.sleep` (sleep is now called inside `gemini.py`, not `rewind.py`)

Specifically, update all `@patch("backend.services.rewind.asyncio.sleep", ...)` → `@patch("backend.services.gemini.asyncio.sleep", ...)` in `tests/test_rewind.py` (affects 3 tests: `test_generate_rewind_happy_path`, `test_generate_rewind_first_report`, `test_generate_rewind_gemini_failure`).

**Leave `backend/services/summarizer.py` as-is:** It uses the sync Gemini client (`client.models.generate_content`), which is a different pattern. Refactoring it is out of scope.

**Leave `backend/services/scorer.py` `create_gemini_client`:** Keep the original in scorer.py for backward compatibility, but new code should import from `gemini.py`. A re-export or deprecation can be done later.

---

## 4. Backend Design

### 4.1 Service: `backend/services/digest.py`

#### TypedDict Definitions

```python
class DigestSection(TypedDict):
    """Single thematic section within a digest."""
    theme: str
    title: str
    body: str
    article_ids: list[int]


class DigestContent(TypedDict):
    """Full structured digest content returned by Gemini."""
    headline: str
    sections: list[DigestSection]
    key_takeaways: list[str]
    connections: str
```

#### Fallback Constant

```python
_NO_ARTICLES_DIGEST = DigestContent(
    headline="",
    sections=[],
    key_takeaways=[],
    connections="",
)
```

#### Core Function: `generate_daily_digest` (complete implementation)

```python
async def generate_daily_digest(
    client: Client,
    digest_date: str,
    settings: Settings | None = None,
) -> tuple[DigestContent, list[int]]:
    """Generate a synthesized daily digest from the day's newsletter articles.

    Args:
        client: Supabase client instance.
        digest_date: ISO date string (e.g., "2026-02-18").
        settings: Application settings. Uses defaults if None.

    Returns:
        Tuple of (DigestContent, list of all article IDs used).
    """
    if settings is None:
        settings = get_settings()

    # Step 1: Fetch articles for the date
    result = (
        client.table("articles")
        .select("id, title, summary, categories, keywords, relevance_score, source_url")
        .eq("newsletter_date", digest_date)
        .order("relevance_score", desc=True)
        .execute()
    )
    articles = cast(list[dict[str, Any]], result.data)

    # Step 2: Early return if no articles
    if not articles:
        logger.info("No articles found for %s, returning empty digest", digest_date)
        return _NO_ARTICLES_DIGEST, []

    logger.info(
        "Generating digest for %s with %d article(s)", digest_date, len(articles)
    )

    # Step 3: Build index-to-ID map (prompt uses 1-based indices)
    index_to_id: dict[int, int] = {}
    for i, article in enumerate(articles):
        index_to_id[i + 1] = article["id"]
    all_article_ids = [article["id"] for article in articles]

    # Step 4: Build prompt
    prompt = _build_digest_prompt(articles)

    # Step 5: Call Gemini with JSON response mode
    gemini_client = create_gemini_client(settings)
    try:
        response_text = await call_gemini_with_retry(
            gemini_client,
            settings.gemini.model,
            prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        digest = _parse_digest_response(response_text)
    except Exception:
        logger.exception("Gemini digest generation failed for %s", digest_date)
        return _NO_ARTICLES_DIGEST, all_article_ids

    # Step 6: Map Gemini's 1-based indices back to real DB IDs
    for section in digest["sections"]:
        section["article_ids"] = [
            index_to_id[idx]
            for idx in section["article_ids"]
            if idx in index_to_id  # Guard against out-of-range indices
        ]

    return digest, all_article_ids
```

#### Gemini Prompt: `_build_digest_prompt`

```python
_DIGEST_PROMPT = """\
You are a senior tech editor writing a daily briefing for a Korean tech professional.
You are given today's {article_count} curated articles, ranked by personal relevance score.

## Today's Articles

{articles_section}

## Instructions

Write a daily digest that SYNTHESIZES these articles into a cohesive briefing.
DO NOT simply restate each article's summary. Instead:
- Identify 2-5 common themes across articles
- Group related articles into thematic sections
- Draw connections between articles within each theme
- Tell a story about what matters today

Output a JSON object with these fields:

1. "headline": A single compelling sentence capturing today's dominant narrative.
   - Max 100 characters. Write in Korean.

2. "sections": An array of 2-5 thematic sections. Each section:
   - "theme": Category label (e.g., "AI/ML", "DevOps", "Backend")
   - "title": One-line section heading in Korean
   - "body": 3-5 sentence narrative synthesis in Korean (NOT a list of per-article summaries)
   - "article_ids": List of article index numbers (1-based) covered in this section

3. "key_takeaways": An array of 3-5 bullet points in Korean. These are the
   "if you read nothing else" items. Each should be a complete, standalone sentence.

4. "connections": 2-3 sentences in Korean identifying cross-theme patterns
   and relationships between the sections.

IMPORTANT:
- article_ids must use the index numbers [1], [2], etc. from the article list above.
- Every article should appear in at least one section.
- Write entirely in Korean except for technical terms.
- Be insightful, not repetitive.

Respond ONLY with the JSON object."""


def _build_digest_prompt(articles: list[dict[str, Any]]) -> str:
    """Build the Gemini prompt for digest generation.

    Args:
        articles: Articles with id, title, summary, categories, keywords,
                  relevance_score, ordered by relevance_score DESC.

    Returns:
        Formatted prompt string.
    """
    article_lines = []
    for i, article in enumerate(articles):
        title = article.get("title", "Untitled")
        summary = article.get("summary") or "(no summary)"
        score = article.get("relevance_score", 0.0)
        categories = article.get("categories") or []
        keywords = article.get("keywords") or []
        article_lines.append(
            f"[{i + 1}] (relevance: {score:.2f}) \"{title}\"\n"
            f"    Summary: {summary}\n"
            f"    Categories: {', '.join(categories) if categories else 'N/A'}\n"
            f"    Keywords: {', '.join(keywords) if keywords else 'N/A'}"
        )
    articles_section = "\n\n".join(article_lines)

    return _DIGEST_PROMPT.format(
        article_count=len(articles),
        articles_section=articles_section,
    )
```

#### Response Parser: `_parse_digest_response`

```python
def _parse_digest_response(text: str) -> DigestContent:
    """Parse Gemini response text into DigestContent.

    Handles missing/malformed fields gracefully with safe defaults.

    Args:
        text: JSON string returned by Gemini.

    Returns:
        Parsed DigestContent. Returns _NO_ARTICLES_DIGEST on complete parse failure.
    """
    try:
        data: dict[str, Any] = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse digest response JSON, using fallback")
        return _NO_ARTICLES_DIGEST

    # headline
    headline = data.get("headline")
    if not isinstance(headline, str):
        headline = ""

    # sections
    raw_sections = data.get("sections")
    sections: list[DigestSection] = []
    if isinstance(raw_sections, list):
        for s in raw_sections:
            if not isinstance(s, dict):
                continue
            sections.append(DigestSection(
                theme=str(s.get("theme", "")),
                title=str(s.get("title", "")),
                body=str(s.get("body", "")),
                article_ids=[
                    int(aid) for aid in (s.get("article_ids") or [])
                    if isinstance(aid, (int, float))
                ],
            ))

    # key_takeaways
    raw_takeaways = data.get("key_takeaways")
    key_takeaways: list[str] = []
    if isinstance(raw_takeaways, list):
        key_takeaways = [str(t) for t in raw_takeaways]

    # connections
    connections = data.get("connections")
    if not isinstance(connections, str):
        connections = ""

    return DigestContent(
        headline=headline,
        sections=sections,
        key_takeaways=key_takeaways,
        connections=connections,
    )
```

#### Persist Function: `persist_digest`

```python
async def persist_digest(
    client: Client,
    digest_date: str,
    content: DigestContent,
    article_ids: list[int],
) -> int:
    """Upsert a digest into the database.

    If a digest already exists for the given date, it is REPLACED (upsert).
    This enables regeneration via the manual generate endpoint.

    Args:
        client: Supabase client instance.
        digest_date: ISO date string.
        content: Structured digest content.
        article_ids: List of all article IDs used.

    Returns:
        ID of the upserted digest row.
    """
    row: dict[str, Any] = {
        "digest_date": digest_date,
        "content": dict(content),
        "article_ids": article_ids,
        "article_count": len(article_ids),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = (
        client.table("digests")
        .upsert(row, on_conflict="digest_date")
        .execute()
    )
    inserted = cast(list[dict[str, Any]], result.data)
    digest_id: int = inserted[0]["id"]
    logger.info("Persisted digest %d for date %s (%d articles)", digest_id, digest_date, len(article_ids))
    return digest_id
```

**Note on `updated_at`**: On INSERT, the DB default `NOW()` applies. On UPDATE (regeneration), the explicit `datetime.now(timezone.utc).isoformat()` value tracks when the digest was regenerated. Do NOT use `"now()"` string — the Supabase Python client stores it as a literal string, not a SQL function.

#### Full Module Imports

```python
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict, cast

from google.genai import types
from supabase import Client

from backend.config import Settings, get_settings
from backend.services.gemini import call_gemini_with_retry, create_gemini_client

logger = logging.getLogger(__name__)
```

### 4.2 Pipeline Integration: `backend/services/pipeline.py`

Add Stage 7 **after** Stage 6 (`_persist_articles`). At this point, articles are already in the DB with real IDs.

```python
# At top of file, add import:
from backend.services.digest import generate_daily_digest, persist_digest

# After Stage 6 (line ~163, after "Persisted %d article(s)..." log):

# Stage 7: Generate daily digest
logger.info("Stage 7/7: Generating daily digest")
digest_generated = False
try:
    digest_content, digest_article_ids = await generate_daily_digest(
        client, today, settings
    )
    if digest_content["headline"]:  # Non-empty digest
        await persist_digest(client, today, digest_content, digest_article_ids)
        digest_generated = True
        logger.info("Daily digest generated for %s", today)
    else:
        logger.info("Empty digest (no headline), skipping persist")
except Exception:
    logger.warning("Digest generation failed, pipeline continues without digest")
```

**How `article_ids` is obtained**: The digest service internally queries `articles WHERE newsletter_date = today` to get the full article list with IDs. The pipeline does NOT need to pass article IDs to the service — the service fetches them from the DB. This is why `generate_daily_digest` takes `digest_date` (not articles).

**Update `PipelineResult`:**

```python
class PipelineResult(TypedDict):
    articles_collected: int
    articles_scored: int
    articles_filtered: int
    articles_summarized: int
    newsletter_date: str
    digest_generated: bool  # NEW
```

Update the result construction at the end:

```python
result = PipelineResult(
    articles_collected=len(articles),
    articles_scored=articles_scored,
    articles_filtered=len(filtered),
    articles_summarized=summarized_count,
    newsletter_date=today,
    digest_generated=digest_generated,  # NEW
)
```

Also update the early-return `PipelineResult` (when no articles collected) to include `digest_generated=False`.

### 4.3 Schema: `backend/schemas/digest.py`

```python
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
    """Full digest API response.

    The `content` field is stored as JSONB in the DB.
    Pydantic auto-validates the nested structure when the dict
    is returned from the router.
    """

    id: int
    digest_date: date
    content: DigestContentResponse
    article_ids: list[int]
    article_count: int
    created_at: datetime
    updated_at: datetime
```

**JSONB-to-Pydantic note**: The router returns `dict[str, Any]` from Supabase. FastAPI + Pydantic auto-coerce the `content` JSONB dict into `DigestContentResponse` via the `response_model`. No manual parsing needed — same pattern as `RewindReportResponse` which has `report_content: dict[str, Any]`.

### 4.4 Router: `backend/routers/digest.py`

```python
"""Daily digest route handlers."""

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth import get_current_user_id
from backend.schemas.digest import DigestResponse
from backend.services.digest import generate_daily_digest, persist_digest
from backend.supabase_client import get_supabase_client
from backend.time_utils import today_kst

router = APIRouter(prefix="/api/digests", tags=["digests"])
```

**Authentication**: All endpoints require `get_current_user_id` for access control consistency with the rest of the API. The `user_id` is not used for data filtering since digests are shared.

**Date convention**: All "today" references use `today_kst()` from `backend.time_utils`, which returns `datetime.now(tz=ZoneInfo("Asia/Seoul")).date()`. This matches the project-wide convention used in `pipeline.py`, `newsletters.py`, `rewind.py`, and `scheduler.py`.

#### `GET /api/digests/today`

```python
@router.get("/today", response_model=DigestResponse)
async def get_today_digest(
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return today's digest.

    Raises:
        HTTPException: 404 if no digest exists for today.
    """
    client = get_supabase_client()
    today = today_kst().isoformat()

    result = (
        client.table("digests")
        .select("*")
        .eq("digest_date", today)
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No digest found for today",
        )
    return rows[0]
```

#### `GET /api/digests/{date}`

```python
@router.get("/{digest_date}", response_model=DigestResponse)
async def get_digest_by_date(
    digest_date: date,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Return a specific date's digest.

    Args:
        digest_date: Date in YYYY-MM-DD format.

    Raises:
        HTTPException: 404 if no digest exists for the given date.
    """
    client = get_supabase_client()

    result = (
        client.table("digests")
        .select("*")
        .eq("digest_date", digest_date.isoformat())
        .execute()
    )
    rows = cast(list[dict[str, Any]], result.data)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No digest found for {digest_date}",
        )
    return rows[0]
```

#### `GET /api/digests`

```python
@router.get("", response_model=list[DigestResponse])
async def list_digests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """List all digests, newest first, with pagination.

    Args:
        limit: Max items per page (default 20, max 100).
        offset: Number of items to skip.
    """
    client = get_supabase_client()

    result = (
        client.table("digests")
        .select("*")
        .order("digest_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return cast(list[dict[str, Any]], result.data)
```

#### `POST /api/digests/generate`

```python
@router.post("/generate", response_model=DigestResponse, status_code=201)
async def generate_digest(
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate (or regenerate) today's digest.

    If a digest already exists for today, it is replaced via upsert.

    Returns:
        The newly created/updated digest.

    Raises:
        HTTPException: 404 if no articles exist for today's newsletter_date.
    """
    client = get_supabase_client()
    today = today_kst().isoformat()

    # Verify articles exist for today
    count_result = (
        client.table("articles")
        .select("id", count="exact")
        .eq("newsletter_date", today)
        .execute()
    )
    if not count_result.count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No articles found for {today}, cannot generate digest",
        )

    content, article_ids = await generate_daily_digest(client, today)

    # Empty digest = Gemini failure (articles exist but generation failed)
    if not content["headline"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Digest generation failed (LLM returned empty result)",
        )

    digest_id = await persist_digest(client, today, content, article_ids)

    # Return the persisted row
    result = client.table("digests").select("*").eq("id", digest_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    return rows[0]
```

#### `POST /api/digests/generate/{date}`

```python
@router.post("/generate/{digest_date}", response_model=DigestResponse, status_code=201)
async def generate_digest_for_date(
    digest_date: date,
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Generate (or regenerate) a digest for a specific date.

    Enables backfilling digests for dates before this feature was added.

    Args:
        digest_date: Date in YYYY-MM-DD format.

    Raises:
        HTTPException: 404 if no articles exist for the given newsletter_date.
        HTTPException: 502 if LLM generation fails (returns empty result).
    """
    client = get_supabase_client()
    date_str = digest_date.isoformat()

    count_result = (
        client.table("articles")
        .select("id", count="exact")
        .eq("newsletter_date", date_str)
        .execute()
    )
    if not count_result.count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No articles found for {date_str}, cannot generate digest",
        )

    content, article_ids = await generate_daily_digest(client, date_str)

    if not content["headline"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Digest generation failed (LLM returned empty result)",
        )

    digest_id = await persist_digest(client, date_str, content, article_ids)

    result = client.table("digests").select("*").eq("id", digest_id).execute()
    rows = cast(list[dict[str, Any]], result.data)
    return rows[0]
```

### 4.5 Registration: `backend/main.py`

Add to imports:

```python
from backend.routers import (
    articles,
    auth,
    digest,   # NEW
    feeds,
    interests,
    newsletters,
    pipeline,
    rewind,
)
```

Add router registration (after rewind, before pipeline):

```python
app.include_router(digest.router)   # NEW
```

### 4.6 Scheduler

No new scheduler job needed. Digest generation is part of the daily pipeline (Stage 7).

### 4.7 Date Convention: `today_kst()` (Asia/Seoul)

The project uses `backend.time_utils.today_kst()` for all "today" date references. This function returns `datetime.now(tz=ZoneInfo("Asia/Seoul")).date()`, ensuring the correct KST date regardless of server timezone.

**For the digest feature, ALL "today" references MUST use `today_kst()`:**

| Component | Date reference | Source |
|-----------|---------------|--------|
| `pipeline.py` Stage 7 | `today` variable (already `today_kst()` from line 59) | Same variable, no change |
| `routers/digest.py` GET /today | `today_kst().isoformat()` | Import from `backend.time_utils` |
| `routers/digest.py` POST /generate | `today_kst().isoformat()` | Import from `backend.time_utils` |
| Frontend `Digest.tsx` | `new Date().toISOString().split('T')[0]` | Browser local (UTC-based, existing pattern) |

**Frontend note**: `new Date().toISOString().split('T')[0]` returns UTC date, which could differ from KST near midnight. This is an existing limitation shared by all pages (Today, Archive). A full fix would require a timezone-aware date API, which is out of scope.

---

## 5. Frontend Design

### 5.1 TypeScript Types: `frontend/src/types/digest.ts`

```typescript
export interface DigestSection {
  theme: string;
  title: string;
  body: string;
  article_ids: number[];
}

export interface DigestContent {
  headline: string;
  sections: DigestSection[];
  key_takeaways: string[];
  connections: string;
}

export interface Digest {
  id: number;
  digest_date: string;
  content: DigestContent;
  article_ids: number[];
  article_count: number;
  created_at: string;
  updated_at: string;
}
```

**Update `frontend/src/types/index.ts`** — add export:

```typescript
export type { Digest, DigestContent, DigestSection } from './digest';
```

### 5.2 API Client: `frontend/src/api/client.ts`

Add import of `Digest` type and new API group:

```typescript
import type {
  // ... existing imports ...
  Digest,          // NEW
} from '../types';

// Digests (NEW)
export const digestApi = {
  getToday: () => api.get<Digest>('/digests/today'),
  getByDate: (date: string) => api.get<Digest>(`/digests/${date}`),
  list: () => api.get<Digest[]>('/digests'),
  generate: () => api.post<Digest>('/digests/generate'),
  generateForDate: (date: string) => api.post<Digest>(`/digests/generate/${date}`),
};
```

### 5.3 Hook: `frontend/src/hooks/useDigest.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';

import type { Digest } from '../types';
import { digestApi } from '../api/client';

interface UseDigestReturn {
  digest: Digest | null;
  loading: boolean;
  generating: boolean;
  error: string | null;
  notFound: boolean;       // true when 404 (digest not yet generated)
  refetch: () => void;
  generate: () => Promise<void>;
}

export function useDigest(date?: string): UseDigestReturn {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const fetchDigest = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const response = date
        ? await digestApi.getByDate(date)
        : await digestApi.getToday();
      setDigest(response.data);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        // Not an error — digest just hasn't been generated yet
        setNotFound(true);
        setDigest(null);
      } else {
        const message =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ??
          (err instanceof Error ? err.message : 'Failed to load digest');
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    fetchDigest();
  }, [fetchDigest]);

  const generate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = date
        ? await digestApi.generateForDate(date)
        : await digestApi.generate();
      setDigest(response.data);
      setNotFound(false);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to generate digest');
      setError(message);
    } finally {
      setGenerating(false);
    }
  }, [date]);

  return {
    digest,
    loading,
    generating,
    error,
    notFound,
    refetch: fetchDigest,
    generate,
  };
}
```

**Key difference from useRewind**: The `notFound` state handles 404 as a normal condition (digest not yet generated), not as an error. This drives the EmptyState with "Generate" button in the UI.

**Update `frontend/src/hooks/index.ts`** — add export:

```typescript
export { useDigest } from './useDigest';
```

### 5.4 Page: `frontend/src/pages/Digest.tsx`

```typescript
import { useState } from 'react';
import { FileText, ChevronLeft, ChevronRight, RotateCw } from 'lucide-react';

import DigestView from '../components/DigestView';
import { EmptyState, ErrorDisplay } from '../components/common';
import { DigestSkeleton } from '../components/common';
import { useDigest } from '../hooks';

/**
 * Shift a YYYY-MM-DD date string by the given number of days.
 * Returns a new YYYY-MM-DD string.
 */
function shiftDate(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

/** Format YYYY-MM-DD as a human-readable date (e.g., "February 18, 2026"). */
function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export default function Digest() {
  const today = new Date().toISOString().split('T')[0];
  const [selectedDate, setSelectedDate] = useState<string>(today);
  const isToday = selectedDate === today;

  // When selectedDate === today, pass undefined to use the /today endpoint
  const { digest, loading, generating, error, notFound, refetch, generate } =
    useDigest(isToday ? undefined : selectedDate);

  const goToPreviousDay = () => setSelectedDate(shiftDate(selectedDate, -1));
  const goToNextDay = () => {
    const next = shiftDate(selectedDate, 1);
    if (next <= today) setSelectedDate(next);
  };

  if (loading) {
    return <DigestSkeleton />;
  }

  if (error && !digest) {
    return <ErrorDisplay message={error} onRetry={refetch} />;
  }

  if (notFound || !digest) {
    return (
      <div>
        {/* Date navigation even when no digest */}
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-gray-200">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Daily Digest</h1>
            <div className="flex items-center gap-2 mt-1">
              <button onClick={goToPreviousDay} className="p-1 rounded hover:bg-gray-100" aria-label="Previous day">
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm text-gray-600">{formatDate(selectedDate)}</span>
              <button onClick={goToNextDay} disabled={isToday} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" aria-label="Next day">
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </header>
        <div className="mt-6">
          <EmptyState
            title="No digest yet"
            description={`Digest for ${formatDate(selectedDate)} hasn't been generated yet.`}
            icon={<FileText className="w-12 h-12" />}
            actionLabel={generating ? 'Generating...' : 'Generate Digest'}
            onAction={() => void generate()}
          />
        </div>
      </div>
    );
  }

  return (
    <div>
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily Digest</h1>
          <div className="flex items-center gap-2 mt-1">
            <button onClick={goToPreviousDay} className="p-1 rounded hover:bg-gray-100 transition-colors" aria-label="Previous day">
              <ChevronLeft size={16} />
            </button>
            <span className="text-sm text-gray-600">
              {formatDate(selectedDate)} · {digest.article_count} articles
            </span>
            <button onClick={goToNextDay} disabled={isToday} className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition-colors" aria-label="Next day">
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void generate()}
          disabled={generating}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
          aria-label="Regenerate digest"
        >
          <RotateCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} aria-hidden="true" />
          {generating ? 'Generating...' : 'Regenerate'}
        </button>
      </header>

      {error && <div className="mt-4"><ErrorDisplay message={error} onRetry={refetch} /></div>}

      <div className="mt-6">
        <DigestView digest={digest} />
      </div>
    </div>
  );
}
```

### 5.5 Component: `frontend/src/components/DigestView.tsx`

Single file containing all digest sub-components. Follows the existing pattern where `RewindReport.tsx` is self-contained.

```typescript
import { Link } from 'react-router-dom';
import { Lightbulb, Link2, Layers } from 'lucide-react';

import type { Digest, DigestSection as DigestSectionType } from '../types';

interface DigestViewProps {
  digest: Digest;
}

export default function DigestView({ digest }: DigestViewProps) {
  const { content } = digest;

  return (
    <div className="space-y-6">
      {/* Headline */}
      {content.headline && (
        <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-5 sm:p-6">
          <p className="text-lg sm:text-xl font-semibold text-indigo-900 leading-relaxed">
            {content.headline}
          </p>
        </div>
      )}

      {/* Key Takeaways */}
      {content.key_takeaways.length > 0 && (
        <section className="rounded-xl bg-amber-50 border border-amber-100 p-4 sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-amber-900">
            <Lightbulb className="w-4 h-4" />
            Key Takeaways
          </h2>
          <ul className="mt-3 space-y-2">
            {content.key_takeaways.map((item, i) => (
              <li key={i} className="flex gap-2 text-sm text-amber-800">
                <span className="mt-1 block w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Thematic Sections */}
      {content.sections.map((section, i) => (
        <DigestSectionCard key={i} section={section} />
      ))}

      {/* Connections */}
      {content.connections && (
        <section className="rounded-xl bg-gray-50 border border-gray-200 p-4 sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900">
            <Layers className="w-4 h-4 text-gray-600" />
            Connections
          </h2>
          <p className="mt-3 text-sm text-gray-700 leading-relaxed">
            {content.connections}
          </p>
        </section>
      )}
    </div>
  );
}


function DigestSectionCard({ section }: { section: DigestSectionType }) {
  // Build the Today page link with article filter
  const articleParam = section.article_ids.join(',');
  const todayLink = `/?articles=${articleParam}`;

  return (
    <section className="rounded-xl bg-white border border-gray-200 p-4 sm:p-5">
      {/* Theme badge + title */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
            {section.theme}
          </span>
          <h3 className="mt-2 text-base font-semibold text-gray-900">
            {section.title}
          </h3>
        </div>
      </div>

      {/* Body */}
      <p className="mt-3 text-sm text-gray-700 leading-relaxed">
        {section.body}
      </p>

      {/* Article link */}
      {section.article_ids.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <Link
            to={todayLink}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
          >
            <Link2 className="w-3 h-3" />
            {section.article_ids.length} article{section.article_ids.length > 1 ? 's' : ''} →
          </Link>
        </div>
      )}
    </section>
  );
}
```

### 5.6 Skeleton: `frontend/src/components/common/Skeleton.tsx`

Add `DigestSkeleton` to the existing `Skeleton.tsx` file (which already exports `RewindSkeleton`, etc.):

```typescript
export function DigestSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="pb-4 border-b border-gray-200">
        <div className="h-7 w-36 rounded bg-gray-200" />
        <div className="h-4 w-48 rounded bg-gray-200 mt-2" />
      </div>
      {/* Headline skeleton */}
      <div className="rounded-xl bg-gray-100 p-6">
        <div className="h-6 w-3/4 rounded bg-gray-200" />
      </div>
      {/* Takeaways skeleton */}
      <div className="rounded-xl bg-gray-100 p-5 space-y-2">
        <div className="h-4 w-24 rounded bg-gray-200" />
        <div className="h-3 w-full rounded bg-gray-200" />
        <div className="h-3 w-5/6 rounded bg-gray-200" />
        <div className="h-3 w-4/6 rounded bg-gray-200" />
      </div>
      {/* Section skeletons (x3) */}
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-xl bg-gray-100 p-5 space-y-3">
          <div className="h-4 w-16 rounded-full bg-gray-200" />
          <div className="h-5 w-2/3 rounded bg-gray-200" />
          <div className="h-3 w-full rounded bg-gray-200" />
          <div className="h-3 w-full rounded bg-gray-200" />
          <div className="h-3 w-3/4 rounded bg-gray-200" />
        </div>
      ))}
    </div>
  );
}
```

**Update `frontend/src/components/common/index.ts`** — add export:

```typescript
export {
  // ... existing exports ...
  DigestSkeleton,     // NEW
} from './Skeleton';
```

### 5.7 Router & NavBar Updates

**`frontend/src/App.tsx`** — add route:

```typescript
import Digest from './pages/Digest'   // NEW import

// Inside Routes, after "/" and before "/archive":
<Route path="/digest" element={<Digest />} />
```

**`frontend/src/components/NavBar.tsx`** — add nav item:

```typescript
import {
  // ... existing imports ...
  FileText,    // NEW
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Today', icon: Newspaper },
  { to: '/digest', label: 'Digest', icon: FileText },    // NEW
  { to: '/archive', label: 'Archive', icon: Archive },
  { to: '/bookmarks', label: 'Bookmarks', icon: Bookmark },
  { to: '/rewind', label: 'Rewind', icon: TrendingUp },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const
```

### 5.8 Today Page Filter: `frontend/src/pages/Today.tsx`

Add `?articles=1,2,3` query parameter support to filter displayed articles.

**Current structure** (post-pull): Today.tsx renders a flat list of `ArticleCard` components sorted by `relevance_score` DESC. There is no `CategorySection` grouping — just a `sortedArticles.map()` loop.

**Changes to `Today.tsx`:**

1. Add `useSearchParams` import from `react-router-dom`
2. Add `X` icon import from `lucide-react`
3. Parse `?articles=` query param into an ID filter
4. Apply filter to `sortedArticles` before rendering
5. Show/hide filter banner

```typescript
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";          // ADD
import { Newspaper, X } from "lucide-react";                 // ADD X

// ... existing imports (DateHeader, ArticleCard, etc.) ...

export default function Today() {
  const [searchParams, setSearchParams] = useSearchParams();  // NEW
  const { newsletter, loading, error, refetch } = useNewsletter();
  const initialArticles = useMemo(
    () => newsletter?.articles ?? [],
    [newsletter],
  );
  const { articles, toggleLike, toggleBookmark } =
    useArticleInteractions(initialArticles);

  // NEW: Parse ?articles= query parameter
  const filterArticleIds = useMemo(() => {
    const param = searchParams.get('articles');
    if (!param) return null;
    return param.split(',').map(Number).filter((n) => !isNaN(n));
  }, [searchParams]);

  // CHANGED: Apply filter before sorting
  const filteredArticles = useMemo(() => {
    if (!filterArticleIds) return articles;
    return articles.filter((a) => filterArticleIds.includes(a.id));
  }, [articles, filterArticleIds]);

  const sortedArticles = useMemo(
    () =>
      [...filteredArticles].sort(                             // CHANGED: use filteredArticles
        (a, b) => (b.relevance_score ?? -1) - (a.relevance_score ?? -1),
      ),
    [filteredArticles],
  );

  const clearFilter = () => {                                 // NEW
    searchParams.delete('articles');
    setSearchParams(searchParams);
  };

  // ... loading / error / empty states remain unchanged ...

  return (
    <div>
      <header className="pb-4 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-gray-900">Today</h1>
        <p className="mt-1 text-sm text-gray-600">
          Your curated articles for today.
        </p>
      </header>

      {/* NEW: Filter banner (shown when ?articles= is active) */}
      {filterArticleIds && (
        <div className="mt-4 flex items-center justify-between rounded-lg bg-indigo-50 border border-indigo-100 px-4 py-2">
          <span className="text-sm text-indigo-700">
            Showing {sortedArticles.length} article{sortedArticles.length !== 1 ? 's' : ''} from Digest
          </span>
          <button
            onClick={clearFilter}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
          >
            <X size={14} />
            Show all
          </button>
        </div>
      )}

      <div className="mt-6">
        <DateHeader date={newsletter.date} articleCount={sortedArticles.length} />
      </div>
      <div className="mt-6 space-y-4">
        {sortedArticles.map((article) => (
          <ArticleCard
            key={article.id}
            article={article}
            onLike={toggleLike}
            onBookmark={toggleBookmark}
          />
        ))}
      </div>
    </div>
  );
}
```

### 5.9 MSW Mock Data & Handlers

#### Mock Data: `frontend/src/mocks/data.ts`

Add at the end of the file, **after** `mockRewindReport`:

```typescript
import type { Digest } from '../types/digest';    // Add to imports at top

export const mockDigest: Digest = {
  id: 1,
  digest_date: '2026-02-16',
  content: {
    headline: 'AI 에이전트 혁신과 클라우드 인프라 진화가 개발 생태계를 재편',
    sections: [
      {
        theme: 'AI/ML',
        title: 'AI 에이전트와 LLM의 급격한 진화',
        body: 'GPT-5 출시가 임박한 가운데, 멀티모달 기능과 코드 생성 능력이 크게 향상될 전망입니다. AI 에이전트의 도구 사용 패턴이 프로덕션 환경에서 검증되고 있으며, ReAct 프레임워크와 함수 호출 조합이 가장 높은 성공률을 보이고 있습니다. LLM 파인튜닝의 접근성도 크게 향상되어 8GB VRAM GPU에서도 효과적인 학습이 가능해졌습니다.',
        article_ids: [1, 2, 3],
      },
      {
        theme: 'DevOps',
        title: 'Kubernetes 생태계 진화와 인프라 도구 경쟁',
        body: 'Kubernetes 1.33 출시로 사이드카 컨테이너 네이티브 지원이라는 오랜 숙원이 해결되었습니다. 메모리 사용량 15% 감소와 Pod 시작 시간 단축도 주목할 만합니다. IaC 영역에서는 Terraform과 Pulumi의 경쟁이 심화되고 있으며, GitOps 모범 사례도 성숙기에 접어들고 있습니다.',
        article_ids: [5, 6, 7],
      },
      {
        theme: 'Backend',
        title: '데이터베이스와 분산 시스템의 진보',
        body: 'PostgreSQL 17이 병렬 쿼리 실행 30% 향상과 JSONB 인덱싱 개선을 포함하여 출시되었습니다. 대규모 테이블의 VACUUM 효율성도 크게 개선되었으며, 분산 시스템에서의 Rate Limiter 설계에 대한 심층 분석도 실무에 바로 적용 가능한 수준입니다.',
        article_ids: [8, 9],
      },
    ],
    key_takeaways: [
      'GPT-5 출시 임박 — 멀티모달 기능 향상, API 가격 40% 인하 예정',
      'AI 에이전트의 프로덕션 적용이 가속화, ReAct + 함수 호출 조합이 최적 아키텍처로 부상',
      'Kubernetes 1.33의 사이드카 네이티브 지원으로 컨테이너 오케스트레이션의 오랜 과제 해결',
      'PostgreSQL 17의 병렬 쿼리 30% 향상은 대규모 데이터 처리에 즉시 적용 가능',
    ],
    connections:
      'AI와 인프라 주제가 긴밀하게 연결되어 있습니다. AI 워크로드의 급격한 증가가 Kubernetes와 같은 클라우드 인프라의 성능 개선을 요구하고 있으며, PostgreSQL의 JSONB 성능 향상은 AI 메타데이터 저장과 벡터 인덱싱에 직접적인 이점을 제공합니다. MLOps의 성숙은 이 모든 요소를 연결하는 접착제 역할을 하고 있습니다.',
  },
  article_ids: [1, 2, 3, 5, 6, 7, 8, 9],
  article_count: 8,
  created_at: '2026-02-16T06:30:00Z',
  updated_at: '2026-02-16T06:30:00Z',
};
```

#### Mock Handlers: `frontend/src/mocks/handlers.ts`

Add imports and handlers. Place digest handlers **before** the catch-all routes:

```typescript
import { mockDigest } from './data';   // Add to existing import

// Add these handlers to the handlers array:

// GET /api/digests/today (must be before /api/digests/:date)
http.get('/api/digests/today', () => {
  return HttpResponse.json(mockDigest);
}),

// GET /api/digests (list)
http.get('/api/digests', () => {
  return HttpResponse.json([mockDigest]);
}),

// GET /api/digests/:date
http.get('/api/digests/:date', ({ params }) => {
  if (params.date === mockDigest.digest_date) {
    return HttpResponse.json(mockDigest);
  }
  return new HttpResponse(null, { status: 404 });
}),

// POST /api/digests/generate (must be before /api/digests/generate/:date)
http.post('/api/digests/generate', async () => {
  await delay(1500);
  return HttpResponse.json(mockDigest, { status: 201 });
}),

// POST /api/digests/generate/:date
http.post('/api/digests/generate/:date', async ({ params }) => {
  await delay(1500);
  if (params.date === mockDigest.digest_date) {
    return HttpResponse.json(mockDigest, { status: 201 });
  }
  return new HttpResponse(
    JSON.stringify({ detail: `No articles found for ${params.date}` }),
    { status: 404 },
  );
}),
```

**Handler ordering note**: `/api/digests/today` must be registered before `/api/digests/:date` to avoid `"today"` being matched as a date parameter. Same for `/api/digests/generate` before `/api/digests/generate/:date`.

---

## 6. Testing

### 6.1 Backend Tests: `tests/test_digest.py`

Follow the `test_rewind.py` pattern. Use `MagicMock` for Supabase, `AsyncMock` for Gemini.

#### Service Test Helper

Used by tests #1-#7. The service's `generate_daily_digest` calls `client.table("articles").select(...).eq(...).order(...).execute()` — a **data query** (no count).

```python
def _make_service_supabase_mock(
    *,
    articles: list[dict] | None = None,
    upsert_result: list[dict] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for digest SERVICE tests.

    The service queries articles (data) and upserts digests.
    No count queries are involved at the service level.

    Args:
        articles: Rows for articles table query (newsletter articles).
        upsert_result: Rows returned from digests upsert.
    """
    mock_articles = MagicMock()
    mock_digests = MagicMock()

    # articles: select -> eq -> order -> execute (data query)
    article_data = articles if articles is not None else []
    mock_articles.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=article_data
    )

    # digests: upsert -> execute
    ups_data = upsert_result if upsert_result is not None else [{"id": 1}]
    mock_digests.upsert.return_value.execute.return_value = MagicMock(data=ups_data)

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "articles":
            return mock_articles
        if name == "digests":
            return mock_digests
        return MagicMock()

    mock_client.table.side_effect = route_table
    return mock_client
```

#### Router Test Helper

Used by tests #8-#17. Router endpoints call `client.table("articles").select("id", count="exact")` (count query) and `client.table("digests").select(...)` (data query). The `generate_daily_digest` and `persist_digest` are **patched** in router tests, so no articles data query occurs.

Follows the `_make_router_mock_client` pattern from `tests/test_rewind.py`.

```python
def _make_router_mock_client(
    *,
    user: dict | None = None,
    article_count: int = 0,
    digest_rows: list[dict] | None = None,
) -> MagicMock:
    """Build a mock Supabase client for digest ROUTER tests.

    The router performs:
    - users.select().eq().execute() -> user lookup (auth)
    - articles.select(count="exact").eq().execute() -> count check (generate endpoints)
    - digests.select().eq().execute() -> digest lookup (GET endpoints)
    - digests.select().order().range().execute() -> digest list (GET list endpoint)

    Args:
        user: Row for users table lookup.
        article_count: Count to return for articles count query.
        digest_rows: Rows for digests table queries.
    """
    mock_users = MagicMock()
    mock_articles = MagicMock()
    mock_digests = MagicMock()

    # users: select -> eq -> execute
    user_data = [user] if user is not None else []
    mock_users.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=user_data
    )

    # articles: select(count="exact") -> eq -> execute (COUNT query)
    mock_articles.select.return_value.eq.return_value.execute.return_value = MagicMock(
        count=article_count
    )

    # digests: select -> eq -> execute (by date or by id)
    digest_data = digest_rows if digest_rows is not None else []
    mock_digests.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=digest_data
    )

    # digests: select -> order -> range -> execute (list)
    mock_digests.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=digest_data
    )

    mock_client = MagicMock()

    def route_table(name: str) -> MagicMock:
        if name == "users":
            return mock_users
        if name == "articles":
            return mock_articles
        if name == "digests":
            return mock_digests
        return MagicMock()

    mock_client.table.side_effect = route_table
    return mock_client
```

**Why two helpers?** The call order differs:
- **Service tests**: `articles` → data query (`.select().eq().order().execute()`)
- **Router tests**: `articles` → count query (`.select(count="exact").eq().execute()`)

A single helper with call-count tracking is fragile and order-dependent. Separate helpers, following the `test_rewind.py` pattern, are more robust.

#### Test Cases (explicit list)

**Service tests:**

| # | Test name | Description | Mocks | Assertions |
|---|-----------|-------------|-------|------------|
| 1 | `test_generate_digest_happy_path` | Normal generation with articles | Supabase returns 3 articles, Gemini returns valid JSON | DigestContent has headline, sections with mapped IDs, takeaways |
| 2 | `test_generate_digest_no_articles` | No articles for date | Supabase returns empty article list | Returns `_NO_ARTICLES_DIGEST`, Gemini not called |
| 3 | `test_generate_digest_gemini_failure` | Gemini fails after retries | Supabase returns articles, Gemini raises RuntimeError | Returns fallback empty digest |
| 4 | `test_generate_digest_malformed_json` | Gemini returns invalid JSON | Supabase returns articles, Gemini returns `"not json"` | Returns fallback empty digest |
| 5 | `test_parse_digest_response_partial` | Missing fields in Gemini JSON | N/A (unit test parser directly) | Missing fields filled with defaults |
| 6 | `test_article_index_to_id_mapping` | Verify 1-based index → DB ID mapping | Supabase returns articles with IDs [101, 102, 103], Gemini returns `article_ids: [1, 3]` | Section `article_ids` becomes `[101, 103]` |
| 7 | `test_persist_digest_upsert` | Persist calls Supabase upsert | Mock upsert returns `{id: 42}` | Returns ID 42, upsert called with `on_conflict="digest_date"` |

**Router tests:**

| # | Test name | Description | Mocks | Assertions |
|---|-----------|-------------|-------|------------|
| 8 | `test_get_today_digest_200` | Today's digest exists | Supabase returns digest row | 200, content matches |
| 9 | `test_get_today_digest_404` | No digest for today | Supabase returns empty | 404 |
| 10 | `test_get_digest_by_date_200` | Specific date digest exists | Supabase returns digest row | 200 |
| 11 | `test_get_digest_by_date_404` | No digest for date | Supabase returns empty | 404, message includes date |
| 12 | `test_post_generate_201` | Manual generation succeeds | Service returns non-empty content, Supabase returns persisted row | 201, service called |
| 13 | `test_post_generate_no_articles_404` | No articles for today | Supabase count returns 0 | 404, service NOT called |
| 14 | `test_post_generate_empty_result_502` | Gemini returns empty digest | Service returns `_NO_ARTICLES_DIGEST` (empty headline) | 502, persist NOT called |
| 15 | `test_post_generate_for_date_201` | Backfill succeeds | Service returns non-empty content for specific date | 201 |
| 16 | `test_post_generate_for_date_no_articles_404` | No articles for date | Supabase count returns 0 | 404 |
| 17 | `test_list_digests` | List with pagination | Supabase returns rows | 200, list returned |

**Gemini mock pattern:**

**IMPORTANT**: Since `call_gemini_with_retry` and `create_gemini_client` live in `backend.services.gemini` but are imported into `digest.py`, mock targets must be chosen correctly:

- `create_gemini_client` — patch at **`backend.services.digest.create_gemini_client`** (patches the imported name in digest.py). This works because `digest.py` does `from backend.services.gemini import create_gemini_client`.
- `asyncio.sleep` — patch at **`backend.services.gemini.asyncio.sleep`** (sleep is called INSIDE `gemini.py`, not `digest.py`).
- `get_settings` — patch at **`backend.services.digest.get_settings`** (imported directly in digest.py).

```python
@pytest.mark.asyncio
@patch("backend.services.gemini.asyncio.sleep", new_callable=AsyncMock)
@patch("backend.services.digest.create_gemini_client")
@patch("backend.services.digest.get_settings")
async def test_generate_digest_happy_path(
    mock_get_settings: MagicMock,
    mock_create_gemini: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Verify digest generation with articles.

    Mocks: Supabase returns newsletter articles,
           Gemini returns valid JSON digest.
    Expects: DigestContent with headline, sections containing mapped DB IDs.
    """
```

### 6.2 Pipeline Test Update: `tests/test_pipeline.py`

The pipeline now imports `generate_daily_digest` and `persist_digest`. Existing pipeline tests do NOT mock these functions, so Stage 7 will try to execute and hit unmocked Supabase queries. **All existing pipeline tests must patch the digest service.**

**Required changes to every `test_pipeline_*` async test:**

1. Add these patches to each test's decorator stack:

```python
@patch("backend.services.pipeline.persist_digest", new_callable=AsyncMock, return_value=1)
@patch("backend.services.pipeline.generate_daily_digest", new_callable=AsyncMock, return_value=(_NO_ARTICLES_DIGEST, []))
```

Where `_NO_ARTICLES_DIGEST` is imported or inlined as:
```python
_EMPTY_DIGEST = ({"headline": "", "sections": [], "key_takeaways": [], "connections": ""}, [])
```

2. Add `digest_generated=False` to all `PipelineResult` assertions (digest returns empty, so pipeline skips persist).

3. For `test_pipeline_empty_collection`: No change needed beyond `digest_generated=False` since pipeline returns early before Stage 7.

**Example patch for `test_pipeline_happy_path`:**

Note: The current tests already mock `today_kst` with `@patch("backend.services.pipeline.today_kst", return_value=date(2026, 2, 16))`. The digest patches must be added **above** (outermost) the existing decorators to maintain correct parameter order.

```python
@pytest.mark.asyncio
@patch("backend.services.pipeline.persist_digest", new_callable=AsyncMock, return_value=1)
@patch("backend.services.pipeline.generate_daily_digest", new_callable=AsyncMock)
@patch("backend.services.pipeline.today_kst", return_value=date(2026, 2, 16))  # EXISTING
@patch("backend.services.pipeline.apply_time_decay", new_callable=AsyncMock, return_value=0)
@patch("backend.services.pipeline.generate_basic_summary", new_callable=AsyncMock)
@patch("backend.services.pipeline.score_articles", new_callable=AsyncMock)
@patch("backend.services.pipeline.collect_articles", new_callable=AsyncMock)
async def test_pipeline_happy_path(
    mock_collect: AsyncMock,
    mock_score: AsyncMock,
    mock_summarize: AsyncMock,
    _mock_decay: AsyncMock,
    _mock_today_kst: MagicMock,           # EXISTING
    mock_gen_digest: AsyncMock,            # NEW
    _mock_persist_digest: AsyncMock,       # NEW
) -> None:
    # ... existing test body ...
    # mock_gen_digest returns empty digest by default (no headline -> skip persist)
    mock_gen_digest.return_value = (
        {"headline": "", "sections": [], "key_takeaways": [], "connections": ""},
        [],
    )
    # ... existing assertions ...
    assert result["digest_generated"] is False  # ADD THIS
```

**Affected tests** (all async pipeline tests in `tests/test_pipeline.py`):

| Test | Has `today_kst` mock? | Digest patches needed? |
|------|----------------------|----------------------|
| `test_pipeline_happy_path` | Yes | Yes — add `generate_daily_digest` + `persist_digest` |
| `test_pipeline_empty_collection` | No (early return) | No — pipeline returns before Stage 7. Just add `digest_generated=False` assertion |
| `test_pipeline_scoring_failure` | No (aborts at Stage 3) | No — pipeline returns before Stage 7. Just add `digest_generated=False` assertion |
| `test_pipeline_summarization_failure` | No (`today_kst` not mocked) | Yes — reaches Stage 7. Add digest patches + `today_kst` mock |
| `test_pipeline_filtering_threshold_and_top_n` | No | Yes — reaches Stage 7 |
| `test_pipeline_newsletter_date_is_today` | No | Yes — reaches Stage 7 |

For tests that reach Stage 7 but DON'T already mock `today_kst`: they now need it because `generate_daily_digest` may call `today_kst` indirectly. However, since `generate_daily_digest` is patched (mocked), it won't actually call `today_kst`. So only the two pipeline-level digest patches are needed.

### 6.3 Digest Router Test: `today_kst` Mocking

The digest router endpoints `GET /today` and `POST /generate` call `today_kst()`. Router tests must mock this to ensure deterministic dates:

```python
@patch("backend.routers.digest.today_kst", return_value=date(2026, 2, 16))
@patch("backend.routers.digest.get_supabase_client")
def test_get_today_digest_200(
    mock_get_client: MagicMock,
    _mock_today: MagicMock,
) -> None:
    # ...
```

This applies to tests #8, #9, #12, #13, #14. Tests for `GET /{date}` and `POST /generate/{date}` do NOT need `today_kst` mock since they receive the date as a path parameter.

### 6.4 E2E Tests (Playwright)

The project uses Playwright for e2e testing. Tests run against the dev server with MSW mocks (`npm run dev`). Follow the patterns in `frontend/e2e/rewind.spec.ts` and `frontend/e2e/today.spec.ts`.

#### `frontend/e2e/digest.spec.ts` (NEW file)

| # | Test name | Description |
|---|-----------|-------------|
| E1 | `should display headline in indigo card` | Navigate to `/digest`, verify `mockDigest.content.headline` text visible |
| E2 | `should display key takeaways as bullet list` | Verify 4 takeaway items visible in amber-colored section |
| E3 | `should display thematic sections with theme badges` | Verify 3 sections with theme badges ("AI/ML", "DevOps", "Backend"), titles, and body text |
| E4 | `should display connections section` | Verify connections text visible in gray card |
| E5 | `should display article count link in each section` | Verify "3 articles →", "3 articles →", "2 articles →" links visible |
| E6 | `should navigate to Today page with article filter on section link click` | Click "3 articles →" in AI/ML section → URL becomes `/?articles=1,2,3` |
| E7 | `should show date navigation buttons` | Verify `<` and `>` buttons visible |
| E8 | `should disable next-day button on today's date` | Verify `>` button has disabled state |
| E9 | `should handle Generate button with loading state` | Click "Regenerate" → shows "Generating..." with spinner → returns to normal |
| E10 | `should transition from loading skeleton to content` | Fresh navigate, verify skeleton disappears and content appears |

**Test structure:**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Digest Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/digest');
    // Wait for digest to load (headline appears)
    await expect(
      page.getByText('AI 에이전트 혁신과 클라우드 인프라 진화가 개발 생태계를 재편'),
    ).toBeVisible();
  });

  test('should display headline in indigo card', async ({ page }) => {
    // headline text from mockDigest
    await expect(
      page.getByText('AI 에이전트 혁신과 클라우드 인프라 진화가 개발 생태계를 재편'),
    ).toBeVisible();
  });

  // ... remaining tests follow rewind.spec.ts patterns ...
});
```

#### `frontend/e2e/navigation.spec.ts` update

Add Digest to the `should navigate between all pages` test:

```typescript
// After navigating to Today, before Archive:
await page.getByRole('link', { name: /digest/i }).click();
await expect(page).toHaveURL('/digest');
```

#### `frontend/e2e/today.spec.ts` update

Add one test for the `?articles=` filter:

```typescript
test('should filter articles when ?articles= query param is present', async ({ page }) => {
  // Navigate with filter
  await page.goto('/?articles=1,2');

  // Should show filter banner
  await expect(page.getByText(/Showing 2 articles from Digest/)).toBeVisible();

  // Should show only 2 articles
  const articleLinks = page.getByRole('link', { name: /GPT-5|Building Reliable AI Agents/ });
  await expect(articleLinks).toHaveCount(2);

  // Click "Show all" to clear filter
  await page.getByRole('button', { name: /Show all/ }).click();
  await expect(page).toHaveURL('/');
  await expect(page.getByText('10 articles')).toBeVisible();
});
```

---

## 7. Gemini API Usage Estimate

| Component | Tokens (approx) |
|-----------|-----------------|
| Prompt (instructions + 20 articles with summaries) | ~3,000-4,000 input |
| Response (structured JSON) | ~1,500-2,000 output |
| **Total per call** | **~5,000-6,000 tokens** |

- 1 digest/day = 1 Gemini call
- Cost: ~$0.001/day (negligible with Gemini 2.5 Flash)

---

## 8. Implementation Plan

### Commit Strategy

Each commit must pass its verification gate before proceeding. Branch: `feature/daily-digest`.

| Commit | Steps | Description | Verification gate |
|--------|-------|-------------|-------------------|
| **C1** `refactor: extract shared Gemini retry utility` | 1.1-1.2 | `gemini.py` shared utility + `rewind.py` refactor + rewind test patch path update | `uv run pytest tests/test_rewind.py` |
| **C2** `feat: add digest service, schema, and API endpoints` | 1.3-1.6 | Digest service + schema + router + main.py registration | `uv run pytest tests/test_digest.py` (service tests #1-7) |
| **C3** `feat: integrate digest into daily pipeline` | 1.7-1.8 | Pipeline Stage 7 + pipeline test update + digest router tests #8-17 | `uv run pytest` (full suite) |
| **C4** `feat(frontend): add digest types, API client, and hook` | 2.1-2.5 | TypeScript types + API client + useDigest hook + barrel exports | TS compile check (`cd frontend && npx tsc --noEmit`) |
| **C5** `feat(frontend): add Digest page, components, and navigation` | 2.6-2.13 | DigestView + DigestSkeleton + Digest page + App route + NavBar + MSW mock data & handlers | `cd frontend && npm run dev` → Digest page renders with mock data |
| **C6** `feat(frontend): add article filter to Today page` | 3.1 | Today.tsx `?articles=` query param filter + banner | `cd frontend && npm run dev` → `/?articles=1,2` filters correctly |
| **C7** `test(e2e): add Digest page and Today filter e2e tests` | 4.1-4.3 | `digest.spec.ts` + navigation.spec.ts update + today.spec.ts update | `cd frontend && npx playwright test` |
| **C8** `docs: update CLAUDE.md with Digest page` | 5.5 | Route map + page list update | `uv run pre-commit run --all-files` |

### Phase 1: Backend Foundation

| Step | File(s) | Description |
|------|---------|-------------|
| 1.0 | DB | Run `CREATE TABLE digests` SQL via Supabase SQL Editor |
| 1.1 | `backend/services/gemini.py` | Create shared Gemini utility (NEW file) |
| 1.2 | `backend/services/rewind.py` + `tests/test_rewind.py` | Refactor to import from `gemini.py` (remove local `_call_gemini_with_retry`) + update 3 test patch paths |
| 1.3 | `backend/services/digest.py` | Implement full service (NEW file) |
| 1.4 | `backend/schemas/digest.py` | Pydantic response models (NEW file) |
| 1.5 | `backend/routers/digest.py` | API endpoints (NEW file) |
| 1.6 | `backend/main.py` | Register digest router |
| 1.7 | `backend/services/pipeline.py` | Add Stage 7 + update PipelineResult |
| 1.8 | `tests/test_digest.py` | All 17 test cases (NEW file) |

### Phase 2: Frontend

| Step | File(s) | Description |
|------|---------|-------------|
| 2.1 | `frontend/src/types/digest.ts` | TypeScript types (NEW file) |
| 2.2 | `frontend/src/types/index.ts` | Add Digest exports |
| 2.3 | `frontend/src/api/client.ts` | Add `digestApi` |
| 2.4 | `frontend/src/hooks/useDigest.ts` | Data fetching hook (NEW file) |
| 2.5 | `frontend/src/hooks/index.ts` | Add useDigest export |
| 2.6 | `frontend/src/components/DigestView.tsx` | Main digest component (NEW file) |
| 2.7 | `frontend/src/components/common/Skeleton.tsx` | Add DigestSkeleton |
| 2.8 | `frontend/src/components/common/index.ts` | Export DigestSkeleton |
| 2.9 | `frontend/src/pages/Digest.tsx` | Digest page with date navigation (NEW file) |
| 2.10 | `frontend/src/App.tsx` | Add `/digest` route |
| 2.11 | `frontend/src/components/NavBar.tsx` | Add Digest nav item |
| 2.12 | `frontend/src/mocks/data.ts` | Add `mockDigest` |
| 2.13 | `frontend/src/mocks/handlers.ts` | Add 5 digest handlers |

### Phase 3: Today Page Enhancement

| Step | File(s) | Description |
|------|---------|-------------|
| 3.1 | `frontend/src/pages/Today.tsx` | Add `?articles=` query param filter + banner |

### Phase 4: E2E Tests

| Step | File(s) | Description |
|------|---------|-------------|
| 4.1 | `frontend/e2e/digest.spec.ts` | Digest page e2e tests (NEW file) |
| 4.2 | `frontend/e2e/navigation.spec.ts` | Add Digest link to navigation test |
| 4.3 | `frontend/e2e/today.spec.ts` | Add `?articles=` filter e2e test |

### Phase 5: Verification

| Step | Description |
|------|-------------|
| 5.1 | `uv run pytest` — all backend tests pass |
| 5.2 | `uv run pre-commit run --all-files` — linting/formatting pass |
| 5.3 | `cd frontend && npm run dev` — verify Digest page with MSW mocks |
| 5.4 | `cd frontend && npx playwright test` — all e2e tests pass |
| 5.5 | Update `CLAUDE.md` route map and page list |

---

## 9. Files Changed Summary

### New Files (10)

| File | Type |
|------|------|
| `docs/migrations/001_create_digests_table.sql` | SQL |
| `backend/services/gemini.py` | Python |
| `backend/services/digest.py` | Python |
| `backend/schemas/digest.py` | Python |
| `backend/routers/digest.py` | Python |
| `tests/test_digest.py` | Python |
| `frontend/src/types/digest.ts` | TypeScript |
| `frontend/src/hooks/useDigest.ts` | TypeScript |
| `frontend/src/pages/Digest.tsx` | TypeScript |
| `frontend/src/components/DigestView.tsx` | TypeScript |
| `frontend/e2e/digest.spec.ts` | TypeScript (Playwright) |

### Modified Files (15)

| File | Change |
|------|--------|
| `backend/services/rewind.py` | Import from `gemini.py` instead of local retry function |
| `tests/test_rewind.py` | Update `asyncio.sleep` patch path: `rewind.asyncio.sleep` → `gemini.asyncio.sleep` (3 tests) |
| `backend/services/pipeline.py` | Add Stage 7 + `digest_generated` field |
| `backend/main.py` | Register `digest.router` |
| `frontend/src/types/index.ts` | Export Digest types |
| `frontend/src/api/client.ts` | Add `digestApi` |
| `frontend/src/hooks/index.ts` | Export `useDigest` |
| `frontend/src/components/common/Skeleton.tsx` | Add `DigestSkeleton` |
| `frontend/src/components/common/index.ts` | Export `DigestSkeleton` |
| `frontend/src/pages/Today.tsx` | Add `?articles=` filter support |
| `frontend/src/App.tsx` | Add `/digest` route |
| `frontend/src/components/NavBar.tsx` | Add Digest nav item |
| `frontend/src/mocks/data.ts` | Add `mockDigest` |
| `frontend/src/mocks/handlers.ts` | Add 5 digest handlers |
| `frontend/e2e/navigation.spec.ts` | Add Digest link to navigation test |
| `frontend/e2e/today.spec.ts` | Add `?articles=` filter e2e test |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini returns poorly structured JSON | Digest shows empty/broken content | Robust parser with field-level fallbacks; fallback empty digest |
| Gemini returns out-of-range article indices | Section shows wrong or no articles | Guard clause in index-to-ID mapping: `if idx in index_to_id` |
| Digest generation fails in pipeline | Users see no digest for today | Pipeline logs warning and continues; manual generate endpoint as backup |
| Digest content too similar to per-article summaries | Low value-add vs Today page | Prompt explicitly instructs "synthesize, don't concatenate" |
| Large number of categories → too many sections | Long, unfocused digest | Prompt caps sections at 5 |
| `updated_at` not properly set on upsert | Cannot tell when digest was regenerated | Use explicit timestamp in upsert row |
| `PipelineResult` change breaks existing tests | CI failures | Update existing pipeline test assertions to include `digest_generated=False` |

---

## 11. Future Enhancements (Out of Scope)

- **Per-user digest**: Personalize based on user interests
- **Email delivery**: Send digest as morning email
- **Digest history calendar**: Calendar view like Archive
- **Digest feedback**: Like/dislike sections to improve generation
- **Audio digest**: TTS version for commuters

---

## 12. Acceptance Criteria

Each criterion includes a **verification method** so the implementing agent knows exactly how to confirm it's met.

### 12.1 Database

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | `digests` table exists with correct schema | `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'digests'` returns 7 columns (id, digest_date, content, article_ids, article_count, created_at, updated_at) |
| 2 | `digest_date` has UNIQUE constraint | `INSERT INTO digests (digest_date, content) VALUES ('2026-01-01', '{}'), ('2026-01-01', '{}')` fails with unique violation |
| 3 | `idx_digests_date` index exists | `SELECT indexname FROM pg_indexes WHERE tablename = 'digests'` includes `idx_digests_date` |

### 12.2 Backend — Shared Gemini Utility

| # | Criterion | Verification |
|---|-----------|-------------|
| 4 | `backend/services/gemini.py` exists with `create_gemini_client()` and `call_gemini_with_retry()` | File exists, both functions importable: `from backend.services.gemini import create_gemini_client, call_gemini_with_retry` |
| 5 | `backend/services/rewind.py` imports from `gemini.py` instead of having local `_call_gemini_with_retry` | `grep "_call_gemini_with_retry" backend/services/rewind.py` returns zero matches; `grep "from backend.services.gemini import" backend/services/rewind.py` returns a match |
| 6 | Existing rewind tests still pass after refactor | `uv run pytest tests/test_rewind.py` passes |

### 12.3 Backend — Digest Service

| # | Criterion | Verification |
|---|-----------|-------------|
| 7 | `generate_daily_digest()` returns `(DigestContent, list[int])` with articles from DB | Test #1 (`test_generate_digest_happy_path`): Gemini receives prompt with article data, returned sections contain mapped real DB IDs (not 1-based indices) |
| 8 | Returns `_NO_ARTICLES_DIGEST` when no articles exist for the date | Test #2 (`test_generate_digest_no_articles`): Gemini never called, returned headline is `""` |
| 9 | Falls back to empty digest when Gemini fails after 3 retries | Test #3 (`test_generate_digest_gemini_failure`): Returns empty digest, no exception raised |
| 10 | Parser handles malformed JSON gracefully | Test #4 (`test_generate_digest_malformed_json`): Returns empty digest |
| 11 | Parser fills missing fields with safe defaults | Test #5 (`test_parse_digest_response_partial`): e.g., JSON with only `headline` → sections=[], key_takeaways=[], connections="" |
| 12 | 1-based Gemini indices correctly mapped to DB article IDs | Test #6 (`test_article_index_to_id_mapping`): Articles with DB IDs [101, 102, 103], Gemini returns `article_ids: [1, 3]` → section `article_ids` becomes [101, 103] |
| 13 | `persist_digest()` upserts (INSERT or UPDATE) based on `digest_date` | Test #7: upsert called with `on_conflict="digest_date"`; calling twice for same date does not raise error |

### 12.4 Backend — API Endpoints

| # | Criterion | Verification |
|---|-----------|-------------|
| 14 | `GET /api/digests/today` → 200 with `DigestResponse` when digest exists | Test #8: Response has `id`, `digest_date`, `content.headline`, `content.sections`, `content.key_takeaways`, `content.connections`, `article_ids`, `article_count` |
| 15 | `GET /api/digests/today` → 404 when no digest for today | Test #9: Status 404, body contains `"No digest found"` |
| 16 | `GET /api/digests/{date}` → 200 for existing date | Test #10: Response has correct `digest_date` |
| 17 | `GET /api/digests/{date}` → 404 for missing date, message includes the date | Test #11: Status 404, body contains the requested date string |
| 18 | `GET /api/digests` → 200 with list, supports `limit` and `offset` query params | Test #17: Returns list of `DigestResponse` |
| 19 | `POST /api/digests/generate` → 201, triggers generation, returns created digest | Test #12: `generate_daily_digest` called, response has `id` and `content` |
| 20 | `POST /api/digests/generate` → 404 when no articles exist for today | Test #13: Status 404, `generate_daily_digest` NOT called |
| 21 | `POST /api/digests/generate` → 502 when Gemini returns empty result | Test #14: Status 502, `persist_digest` NOT called |
| 22 | `POST /api/digests/generate/{date}` → 201 for date with articles | Test #15: Same as #19 but with arbitrary date |
| 23 | `POST /api/digests/generate/{date}` → 404 for date without articles | Test #16: Same as #20 |
| 24 | All endpoints require `get_current_user_id` dependency | All route handlers include `user_id: int = Depends(get_current_user_id)`. Auth 401 behavior is tested by the project's shared auth infrastructure (`tests/conftest.py:22` `autouse=True` override); no per-router 401 test needed |
| 25 | All "today" references use `today_kst()` from `backend.time_utils` | `grep "today_kst" backend/routers/digest.py` returns matches; `grep "date\.today\b\|timezone\.utc" backend/routers/digest.py` returns zero matches |
| 26 | Digest router registered in `backend/main.py` | `GET /api/digests/today` is routable (not 404 "Not Found" from FastAPI router) |

### 12.5 Backend — Pipeline Integration

| # | Criterion | Verification |
|---|-----------|-------------|
| 27 | Daily pipeline includes Stage 7 (digest generation) after Stage 6 | Pipeline log includes `"Stage 7/7: Generating daily digest"` |
| 28 | `PipelineResult` includes `digest_generated: bool` field | `PipelineResult.__annotations__` contains `digest_generated` |
| 29 | Digest generation failure does NOT abort the pipeline | When `generate_daily_digest` raises an Exception, pipeline still returns a `PipelineResult` with all other fields populated and `digest_generated=False` |
| 30 | Empty digest (no headline) is NOT persisted in pipeline | Pipeline checks `digest_content["headline"]` before calling `persist_digest`; consistent with manual generate endpoints returning 502 |
| 31 | Existing pipeline tests pass with digest service patched | `uv run pytest tests/test_pipeline.py tests/test_pipeline_routes.py` passes. All async pipeline tests must add `@patch("backend.services.pipeline.generate_daily_digest", ...)` and `@patch("backend.services.pipeline.persist_digest", ...)` (see Section 6.2 for details) |

### 12.6 Frontend — Types & API

| # | Criterion | Verification |
|---|-----------|-------------|
| 32 | `Digest`, `DigestContent`, `DigestSection` types exported from `types/index.ts` | `import { Digest, DigestContent, DigestSection } from '../types'` compiles |
| 33 | `digestApi` object in `api/client.ts` with 5 methods | `getToday`, `getByDate`, `list`, `generate`, `generateForDate` all exist |
| 34 | `useDigest` hook exported from `hooks/index.ts` | `import { useDigest } from '../hooks'` compiles |

### 12.7 Frontend — Digest Page

| # | Criterion | Verification |
|---|-----------|-------------|
| 35 | `/digest` route exists and renders `Digest` page | Navigate to `/digest` in browser → page renders (MSW dev mode) |
| 36 | NavBar shows "Digest" link with `FileText` icon between "Today" and "Archive" | Visual inspection: nav order is Today → Digest → Archive → Bookmarks → Rewind → Settings |
| 37 | Digest page shows headline in indigo card | `mockDigest.content.headline` text visible in indigo-colored container |
| 38 | Key Takeaways displayed as bulleted list in amber card | 4 takeaway items visible |
| 39 | Thematic sections rendered with theme badge, title, body, and article link | 3 sections visible, each with theme badge (e.g., "AI/ML"), title, body paragraph, and "N articles →" link |
| 40 | Connections section displayed at bottom in gray card | Connections text visible |
| 41 | Left/right date navigation buttons present | `<` and `>` buttons visible next to the date |
| 42 | "Next day" button disabled when viewing today | On today's date, `>` button has `disabled` attribute / opacity-30 |
| 43 | Clicking "Previous day" changes date and refetches | Click `<`, date label changes to previous day, hook re-fetches |
| 44 | Empty state shown when digest not found (404) | Navigate to a date without digest → EmptyState with "Generate Digest" button visible |
| 45 | Generate button triggers `POST /api/digests/generate` and shows spinner | Click "Generate Digest" → button shows "Generating..." with spinning icon → digest appears after response |
| 46 | Loading state shows `DigestSkeleton` | During fetch, skeleton with animated pulse placeholders visible |
| 47 | Error state shows `ErrorDisplay` with retry | When API fails (non-404), error message and "Retry" button visible |

### 12.8 Frontend — Today Page Filter

| # | Criterion | Verification |
|---|-----------|-------------|
| 48 | `/?articles=1,2,3` filters to only those article IDs | Navigate to `/?articles=1,2` → only articles with id 1 and 2 visible |
| 49 | Filter banner shows "Showing N articles from Digest" | Blue banner visible with correct count |
| 50 | "Show all" button clears the filter and removes query param | Click "Show all" → all articles visible, URL no longer has `?articles=` |
| 51 | Without `?articles=` param, Today page behaves identically to before | No banner, all articles shown |

### 12.9 Frontend — MSW Mocks

| # | Criterion | Verification |
|---|-----------|-------------|
| 52 | `mockDigest` in `data.ts` references valid mock article IDs (1-10) | All `article_ids` in sections are within the range of `mockArticles` IDs |
| 53 | 5 MSW handlers registered for digest endpoints | Handlers for: `GET /today`, `GET /`, `GET /:date`, `POST /generate`, `POST /generate/:date` |
| 54 | `npm run dev` shows Digest page with full mock data, no console errors | Visual + console inspection |

### 12.10 E2E Tests

| # | Criterion | Verification |
|---|-----------|-------------|
| 55 | `frontend/e2e/digest.spec.ts` exists with 10 tests | `npx playwright test e2e/digest.spec.ts` → 10 passed |
| 56 | Digest page renders headline, takeaways, sections, connections | E1-E4: mock data visible in correct styled containers |
| 57 | Section article links navigate to Today page with `?articles=` filter | E6: clicking "3 articles →" navigates to `/?articles=1,2,3` |
| 58 | Date navigation and generate button work | E7-E9: buttons present, next-day disabled, generate shows spinner |
| 59 | Navigation test includes Digest link | `npx playwright test e2e/navigation.spec.ts` → passes, `/digest` URL visited |
| 60 | Today page `?articles=` filter works in e2e | `npx playwright test e2e/today.spec.ts` → filter test passes, banner visible, "Show all" clears |
| 61 | All existing e2e tests still pass | `cd frontend && npx playwright test` → no failures |

### 12.11 Quality Gates

| # | Criterion | Verification |
|---|-----------|-------------|
| 62 | All 17 backend test cases in `tests/test_digest.py` pass | `uv run pytest tests/test_digest.py -v` → 17 passed |
| 63 | All existing backend tests still pass (baseline: 138 passed) | `uv run pytest -q` → no failures, count >= 138 |
| 64 | Pre-commit hooks pass | `uv run pre-commit run --all-files` → all checks passed |
| 65 | All e2e tests pass (including new digest tests) | `cd frontend && npx playwright test` → all passed |
| 66 | `CLAUDE.md` updated with Digest page in route map and page list | Route map includes `/digest` → Digest entry |

### Summary

**Total: 66 acceptance criteria** across 11 categories.

Must-pass gate for "feature complete": **all 66 criteria met**.
