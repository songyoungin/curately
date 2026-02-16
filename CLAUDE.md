# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **OVERRIDE RULE**: When this project-level CLAUDE.md conflicts with the global `~/.claude/CLAUDE.md`, **this file takes precedence**. This applies to all rules including language, commit conventions, coding style, and tooling. Subagents and teammates MUST also follow this project-level file.

## Language

- **All code artifacts in English**: commit messages, code comments, docstrings, variable names, documentation
- **Conversation with user**: Korean

## Project Overview

Curately is an AI-curated personal tech newsletter. It collects articles from RSS feeds daily, scores them against user interests using Gemini 2.5 Flash, generates Korean summaries, and serves a web UI for browsing, liking, bookmarking, and tracking interest trends over time.

**Status**: Phase 3 complete — RSS collection, AI scoring, and summarization implemented.

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

# Linting (pre-commit hooks — must use uv run)
uv run pre-commit run --all-files              # Run all linters

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
- `scheduler.py` — APScheduler daily pipeline (06:00) + weekly Rewind (Sunday) *(stub)*
- `routers/` — API route handlers
  - `feeds.py` — Feed CRUD (list, create, delete, update)
  - `articles.py`, `auth.py`, `interests.py`, `newsletters.py`, `rewind.py` — *(stubs)*
- `services/` — Business logic
  - `collector.py` — RSS fetch & deduplication
  - `scorer.py` — Gemini batch relevance scoring (0.0–1.0, configurable batch size)
  - `summarizer.py` — Korean summary generation (basic 2–3 sentences + detailed with background/takeaways/keywords)
- `scripts/` — Utility scripts
  - `check_no_korean.py` — Pre-commit hook: blocks Hangul in Python files
  - `check_commit_msg_no_korean.py` — Commit-msg hook: blocks Hangul in commit messages

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

## Pre-commit Hooks

Uses `ruff` for both linting and formatting (no `black`):
- **ruff** — lint + auto-fix (`--fix --exit-non-zero-on-fix`)
- **ruff-format** — code formatting (replaces black)
- **mypy** — static type checking (`--ignore-missing-imports`)
- **no-korean-in-code** — blocks Hangul characters in Python files (exempt with `# noqa: korean-ok`)
- **no-korean-in-commit-msg** — blocks Hangul characters in commit messages (runs on `commit-msg` stage)
- Standard hooks: trailing-whitespace, end-of-file-fixer, check-yaml/json/toml, debug-statements, etc.

> After cloning, run `uv run pre-commit install && uv run pre-commit install --hook-type commit-msg` to enable all hooks including commit message checks.

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

Follow the convention from `docs/plans/implementation-phases.md`:

```
feature/phase-01-foundation
feature/phase-02-rss-collection
feature/phase-03-ai-pipeline
...
```

For non-phase work: `chore/`, `fix/`, `docs/`, `refactor/` prefixes.

## Pull Request Workflow

1. **Always attach labels** when creating a PR (e.g., `feature`, `fix`, `refactor`, `docs`, `chore`). Create the label first if it doesn't exist.
2. **Watch CI checks** after PR creation — wait for all checks to complete.
3. **Merge immediately** once all CI checks pass. Use `gh pr merge --merge --delete-branch`.

## CI Pipeline

GitHub Actions runs 3 jobs on every PR:
- **lint** — `ruff check`
- **test** — `pytest`
- **type-check** — `mypy backend/ --ignore-missing-imports`

All 3 must pass before merging.

## Implementation Progress

See `docs/plans/implementation-phases.md` for the full phase plan.

| Phase | Status |
|-------|--------|
| Phase 1: Project Foundation | Done |
| Phase 2: RSS Collection Pipeline | Done |
| Phase 3: AI Pipeline (Scoring & Summarization) | Done |
| Phase 4: Daily Pipeline & Newsletter API | Done |
| Phase 5: User Interactions & Feedback Loop | Done |
| Phase 6: Rewind Weekly Analysis | Done |
| Phase 7: Frontend Foundation | Not started |
| Phase 8: Today Page & Article Interactions | Not started |
| Phase 9: Archive, Bookmarks & Settings | Not started |
| Phase 10: Rewind UI & Polish | Not started |
| Phase 11: Integration Testing & Final QA | Not started |

## Reference

- Full design document: `docs/plans/2026-02-13-tech-newsletter-design.md` (DB schema, API endpoints, component hierarchy, pipeline details)
- Implementation phases: `docs/plans/implementation-phases.md` (task breakdown, team roles, acceptance criteria)
