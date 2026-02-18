# ES256-Only JWT Verification Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Supabase 프로젝트의 ES256 마이그레이션 완료 이후 backend 인증 코드에서 HS256 fallback을 제거하고 ES256-only 정책으로 단순화한다.

**Architecture:** 먼저 운영 전제조건(대시보드 마이그레이션 완료, 토큰 샘플 검증)을 체크리스트로 고정한다. 그 다음 코드에서 HS256 분기/레거시 시크릿 의존을 제거하고 테스트를 ES256-only 시나리오로 재작성한다.

**Tech Stack:** FastAPI, supabase-py, pytest, Supabase Auth (JWKS/claims)

---

### Task 1: 운영 전제조건 검증 체크리스트 문서화

**Files:**
- Create: `docs/plans/2026-02-17-es256-migration-preflight.md`
- Modify: `README.md`

**Step 1: Write failing checklist draft**

```text
- Supabase Dashboard에서 JWT signing key가 ES256으로 전환 완료되었는가?
- 기존 HS256 토큰이 더 이상 발급되지 않는가?
- 롤백 절차(임시) 정의가 있는가?
```

**Step 2: Verify docs missing preflight**

Run: `rg -n "ES256|HS256|Migrate JWT secret" README.md docs`
Expected: insufficient or scattered guidance

**Step 3: Write minimal implementation**

`docs/plans/2026-02-17-es256-migration-preflight.md`에 아래 포함:
- 대시보드 확인 절차
- 샘플 토큰 `alg` 확인 절차
- 장애 시 롤백 조건

**Step 4: Validate preflight doc exists**

Run: `test -f docs/plans/2026-02-17-es256-migration-preflight.md && echo ok`
Expected: `ok`

**Step 5: Commit**

```bash
git add docs/plans/2026-02-17-es256-migration-preflight.md README.md
git commit -m "docs: add es256 auth migration preflight checklist"
```

### Task 2: 인증 코드에서 HS256 분기 제거

**Files:**
- Modify: `backend/auth.py`
- Modify: `backend/config.py`

**Step 1: Write failing test for HS256 rejection**

```python
@patch("backend.auth.get_supabase_client")
def test_hs256_token_is_rejected_after_es256_cutover(mock_get_client: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client.auth.get_claims.side_effect = Exception("unsupported algorithm")
    mock_get_client.return_value = mock_client

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": "Bearer hs256-token"})

    assert response.status_code == 401
```

**Step 2: Run test to verify behavior fails or is ambiguous**

Run: `uv run pytest tests/test_auth.py::test_hs256_token_is_rejected_after_es256_cutover -v`
Expected: FAIL (before cleanup)

**Step 3: Write minimal implementation**

- Remove all HS256-specific branches and references.
- Remove mandatory runtime dependency on `supabase_jwt_secret` in normal auth path.
- Keep uniform 401 response for unsupported/invalid tokens.

**Step 4: Run focused auth tests**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/auth.py backend/config.py tests/test_auth.py
git commit -m "refactor: remove hs256 fallback and enforce es256 auth"
```

### Task 3: 환경 변수 및 문서에서 HS256 레거시 정리

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/security-audit.md`

**Step 1: Write failing doc grep expectation**

```text
No instructions should imply HS256 runtime support remains enabled.
```

**Step 2: Verify current HS256 mentions**

Run: `rg -n "HS256|SUPABASE_JWT_SECRET" .env.example README.md docs/security-audit.md`
Expected: matches found

**Step 3: Write minimal implementation**

- Move HS256 references to “legacy history” section only.
- Mark `SUPABASE_JWT_SECRET` as deprecated and removable.

**Step 4: Validate cleanup**

Run: `rg -n "HS256" README.md docs/security-audit.md`
Expected: only migration history context remains

**Step 5: Commit**

```bash
git add .env.example README.md docs/security-audit.md
git commit -m "docs: deprecate hs256 configuration after es256 migration"
```

### Task 4: 배포 전 회귀 검증

**Files:**
- Test: `tests/test_auth.py`
- Test: `tests/test_health.py`

**Step 1: Run auth regression tests**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS

**Step 2: Run quick API smoke tests**

Run: `uv run pytest tests/test_health.py tests/test_newsletters.py -v`
Expected: PASS

**Step 3: Optional staging canary check**

Run: `curl -i -H "Authorization: Bearer <staging_token>" http://localhost:8000/api/auth/me`
Expected: `200` with user payload

**Step 4: Final commit (if needed)**

```bash
git add -A
git commit -m "chore: finalize es256-only auth cleanup"
```
