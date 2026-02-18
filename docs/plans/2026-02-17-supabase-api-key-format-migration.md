# Supabase API Key Format Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 레거시 `anon/service_role` 키 의존을 `publishable/secret` 키 중심 구조로 전환하고, 2026년 하반기 레거시 제거 전에 무중단 마이그레이션을 완료한다.

**Architecture:** 설정 계층에서 새 키를 우선하고 레거시 키를 fallback으로 지원하는 compatibility layer를 먼저 만든다. 그 다음 backend/client, frontend/vite 매핑, 문서를 순차적으로 갱신한다. 런타임 동작은 유지하면서 경고 로그와 테스트로 전환 상태를 명확히 한다.

**Tech Stack:** FastAPI, pydantic-settings, supabase-py, Vite, @supabase/supabase-js, pytest

---

### Task 1: Settings Compatibility Layer 추가

**Files:**
- Modify: `backend/config.py`
- Modify: `.env.example`
- Test: `tests/test_config_keys.py` (new)

**Step 1: Write the failing test**

```python
# tests/test_config_keys.py
from backend.config import Settings


def test_prefers_new_supabase_keys_over_legacy() -> None:
    settings = Settings(
        supabase_publishable_key="sb_publishable_new",
        supabase_anon_key="legacy_anon",
        supabase_secret_key="sb_secret_new",
        supabase_service_role_key="legacy_service",
    )
    assert settings.effective_supabase_publishable_key == "sb_publishable_new"
    assert settings.effective_supabase_secret_key == "sb_secret_new"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config_keys.py::test_prefers_new_supabase_keys_over_legacy -v`
Expected: FAIL with missing settings fields/properties

**Step 3: Write minimal implementation**

```python
# backend/config.py (Settings)
supabase_publishable_key: str = Field(default="")
supabase_secret_key: str = Field(default="")

@property
def effective_supabase_publishable_key(self) -> str:
    return self.supabase_publishable_key or self.supabase_anon_key

@property
def effective_supabase_secret_key(self) -> str:
    return self.supabase_secret_key or self.supabase_service_role_key
```

Also update `.env.example`:

```env
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
# Legacy fallback (to be removed)
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config_keys.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/config.py .env.example tests/test_config_keys.py
git commit -m "feat: add supabase key compatibility settings"
```

### Task 2: Backend Supabase client 키 소스 전환

**Files:**
- Modify: `backend/supabase_client.py`
- Test: `tests/test_supabase_client.py` (new)

**Step 1: Write the failing test**

```python
# tests/test_supabase_client.py
from unittest.mock import patch

from backend.supabase_client import get_supabase_client


def test_uses_effective_secret_key() -> None:
    with patch("backend.supabase_client.get_settings") as mock_settings, \
         patch("backend.supabase_client.create_client") as mock_create:
        mock_settings.return_value.supabase_url = "https://example.supabase.co"
        mock_settings.return_value.effective_supabase_secret_key = "sb_secret_new"
        get_supabase_client.cache_clear()
        get_supabase_client()
        mock_create.assert_called_once_with(
            "https://example.supabase.co", "sb_secret_new"
        )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_supabase_client.py::test_uses_effective_secret_key -v`
Expected: FAIL because client still references legacy key field

**Step 3: Write minimal implementation**

```python
# backend/supabase_client.py
return create_client(settings.supabase_url, settings.effective_supabase_secret_key)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_supabase_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/supabase_client.py tests/test_supabase_client.py
git commit -m "refactor: switch backend client to effective supabase secret key"
```

### Task 3: Frontend env 매핑을 publishable 우선으로 전환

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/lib/supabase.ts`
- Test: `frontend/package.json` (existing build script)

**Step 1: Write the failing test (build-level guard)**

```ts
// no unit test infra exists; use build as executable regression test
// target change: VITE_SUPABASE_ANON_KEY references replaced by publishable-first mapping
```

**Step 2: Run build to capture baseline**

Run: `cd frontend && npm run build`
Expected: PASS (baseline)

**Step 3: Write minimal implementation**

```ts
// frontend/vite.config.ts
'import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(
  env.VITE_SUPABASE_PUBLISHABLE_KEY || env.SUPABASE_PUBLISHABLE_KEY || env.VITE_SUPABASE_ANON_KEY || env.SUPABASE_ANON_KEY || '',
)
```

```ts
// frontend/src/lib/supabase.ts
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
```

Update runtime error text to mention `VITE_SUPABASE_PUBLISHABLE_KEY` first.

**Step 4: Run build to verify it passes**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/vite.config.ts frontend/src/lib/supabase.ts
git commit -m "feat: prefer publishable key in frontend supabase config"
```

### Task 4: 운영 문서/런북 업데이트

**Files:**
- Modify: `README.md`
- Modify: `docs/deployment.md`
- Modify: `docs/deployment-cloud.md`

**Step 1: Write failing doc check list**

```text
- README env section still shows anon/service_role only
- deployment docs do not mention publishable/secret fallback policy
```

**Step 2: Verify current docs**

Run: `rg -n "SUPABASE_ANON_KEY|SUPABASE_SERVICE_ROLE_KEY" README.md docs/deployment.md docs/deployment-cloud.md`
Expected: multiple matches

**Step 3: Write minimal implementation**

Add migration guidance:
- Primary: `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`
- Legacy fallback window and removal timeline
- Rollback instructions

**Step 4: Validate docs reflect new keys**

Run: `rg -n "SUPABASE_PUBLISHABLE_KEY|SUPABASE_SECRET_KEY" README.md docs/deployment.md docs/deployment-cloud.md`
Expected: matches present in all relevant docs

**Step 5: Commit**

```bash
git add README.md docs/deployment.md docs/deployment-cloud.md
git commit -m "docs: add supabase publishable/secret key migration guide"
```

### Task 5: 통합 검증

**Files:**
- Test: `tests/test_config_keys.py`
- Test: `tests/test_supabase_client.py`

**Step 1: Run focused backend tests**

Run: `uv run pytest tests/test_config_keys.py tests/test_supabase_client.py -v`
Expected: PASS

**Step 2: Run existing auth regression tests**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS

**Step 3: Run frontend build regression**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 4: Final commit (if needed)**

```bash
git add -A
git commit -m "chore: finalize supabase key format migration"
```
