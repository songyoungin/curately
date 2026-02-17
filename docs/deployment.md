# Deployment Guide

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.14+ | Backend runtime |
| Node.js | 20+ | Frontend build/dev |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| [Supabase](https://supabase.com/) project | — | PostgreSQL database + auth |
| [Gemini API key](https://ai.google.dev/) | — | AI scoring & summarization |

---

## Local Development Setup

### 1. Clone & Install

```bash
git clone git@github.com:songyoungin/curately.git
cd curately

# Backend dependencies
uv sync

# Pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Environment Configuration

Create `.env` in the project root:

```env
GEMINI_API_KEY=your-gemini-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Edit `config.yaml` to configure RSS feeds and schedule settings.

### 3. Database Schema

Apply the schema to your Supabase project:

1. Open the [Supabase SQL Editor](https://supabase.com/dashboard/project/_/sql)
2. Execute the SQL from `docs/plans/2026-02-13-tech-newsletter-design.md` (Section 2: Database Schema)
3. This creates: `users`, `feeds`, `articles`, `interactions`, `user_interests`, `rewind_reports` tables
4. RLS policies are included in the schema

### 4. Run Development Servers

```bash
# Terminal 1: Backend (includes APScheduler for daily pipeline)
uv run uvicorn backend.main:app --reload

# Terminal 2: Frontend (MSW auto-mocks all APIs in dev mode)
cd frontend && npm run dev
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

**Note:** The frontend can run independently using MSW mock data — no backend needed for UI development.

---

## Running Tests

### Backend (pytest)

```bash
uv run pytest                                  # All tests
uv run pytest tests/test_collector.py          # Single file
uv run pytest tests/test_collector.py -k test_name  # Single test
```

### Frontend (Playwright E2E)

```bash
cd frontend
npx playwright test                            # All E2E tests
npx playwright test --ui                       # Interactive UI mode
npx playwright test today.spec.ts              # Single spec file
```

### Linting

```bash
uv run pre-commit run --all-files              # All linters
```

---

## Daily Pipeline

The backend runs an APScheduler job at 06:00 daily:

1. **Collect** — Fetches RSS feeds, deduplicates by `source_url`
2. **Score** — Gemini batch scoring (0.0–1.0) against user interests
3. **Filter** — Threshold 0.3, top 20 articles
4. **Summarize** — Gemini generates Korean summaries

Manual trigger:

```bash
curl -X POST http://localhost:8000/api/pipeline/run
```

---

## Troubleshooting FAQ

### Backend won't start

**Symptom:** `ModuleNotFoundError` or import errors

**Fix:**
```bash
uv sync          # Reinstall dependencies
uv run uvicorn backend.main:app --reload
```

### Frontend MSW not working

**Symptom:** API calls fail in dev mode, "Failed to fetch" errors

**Fix:**
1. Ensure `public/mockServiceWorker.js` exists
2. If missing: `cd frontend && npx msw init public/`
3. Restart dev server: `npm run dev`

### Supabase connection fails

**Symptom:** `ConnectionError` or `AuthApiError`

**Fix:**
1. Verify `.env` values are correct
2. Check Supabase project is running (not paused)
3. Ensure `SUPABASE_SERVICE_ROLE_KEY` has admin access

### Pre-commit hooks fail

**Symptom:** Commit blocked by linting errors

**Fix:**
```bash
uv run ruff check . --fix     # Auto-fix lint issues
uv run ruff format .          # Auto-format code
```

### Playwright tests fail

**Symptom:** Browser not found or timeout errors

**Fix:**
```bash
cd frontend
npx playwright install chromium --with-deps    # Install browser
npx playwright test --headed                   # Debug visually
```

### Korean text in code/commits blocked

**Symptom:** Pre-commit hook blocks Hangul characters

**Note:** This is intentional — all code artifacts must be in English. Use `# noqa: korean-ok` to exempt specific lines if needed. Commit messages must also be in English.
