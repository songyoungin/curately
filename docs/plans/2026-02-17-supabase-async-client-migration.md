# Supabase AsyncClient Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** FastAPI 이벤트 루프에 맞게 Supabase 접근 경로를 `AsyncClient` 중심으로 전환해 동시성 효율을 개선한다.

**Architecture:** 전면 치환 대신 adapter 단계로 전환한다. 먼저 async client 팩토리와 공용 DB helper를 도입하고, 인증/핵심 라우터부터 점진적으로 `await` 기반 쿼리로 치환한다. 스케줄러와 서비스 계층은 마지막에 정리해 위험을 분산한다.

**Tech Stack:** FastAPI async, supabase-py (`acreate_client`, `AsyncClient`), pytest, APScheduler

---

### Task 1: Async Supabase client 팩토리 도입

**Files:**
- Modify: `backend/supabase_client.py`
- Test: `tests/test_supabase_client_async.py` (new)

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, patch

from backend.supabase_client import get_async_supabase_client


@pytest.mark.asyncio
async def test_get_async_supabase_client_uses_acreate_client() -> None:
    with patch("backend.supabase_client.acreate_client", new_callable=AsyncMock) as mock_create, \
         patch("backend.supabase_client.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://example.supabase.co"
        mock_settings.return_value.effective_supabase_secret_key = "sb_secret_new"

        await get_async_supabase_client()

        mock_create.assert_awaited_once_with(
            "https://example.supabase.co", "sb_secret_new"
        )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_supabase_client_async.py::test_get_async_supabase_client_uses_acreate_client -v`
Expected: FAIL because async factory does not exist

**Step 3: Write minimal implementation**

```python
from supabase import AsyncClient, acreate_client

_async_client: AsyncClient | None = None

async def get_async_supabase_client() -> AsyncClient:
    global _async_client
    if _async_client is None:
        settings = get_settings()
        _async_client = await acreate_client(
            settings.supabase_url,
            settings.effective_supabase_secret_key,
        )
    return _async_client
```

Keep existing sync client temporarily for migration safety.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_supabase_client_async.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/supabase_client.py tests/test_supabase_client_async.py
git commit -m "feat: add async supabase client factory"
```

### Task 2: auth 경로 async client 전환

**Files:**
- Modify: `backend/auth.py`
- Modify: `backend/routers/auth.py`
- Test: `tests/test_auth.py`

**Step 1: Write the failing test**

```python
@patch("backend.auth.get_async_supabase_client", new_callable=AsyncMock)
def test_auth_uses_async_client_for_user_upsert(mock_get_async_client: AsyncMock) -> None:
    # configure async table().select().eq().execute() chain
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py::test_auth_uses_async_client_for_user_upsert -v`
Expected: FAIL because auth still imports sync client getter

**Step 3: Write minimal implementation**

- Replace `get_supabase_client()` with `await get_async_supabase_client()`
- Make `_upsert_user` async and await `.execute()` calls where async SDK requires it.
- Update `/api/auth/me` route to use async client calls.

**Step 4: Run focused tests**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/auth.py backend/routers/auth.py tests/test_auth.py
git commit -m "refactor: migrate auth flow to async supabase client"
```

### Task 3: 라우터/서비스 점진 전환 (고트래픽 경로 우선)

**Files:**
- Modify: `backend/routers/articles.py`
- Modify: `backend/routers/newsletters.py`
- Modify: `backend/services/pipeline.py`
- Test: `tests/test_articles.py`
- Test: `tests/test_newsletters.py`

**Step 1: Write failing route-level tests**

```python
# example assertion pattern
# ensure route still returns same schema and status while async client is used underneath
```

**Step 2: Run targeted tests to capture baseline**

Run: `uv run pytest tests/test_articles.py tests/test_newsletters.py -v`
Expected: PASS (baseline)

**Step 3: Write minimal implementation per module**

- For each module, replace sync client retrieval with awaited async getter.
- Convert helper functions touching DB to async.
- Keep API response schemas unchanged.

**Step 4: Run targeted tests after each module**

Run: `uv run pytest tests/test_articles.py -v`
Expected: PASS

Run: `uv run pytest tests/test_newsletters.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/routers/articles.py backend/routers/newsletters.py backend/services/pipeline.py tests/test_articles.py tests/test_newsletters.py
git commit -m "refactor: migrate high-traffic routes to async supabase client"
```

### Task 4: 스케줄러/앱 수명주기 정리

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/scheduler.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_rewind.py`

**Step 1: Write failing scheduler/lifespan tests**

```python
# assert startup seeding and scheduled jobs can obtain async client without blocking
```

**Step 2: Run baseline tests**

Run: `uv run pytest tests/test_pipeline.py tests/test_rewind.py -v`
Expected: PASS baseline

**Step 3: Write minimal implementation**

- In `lifespan`, await async client getter.
- In scheduler jobs, ensure DB operations use async client path.
- Remove obsolete sync-only helper usage.

**Step 4: Run regression tests**

Run: `uv run pytest tests/test_pipeline.py tests/test_rewind.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/main.py backend/scheduler.py tests/test_pipeline.py tests/test_rewind.py
git commit -m "refactor: align scheduler and lifespan with async supabase client"
```

### Task 5: sync 경로 제거 및 최종 검증

**Files:**
- Modify: `backend/supabase_client.py`
- Modify: `backend/*` (remaining imports)

**Step 1: Write failing search check**

```text
No production module should import/use get_supabase_client() after migration.
```

**Step 2: Verify remaining sync references**

Run: `rg -n "get_supabase_client\(" backend`
Expected: one or more matches before cleanup

**Step 3: Write minimal implementation**

- Remove sync getter or keep test-only shim with deprecation warning.
- Replace all remaining call sites with async getter path.

**Step 4: Run full regression suite**

Run: `uv run pytest tests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/supabase_client.py backend tests
git commit -m "chore: complete async supabase client migration"
```
