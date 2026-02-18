# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **OVERRIDE RULE**: When this project-level CLAUDE.md conflicts with the global `~/.claude/CLAUDE.md`, **this file takes precedence**. This applies to all rules including language, commit conventions, coding style, and tooling. Subagents and teammates MUST also follow this project-level file.

## Language

- **All code artifacts in English**: commit messages, code comments, docstrings, variable names, documentation
- **Conversation with user**: Korean

## Project Overview

Curately is an AI-curated personal tech newsletter. It collects articles from RSS feeds daily, scores them against user interests using Gemini 2.5 Flash, generates Korean summaries, and serves a web UI for browsing, liking, bookmarking, and tracking interest trends over time.

**Status**: All 11 phases complete — production-ready.

## Tech Stack

- **Backend**: FastAPI + Uvicorn, Python 3.14+
- **Frontend**: React (Vite) + Tailwind CSS, Node 20+
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth (Google OAuth) — JWT verification via ES256 (JWKS) with HS256 legacy fallback
- **LLM**: Gemini 2.5 Flash (via `google-genai`)
- **Scheduler**: APScheduler (in-process) for dev; GCP Cloud Scheduler (HTTP trigger) for production
- **Deployment**: Backend on GCP Cloud Run (Docker), Frontend on Cloudflare Pages
- **Package management**: `uv` (Python), `npm` (Node)

## Development Commands

```bash
# Backend
uv sync                                        # Install Python dependencies
uv run uvicorn backend.main:app --reload       # Start backend dev server

# Frontend
cd frontend && npm install                     # Install Node dependencies
cd frontend && npm run dev                     # Start frontend dev server (MSW mocks all APIs)
VITE_ENABLE_MSW=false npm run dev              # Connect to real backend instead of mocks

# Testing
uv run pytest                                  # Run all backend tests
uv run pytest tests/test_collector.py          # Run a single test file
uv run pytest tests/test_collector.py -k test_name  # Run a single test
cd frontend && npx playwright test             # Run e2e tests (Playwright)
cd frontend && npx playwright test e2e/today.spec.ts  # Run single e2e spec

# Linting (pre-commit hooks — must use uv run)
uv run pre-commit run --all-files              # Run all linters
cd frontend && npm run lint                    # Frontend ESLint

# Dependencies
uv add <package>                               # Add production dependency
uv add --dev <package>                         # Add dev dependency
```

## Architecture

### Data Flow (Daily Pipeline — 7 stages)

`backend/services/pipeline.py` orchestrates the full pipeline via `run_daily_pipeline()`:

1. **Collect** — RSS fetch & dedup by source_url (`collector.py`)
2. **Load interests** — fetch user interest profiles from DB
3. **Time decay** — decay stale interests (7-day threshold, 0.9 factor; `interests.py`)
4. **Score** — Gemini batch relevance scoring 0.0–1.0 (`scorer.py`)
5. **Filter** — threshold 0.3, top 20 articles (`pipeline.py`)
6. **Summarize** — Korean 2–3 sentence summaries (`summarizer.py`)
7. **Persist & Digest** — save articles + generate daily digest (`digest.py`)

### Backend Structure (`backend/`)

- `main.py` — FastAPI app entrypoint, registers all 8 routers, lifespan events (scheduler, seed)
- `config.py` — Loads `config.yaml` + `.env` into typed `Settings` (pydantic-settings)
- `auth.py` — `get_current_user_id` dependency: ES256 JWKS verification + HS256 fallback, auto-upserts users
- `supabase_client.py` — Supabase client initialization
- `seed.py` — `seed_default_feeds()`: seeds config.yaml feeds into DB on startup
- `time_utils.py` — `today_kst()`: KST timezone utility used across pipeline/scheduler
- `scheduler.py` — APScheduler daily pipeline (06:00 KST) + weekly Rewind (Sunday)
- `schemas/` — Pydantic request/response models: articles, digest, feeds, interactions, interests, rewind, users
- `routers/` — API route handlers (all fully implemented):
  - `articles.py`, `auth.py`, `digest.py`, `feeds.py`, `interests.py`, `newsletters.py`, `pipeline.py`, `rewind.py`
  - `pipeline.py` — `/api/pipeline` routes protected by `X-Pipeline-Token` header (for Cloud Scheduler)
- `services/` — Business logic:
  - `collector.py` — RSS fetch & deduplication
  - `scorer.py` — Gemini batch relevance scoring
  - `summarizer.py` — Korean summary generation (basic + detailed with background/takeaways/keywords)
  - `pipeline.py` — 7-stage daily pipeline orchestrator, returns `PipelineResult` TypedDict
  - `digest.py` — `generate_daily_digest()` + `persist_digest()`, produces `DigestContent`
  - `interests.py` — `update_interests_on_like()`, `remove_interests_on_unlike()`, `apply_time_decay()`
  - `gemini.py` — `create_gemini_client()`, `call_gemini_with_retry()` (3 retries, exponential backoff)
- `scripts/` — Pre-commit hooks (`check_no_korean.py`, `check_commit_msg_no_korean.py`)

### Frontend Structure (`frontend/src/`)

- `api/client.ts` — Axios-based API client with typed endpoint functions
- `lib/supabase.ts` — Supabase JS client for auth
- `hooks/` — React hooks: `useNewsletter`, `useArticleInteractions`, `useBookmarks`, `useDigest`, `useFeeds`, `useInterests`, `useNewsletterEditions`, `useRewind`
- `types/` — TypeScript type definitions matching backend Pydantic models
- `components/` — UI components including `ProtectedRoute` (auth guard), `DigestView`, `CalendarView`, `BookmarkCard`, `TrendChart`, `RewindReport`, etc.
- `mocks/` — MSW mock data and API handlers for development
- `pages/` — Route pages: Login, Today, Digest, Archive, Bookmarks, Rewind, Settings
- Route map: `/login` → `/` (Today) → `/digest` → `/archive` → `/bookmarks` → `/rewind` → `/settings`

### Key Design Decisions

- **Shared vs. per-user data**: `articles` and `feeds` are shared; `interactions`, `user_interests`, `rewind_reports` are per-user
- **Auth**: Full JWT verification (ES256 via Supabase JWKS + HS256 legacy fallback). `get_current_user_id` dependency auto-creates users on first request.
- **Article deduplication**: UNIQUE constraint on `articles.source_url`
- **One interaction per type**: Composite UNIQUE on `(user_id, article_id, type)` — user can like AND bookmark, but not like twice

### Feedback Loop

1. **Like** → `update_interests_on_like()` extracts keywords → upserts `user_interests` (weight +1.0) → improves next day's scoring
2. **Unlike** → `remove_interests_on_unlike()` → decrements weight, deletes if ≤ 0
3. **Time decay** → `apply_time_decay()` runs during pipeline: 0.9 factor for 7-day stale interests, deletes < 0.01
4. **Bookmark** → triggers async `generate_detailed_summary()` → stored as JSON in `articles.detailed_summary`
5. **Rewind** → weekly aggregation of liked articles → comparative Gemini analysis → stored as JSON in `rewind_reports`

## Configuration

- `config.yaml` — 5 sections: `feeds` (RSS sources), `schedule` (timing), `pipeline` (thresholds), `interests` (decay tuning), `gemini` (model name)
- `.env` — Required secrets:
  - `GEMINI_API_KEY` — Gemini API access
  - `SUPABASE_URL` — Supabase project URL
  - `SUPABASE_PUBLISHABLE_KEY` (or legacy `SUPABASE_ANON_KEY`) — client-side key
  - `SUPABASE_SECRET_KEY` (or legacy `SUPABASE_SERVICE_ROLE_KEY`) — server-side key
  - `SUPABASE_JWT_SECRET` — HS256 legacy JWT verification fallback
  - `PIPELINE_TRIGGER_TOKEN` — protects `/api/pipeline` endpoints
  - `CORS_ORIGINS` — allowed origins (default: `http://localhost:5173`)
  - `ENV` — `dev` or `prod`
  - `ENABLE_INTERNAL_SCHEDULER` — `false` in production (Cloud Scheduler triggers via HTTP)

## Pre-commit Hooks

Uses `ruff` for both linting and formatting (no `black`):
- **ruff** — lint + auto-fix (`--fix --exit-non-zero-on-fix`)
- **ruff-format** — code formatting
- **mypy** — static type checking (`--ignore-missing-imports`)
- **no-korean-in-code** — blocks Hangul in Python files (exempt with `# noqa: korean-ok`)
- **no-korean-in-commit-msg** — blocks Hangul in commit messages (runs on `commit-msg` stage)
- Standard hooks: trailing-whitespace, end-of-file-fixer, check-yaml/json/toml, debug-statements, etc.

> After cloning, run `uv run pre-commit install && uv run pre-commit install --hook-type commit-msg` to enable all hooks.

## Testing

### Backend Tests (`tests/`)

- **Auth override**: `conftest.py` has an `autouse` fixture that globally overrides `get_current_user_id` → returns `MOCK_USER_ID = 1`. Tests needing real JWT behavior (e.g., `test_auth.py`) create their own FastAPI app instance.
- All Supabase calls are mocked in tests — no real DB connection needed.

### E2E Tests (`frontend/e2e/`)

Playwright specs covering all pages: today, digest, archive, bookmarks, rewind, settings, navigation, feedback-loop, login smoke test. Run with `cd frontend && npx playwright test`.

## Mock API (MSW)

The frontend uses MSW to mock all backend API endpoints during development:
- **Auto-start**: MSW starts automatically with `npm run dev`. Disable with `VITE_ENABLE_MSW=false`.
- **Mock data**: `frontend/src/mocks/data.ts` — realistic fixtures for all entities
- **Handlers**: `frontend/src/mocks/handlers.ts` — stateful handlers (like/bookmark toggles persist)
- **Production**: MSW is NOT included in production builds.

## Coding Patterns

### Supabase Client Type Handling

Supabase `response.data` returns `list[JSON]` which mypy cannot index with `str`. Always use `cast()`:

```python
from typing import Any, cast

result = client.table("feeds").select("*").execute()
rows = cast(list[dict[str, Any]], result.data)       # for list returns
row = cast(dict[str, Any], result.data[0])            # for single row
```

### Branch Naming

`feature/`, `fix/`, `chore/`, `docs/`, `refactor/` prefixes. Phase branches: `feature/phase-01-foundation`, etc.

## CI Pipeline

GitHub Actions runs **6 jobs** on every PR (all must pass):
- **checklist** — verifies PR body checklist items are all checked
- **lint** — `ruff check` + `ruff format --check`
- **type-check** — `mypy backend/ --ignore-missing-imports`
- **test** — `pytest`
- **frontend-lint** — ESLint + `tsc -b --noEmit`
- **frontend-e2e** — Playwright e2e tests (chromium)

## Deployment

- **Backend**: GCP Cloud Run via `deploy-backend.yml` (triggers on push to `main`). Uses Workload Identity Federation. Includes Cloud Scheduler setup and post-deploy smoke test.
- **Frontend**: Cloudflare Pages via `deploy-frontend.yml` (triggers on push to `main`). Includes post-deploy login smoke test.
- **Pipeline trigger**: Production uses GCP Cloud Scheduler → HTTP POST to `/api/pipeline/run` with `X-Pipeline-Token` header (instead of in-process APScheduler).

## Pull Request Workflow

1. **Always attach labels** when creating a PR (e.g., `feature`, `fix`, `refactor`, `docs`, `chore`). Create the label first if it doesn't exist.
2. **Include PR checklist** — CI's `checklist` job verifies all items are checked.
3. **Watch CI checks** — wait for all 6 jobs to pass.
4. **Merge immediately** once all CI checks pass. Use `gh pr merge --merge --delete-branch`.

## Reference

- Full design document: `docs/plans/2026-02-13-tech-newsletter-design.md`
- Implementation phases: `docs/plans/implementation-phases.md`
- Migration plans: `docs/plans/2026-02-17-*.md`, `docs/migrations/`
