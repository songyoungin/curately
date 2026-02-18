# Supabase auth.get_claims Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** backend JWT 검증 로직을 PyJWT 직접 구현에서 `supabase.auth.get_claims()` 중심으로 전환해 인증 코드 복잡도를 낮춘다.

**Architecture:** 인증 경계(`backend/auth.py`)는 유지하고, 토큰 검증과 claim 파싱을 SDK에 위임한다. 기존 에러 메시지 계약(401/500)과 사용자 upsert 흐름은 그대로 유지해 API 동작 회귀를 막는다.

**Tech Stack:** FastAPI, supabase-py 2.28.x, pytest, unittest.mock

---

### Task 1: get_claims 기반 검증 테스트 추가

**Files:**
- Modify: `tests/test_auth.py`

**Step 1: Write the failing test**

```python
@patch("backend.auth.get_supabase_client")
def test_uses_supabase_get_claims_for_token_verification(mock_get_client: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client.auth.get_claims.return_value = MagicMock(claims={
        "email": "test@example.com",
        "sub": "google-sub-123",
    })
    mock_client.table = _make_mock_client(existing_user=MOCK_USER_ROW).table
    mock_get_client.return_value = mock_client

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": "Bearer any-token"})

    assert response.status_code == 200
    mock_client.auth.get_claims.assert_called_once_with(jwt="any-token")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py::test_uses_supabase_get_claims_for_token_verification -v`
Expected: FAIL because code still calls PyJWT decode directly

**Step 3: Write minimal implementation target**

```python
# backend/auth.py
claims_response = client.auth.get_claims(jwt=token)
payload = claims_response.claims
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth.py::test_uses_supabase_get_claims_for_token_verification -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_auth.py backend/auth.py
git commit -m "test: add auth.get_claims verification coverage"
```

### Task 2: auth.py에서 PyJWT/JWKS 제거

**Files:**
- Modify: `backend/auth.py`

**Step 1: Write failing regression tests for error mapping**

```python
@patch("backend.auth.get_supabase_client")
def test_get_claims_invalid_token_maps_to_401(mock_get_client: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client.auth.get_claims.side_effect = Exception("invalid")
    mock_get_client.return_value = mock_client

    app = _build_test_app()
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py::test_get_claims_invalid_token_maps_to_401 -v`
Expected: FAIL due current exception handling mismatch

**Step 3: Write minimal implementation**

- Remove `jwt`, `PyJWKClient`, `_get_jwks_client()` usage.
- Keep header format checks.
- Add SDK error mapping rules:
  - token invalid/expired -> 401
  - SDK misconfiguration/unexpected error -> 500 with safe message

Example skeleton:

```python
try:
    claims_response = client.auth.get_claims(jwt=token)
    payload = claims_response.claims
except Exception as exc:
    logger.error("Token verification failed via Supabase SDK: %s", exc)
    raise HTTPException(status_code=401, detail="Invalid token")
```

**Step 4: Run focused auth tests**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS (including existing missing-header/invalid-format tests)

**Step 5: Commit**

```bash
git add backend/auth.py tests/test_auth.py
git commit -m "refactor: migrate jwt verification to supabase auth.get_claims"
```

### Task 3: 설정/문서 정리

**Files:**
- Modify: `backend/config.py`
- Modify: `.env.example`
- Modify: `README.md`

**Step 1: Write failing doc/config checklist**

```text
- backend/config.py still requires SUPABASE_JWT_SECRET for normal flow
- .env.example and README do not describe get_claims-based verification
```

**Step 2: Verify current usage**

Run: `rg -n "supabase_jwt_secret|SUPABASE_JWT_SECRET" backend/config.py .env.example README.md`
Expected: matches present

**Step 3: Write minimal implementation**

- Mark `SUPABASE_JWT_SECRET` as legacy fallback only.
- Update README auth section to explain SDK-based verification path.

**Step 4: Validate references**

Run: `rg -n "SUPABASE_JWT_SECRET" .env.example README.md`
Expected: only legacy/optional context remains

**Step 5: Commit**

```bash
git add backend/config.py .env.example README.md
git commit -m "docs: document supabase sdk claims verification"
```

### Task 4: 통합 검증

**Files:**
- Test: `tests/test_auth.py`

**Step 1: Run full auth test module**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS

**Step 2: Run API regression smoke tests**

Run: `uv run pytest tests/test_health.py tests/test_pipeline_routes.py -v`
Expected: PASS

**Step 3: Final commit (if needed)**

```bash
git add -A
git commit -m "chore: finalize auth.get_claims migration"
```
