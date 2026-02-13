# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

- **All code artifacts in English**: commit messages, code comments, docstrings, variable names, documentation
- **Conversation with user**: Korean

## Project Overview

Curately is an AI-curated personal tech newsletter. It collects articles from RSS feeds daily, scores them against user interests using Gemini 2.5 Flash, generates Korean summaries, and serves a web UI for browsing, liking, bookmarking, and tracking interest trends over time.

**Status**: Early stage — design document complete, implementation not yet started.

## Tech Stack

- **Backend**: FastAPI + Uvicorn, Python 3.14+
- **Frontend**: React (Vite) + Tailwind CSS, Node 20+
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth (Google OAuth, MVP uses default user without auth)
- **LLM**: Gemini 2.5 Flash (via `google-genai`)
- **Scheduler**: APScheduler (in-process, inside FastAPI)
- **Package management**: `uv` (Python), `npm` (Node)

## Development Commands

```bash
# Backend
uv sync                                        # Install Python dependencies
uv run uvicorn backend.main:app --reload       # Start backend dev server

# Frontend
cd frontend && npm install                     # Install Node dependencies
cd frontend && npm run dev                     # Start frontend dev server

# Testing
uv run pytest                                  # Run all tests
uv run pytest tests/test_collector.py          # Run a single test file
uv run pytest tests/test_collector.py -k test_name  # Run a single test

# Linting (pre-commit hooks)
pre-commit run --all-files                     # Run all linters

# Dependencies
uv add <package>                               # Add production dependency
uv add --dev <package>                         # Add dev dependency
```

## Architecture

### Data Flow (Daily Pipeline)

RSS Feeds → **Collector** (feedparser, dedup by source_url) → **Scorer** (Gemini batch scoring 0.0–1.0 against user interests) → **Filter** (threshold 0.3, top 20) → **Summarizer** (Gemini Korean 2–3 sentence summaries) → **Supabase DB**

### Backend Structure (`backend/`)

- `main.py` — FastAPI app entrypoint
- `config.py` — Loads `config.yaml` + `.env` into typed settings
- `supabase_client.py` — Supabase client initialization
- `scheduler.py` — APScheduler daily pipeline (06:00) + weekly Rewind (Sunday)
- `routers/` — API route handlers: auth, newsletters, articles, feeds, interests, rewind
- `services/` — Business logic:
  - `collector.py` — RSS fetch & deduplication
  - `scorer.py` — Gemini relevance scoring (batched, 5–10 articles per call)
  - `summarizer.py` — Summary generation (basic + detailed on bookmark)
  - `interests.py` — Interest profile updates & time decay (0.9 factor per 7 days)
  - `rewind.py` — Weekly trend analysis & report generation

### Frontend Structure (`frontend/src/`)

- `api/client.ts` — Axios-based API client
- `lib/supabase.ts` — Supabase JS client for auth
- Pages: Today (main feed by category), Archive (calendar browse), Bookmarks (detailed summaries), Rewind (weekly trends), Settings (feeds + interests)

### Key Design Decisions

- **Shared vs. per-user data**: `articles` and `feeds` are shared across users; `interactions`, `user_interests`, `rewind_reports` are per-user
- **MVP auth strategy**: Single default user auto-created, no auth required; schema already supports multi-user for when OAuth is enabled
- **Article deduplication**: UNIQUE constraint on `articles.source_url`
- **One interaction per type**: Composite UNIQUE on `(user_id, article_id, type)` — user can like AND bookmark, but not like twice

### Feedback Loop

1. **Like** → extracts keywords → upserts `user_interests` (weight +1) → improves next day's scoring
2. **Bookmark** → triggers async Gemini detailed summary → stored in `articles.detailed_summary`
3. **Rewind** → weekly aggregation of liked articles → comparative Gemini analysis → stored as JSON in `rewind_reports`

## Configuration

- `config.yaml` — RSS feed list, schedule settings, relevance thresholds
- `.env` — Secrets: `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

## Reference

- Full design document: `docs/plans/2026-02-13-tech-newsletter-design.md` (DB schema, API endpoints, component hierarchy, pipeline details)
