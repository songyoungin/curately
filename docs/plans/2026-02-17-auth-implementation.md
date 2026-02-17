# Auth Implementation Plan: Supabase Google OAuth

## 1. Overview

Replace the default-user MVP auth with real Supabase Google OAuth.
After this change, unauthenticated requests are rejected and every
user-scoped operation reads `user_id` from the JWT instead of a
hardcoded default user.

### Decisions

| Item | Decision |
|------|----------|
| Auth provider | Supabase Auth — Google OAuth |
| Transition mode | **Full** (default user removed, OAuth required) |
| Existing default user data | Keep as-is, no migration |
| Multi-user support | Schema ready, but **single-user OAuth** for now |
| JWT verification | Local (PyJWT + Supabase JWT secret) — no API call per request |

---

## 2. Prerequisites (before coding)

### 2.1 Google Cloud Console

1. Create OAuth 2.0 credentials (Web application)
2. Authorized redirect URI: `https://<supabase-project>.supabase.co/auth/v1/callback`
3. Note the **Client ID** and **Client Secret**

### 2.2 Supabase Dashboard

1. **Authentication → Providers → Google**: Enable, paste Client ID + Secret
2. **Settings → API → JWT Secret**: Copy for backend `.env`
3. **URL Configuration → Site URL**: Set to `http://localhost:5173` (dev)
4. **URL Configuration → Redirect URLs**: Add `http://localhost:5173`

### 2.3 Environment Variables

Backend `.env` — add:
```
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

Frontend `.env` — create:
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key-here
```

---

## 3. Implementation Tasks

### Task 1: Backend — Auth dependency (JWT verification)

**New file**: `backend/auth.py`

Create a FastAPI dependency that extracts and verifies the JWT from
the `Authorization: Bearer <token>` header.

```python
# Pseudocode
async def get_current_user_id(authorization: str = Header(...)) -> int:
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"],
                         audience="authenticated")
    email = payload["email"]
    # Find or create user in our users table
    user = upsert_user(email=email, google_sub=payload["sub"])
    return user["id"]
```

Key points:
- Use `PyJWT` library for local JWT verification (add via `uv add PyJWT`)
- Extract `email` and `sub` from JWT claims
- Upsert into `users` table (first login creates row, subsequent logins update `last_login_at`)
- Return our BIGSERIAL `user_id` (not Supabase auth UUID)
- Raise `HTTPException(401)` on invalid/missing/expired token

**Changes to `backend/config.py`**:
- Add `supabase_jwt_secret: str` to Settings

**Tests**: Mock JWT creation with `PyJWT`, test valid/invalid/expired/missing tokens.

---

### Task 2: Backend — Auth router endpoints

**File**: `backend/routers/auth.py` (currently empty stub)

| Endpoint | Description |
|----------|-------------|
| `GET /api/auth/me` | Return current user info from JWT. Uses `get_current_user_id` dependency, then fetches full user row. |
| `POST /api/auth/logout` | Optional — Supabase handles logout client-side, but endpoint can invalidate server-side cache if needed. |

Note: `POST /api/auth/google` is NOT needed — Supabase JS SDK handles
the OAuth flow entirely client-side. The backend only verifies JWTs.

---

### Task 3: Backend — Replace `_get_default_user_id()` across all routers

Replace every occurrence of the hardcoded default user lookup with the
`get_current_user_id` FastAPI dependency.

| File | Change |
|------|--------|
| `routers/articles.py` | Remove `_get_default_user_id()`, add `user_id: int = Depends(get_current_user_id)` to endpoints that need it |
| `routers/newsletters.py` | Same — `get_today_newsletter`, `get_newsletter_by_date` |
| `routers/rewind.py` | Same — all 4 endpoints |
| `routers/interests.py` | Same — `list_interests` |

Also remove the duplicated `_attach_interaction_flags` helper from
individual routers and extract to a shared module if desired.

Endpoints that do NOT need auth:
- `GET /api/health` — public
- `GET /api/feeds` — shared data, read-only (keep public or protect — decide)
- `POST /api/pipeline/run` — dev-only (consider admin-only or remove in prod)

---

### Task 4: Backend — Update scheduler for dynamic user lookup

**File**: `backend/scheduler.py`

The `_run_weekly_rewind_job()` currently calls `_get_default_user_id()`.
Change to query all users from the `users` table and generate a rewind
report for each.

```python
async def _run_weekly_rewind_job():
    client = get_supabase_client()
    users = client.table("users").select("id").execute()
    for user in users.data:
        report = await generate_rewind_report(client, user["id"])
        await persist_rewind_report(client, user["id"], report, ...)
```

Similarly, the daily pipeline's interest loading
(`_load_user_interests` in `services/pipeline.py`) currently
hardcodes `default@curately.local`. Change to accept `user_id`
parameter, or aggregate interests across all users.

---

### Task 5: Backend — Remove seed_default_user

**File**: `backend/seed.py`
- Remove `seed_default_user()` function and `DEFAULT_USER_EMAIL` / `DEFAULT_USER_NAME` constants
- Keep `seed_default_feeds()` (feeds are shared, not per-user)

**File**: `backend/main.py`
- Remove `seed_default_user(client)` call from lifespan
- Remove import

**File**: All routers that import `DEFAULT_USER_EMAIL` from `backend/seed`
- Should already be cleaned up by Task 3

---

### Task 6: Frontend — Supabase client (non-nullable)

**File**: `frontend/src/lib/supabase.ts`

Change from nullable to required:
```typescript
// Before
export const supabase: SupabaseClient | null = ...

// After
if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are required');
}
export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey);
```

This removes all `if (supabase)` null checks downstream.

---

### Task 7: Frontend — Auth context + provider

**New file**: `frontend/src/contexts/AuthContext.tsx`

```typescript
interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}
```

- Listen to `supabase.auth.onAuthStateChange()` for session changes
- On session acquired: call `GET /api/auth/me` to get our user record
- Expose `signIn()` → `supabase.auth.signInWithOAuth({ provider: 'google' })`
- Expose `signOut()` → `supabase.auth.signOut()`

**File**: `frontend/src/App.tsx`
- Wrap with `<AuthProvider>`

---

### Task 8: Frontend — Login page + route guard

**New file**: `frontend/src/pages/Login.tsx`

- Centered card with app logo + "Sign in with Google" button
- Calls `signIn()` from AuthContext

**New file**: `frontend/src/components/ProtectedRoute.tsx`

```typescript
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner />;
  if (!user) return <Navigate to="/login" />;
  return children;
}
```

**File**: `frontend/src/App.tsx`
- Add `/login` route
- Wrap all other routes with `<ProtectedRoute>`

**File**: `frontend/src/components/NavBar.tsx`
- Show user name/avatar (from `useAuth().user`)
- Add logout button

---

### Task 9: Frontend — 401 handling

**File**: `frontend/src/api/client.ts`

Replace the current 401 stub:
```typescript
// Before
console.error('Unauthorized request — session may have expired');

// After
window.location.href = '/login';
```

---

### Task 10: Update MSW mock handlers

**File**: `frontend/src/mocks/handlers.ts`

- Add mock handler for `GET /api/auth/me` returning a mock user
- Update handlers to not require auth in dev mode
- Ensure MSW intercepts before auth checks

---

## 4. Verification Criteria (Ralph Loop)

### 4.1 Automated — pytest (after each task)

```bash
uv run pre-commit run --all-files   # lint + format + type check
uv run pytest                        # all tests pass
```

| Test | Verification |
|------|-------------|
| Valid JWT → `get_current_user_id` returns user_id | Mock JWT with PyJWT, assert returned ID |
| Expired JWT → 401 | Assert HTTPException status |
| Missing Authorization header → 401 | Assert HTTPException status |
| Malformed token → 401 | Assert HTTPException status |
| First login creates user row in DB | Mock Supabase, verify insert called |
| Subsequent login updates `last_login_at` | Mock Supabase, verify update called |
| `GET /api/auth/me` returns user info | TestClient with mocked auth |
| All protected endpoints reject unauthenticated requests | TestClient without auth header → 401 |
| Scheduler generates rewind for all users | Mock DB with N users, verify N reports |

### 4.2 Supabase MCP verification

Run these SQL queries after deploying to verify real DB state:

```sql
-- 1. Verify user was created after OAuth login
SELECT id, email, google_sub, last_login_at
FROM users
WHERE google_sub IS NOT NULL;

-- 2. Verify RLS blocks cross-user access
-- (Set role to authenticated with user A's JWT, try to read user B's data)
SET request.jwt.claims = '{"sub":"user-a-uuid","email":"a@test.com"}';
SET role TO authenticated;
SELECT * FROM interactions WHERE user_id = <user_b_id>;
-- Expected: 0 rows

-- 3. Verify old default user data is untouched
SELECT * FROM users WHERE email = 'default@curately.local';
SELECT COUNT(*) FROM interactions WHERE user_id = <default_user_id>;
```

### 4.3 Playwright MCP verification

Run these browser automation checks against `http://localhost:5173`:

| Step | Action | Expected |
|------|--------|----------|
| 1 | `browser_navigate` to `/` | Redirect to `/login` (no auth) |
| 2 | `browser_snapshot` on `/login` | "Sign in with Google" button visible |
| 3 | `browser_click` on sign-in button | Redirects to `accounts.google.com` or Supabase OAuth URL |
| 4 | After OAuth complete, `browser_navigate` to `/` | Today page renders with articles |
| 5 | `browser_snapshot` on NavBar | User name/avatar displayed, logout button visible |
| 6 | `browser_click` logout button | Redirect to `/login` |
| 7 | `browser_navigate` to `/bookmarks` | Redirect to `/login` (session cleared) |

For automated testing without real Google account:
```sql
-- Create test user via Supabase MCP
-- Then use Supabase admin API to generate a session token
-- Inject token into Playwright via browser_evaluate:
-- localStorage.setItem('supabase.auth.token', JSON.stringify({...}))
```

### 4.4 Full success criteria checklist

- [ ] `uv run pre-commit run --all-files` passes
- [ ] `uv run pytest` — all tests pass (existing + new auth tests)
- [ ] `cd frontend && npm run build` — no TypeScript errors
- [ ] Unauthenticated `GET /api/articles/bookmarked` → 401
- [ ] Unauthenticated `GET /api/newsletters/today` → 401
- [ ] Authenticated requests return correct user-scoped data
- [ ] `GET /api/health` works without auth
- [ ] `GET /api/feeds` works without auth (shared data)
- [ ] Login page renders at `/login`
- [ ] OAuth redirect works (Playwright)
- [ ] Logged-in user sees their name in NavBar (Playwright)
- [ ] Logout clears session and redirects (Playwright)
- [ ] Old default user data remains in DB (Supabase MCP)
- [ ] Scheduler generates rewind for OAuth users (pytest)
- [ ] `seed_default_user` completely removed
- [ ] `seed_default_feeds` still runs on startup
- [ ] No secrets in code or client bundle

---

## 5. Files Changed Summary

### New files
| File | Purpose |
|------|---------|
| `backend/auth.py` | JWT verification dependency |
| `frontend/src/contexts/AuthContext.tsx` | Auth state management |
| `frontend/src/pages/Login.tsx` | Login page |
| `frontend/src/components/ProtectedRoute.tsx` | Route guard |
| `frontend/.env.example` | Frontend env template |

### Modified files
| File | Change |
|------|--------|
| `backend/config.py` | Add `supabase_jwt_secret` |
| `backend/main.py` | Remove `seed_default_user`, keep `seed_default_feeds` |
| `backend/seed.py` | Remove `seed_default_user()`, keep `seed_default_feeds()` |
| `backend/routers/auth.py` | Implement `GET /api/auth/me` |
| `backend/routers/articles.py` | Use `Depends(get_current_user_id)` |
| `backend/routers/newsletters.py` | Same |
| `backend/routers/rewind.py` | Same |
| `backend/routers/interests.py` | Same |
| `backend/scheduler.py` | Dynamic user lookup |
| `backend/services/pipeline.py` | Parameterize user_id |
| `frontend/src/lib/supabase.ts` | Non-nullable client |
| `frontend/src/App.tsx` | AuthProvider + route guard + /login route |
| `frontend/src/api/client.ts` | 401 → redirect to /login |
| `frontend/src/components/NavBar.tsx` | User info + logout |
| `frontend/src/mocks/handlers.ts` | Mock auth endpoint |
| `.env.example` | Add `SUPABASE_JWT_SECRET` |

### Dependencies
| Package | Purpose |
|---------|---------|
| `PyJWT` (backend) | Local JWT verification |

---

## 6. Recommended Implementation Order

```
Task 1 (auth dependency) → Task 2 (auth router)
    → Task 3 (replace _get_default_user_id)
    → Task 4 (scheduler) + Task 5 (remove seed)
    → Task 6 (supabase non-null) → Task 7 (auth context)
    → Task 8 (login + route guard) → Task 9 (401 handling)
    → Task 10 (MSW mocks)
```

Tasks 1-5 are backend-only and can be tested with pytest alone.
Tasks 6-10 are frontend and need Playwright for full verification.
