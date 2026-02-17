# Curately Implementation Phases

> Reference: [Design Document](./2026-02-13-tech-newsletter-design.md)

## Team Roles

| # | Role | Responsibility |
|---|------|----------------|
| 1 | Planner (기획자) | Validates implementation against design requirements |
| 2 | Backend Developer (백엔드 개발자) | Backend engineering specialist |
| 3 | Frontend Developer (프론트엔드 개발자) | Frontend engineering specialist |
| 4 | AI Developer (AI 개발자) | Reviews LLM usage, prompt design, and cost optimization |
| 5 | Code Reviewer (코드 리뷰어) | Senior engineer — reviews design, efficiency, stability, scalability |
| 6 | Security Engineer (보안 담당자) | Reviews code for security vulnerabilities |
| 7 | Designer (디자이너) | Reviews web app design and component usability |
| 8 | QA Tester (QA 테스터) | Tests product quality at each phase |
| 9 | Decision Maker (의사결정자/리더) | Decides whether to proceed to the next phase |

## Dependency Graph

```
Phase 1 (Foundation)
    ├──→ Phase 2 (RSS Collection)
    │        └──→ Phase 3 (AI Pipeline)
    │                 └──→ Phase 4 (Daily Pipeline & Newsletter API)
    │                          └──→ Phase 5 (Interactions & Feedback)
    │                                   └──→ Phase 6 (Rewind)
    │
    └──→ Phase 7 (Frontend Foundation)  ※ Can start after Phase 4
             └──→ Phase 8 (Today Page)         ← Needs Phase 5 API
                      └──→ Phase 9 (Archive/Bookmarks/Settings)  ← Needs Phase 5,6 API
                               └──→ Phase 10 (Rewind UI & Polish) ← Needs Phase 6 API

All phases ──→ Phase 11 (Integration & QA)
```

**Parallelization opportunity:** Phases 5–6 (backend) and Phases 7–8 (frontend) can run concurrently to reduce total timeline.

---

## Phase 1: Project Foundation

### Goal

Set up development infrastructure — runnable FastAPI skeleton with database schema, config system, and Supabase client.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 1.1 | Directory structure | Create `backend/`, `backend/routers/`, `backend/services/`, `frontend/`, `tests/` with `__init__.py` files |
| 1.2 | Python dependencies | Add to `pyproject.toml`: fastapi, uvicorn, supabase, feedparser, google-genai, apscheduler, pyyaml, pydantic, httpx |
| 1.3 | Dev dependencies | Add: pytest, pytest-asyncio, httpx (test client), pre-commit, black, ruff, mypy |
| 1.4 | Config system | `config.yaml` template (RSS feeds, schedule, thresholds) + `backend/config.py` (Pydantic Settings loading yaml + .env) |
| 1.5 | Environment files | `.env.example` with GEMINI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY |
| 1.6 | Supabase client | `backend/supabase_client.py` — client initialization helper |
| 1.7 | FastAPI skeleton | `backend/main.py` — app factory with CORS, router mounts, health endpoint (`GET /api/health`) |
| 1.8 | DB schema | SQL file (`docs/schema.sql`) with all 6 tables + indexes from design doc |
| 1.9 | Pydantic models | Request/response schemas for each entity (articles, feeds, interactions, interests, rewind_reports, users) |
| 1.10 | Default user | MVP default user seeding logic (auto-create on first run) |
| 1.11 | Pre-commit setup | Configure black, ruff, mypy hooks |
| 1.12 | .gitignore update | Ensure .env, .venv, __pycache__, node_modules, .pytest_cache are excluded |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Backend Developer | Builds everything |
| Planner | Verifies DB schema matches design doc exactly (6 tables, all columns, constraints, indexes) |
| Code Reviewer | Reviews project structure, config patterns, Pydantic model design |
| Security Engineer | Validates .env secret management, .gitignore coverage, no hardcoded credentials |

### Acceptance Criteria

- [ ] `uv sync` installs all dependencies without errors
- [ ] `uv run uvicorn backend.main:app --reload` starts successfully
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] DB schema SQL is valid and matches design document
- [ ] `.env.example` documents all required environment variables
- [ ] `config.yaml` contains RSS feed list, schedule settings, threshold defaults
- [ ] `pre-commit run --all-files` passes

### Reference

- Design doc §8 (Project Directory Structure)
- Design doc §9 (Dependencies)
- Design doc §4 (Database Schema)

---

## Phase 2: RSS Collection Pipeline

### Goal

Collect articles from RSS feeds with deduplication — the first stage of the daily pipeline.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 2.1 | collector.py | `backend/services/collector.py` — fetch all active feeds via feedparser, deduplicate by `source_url`, return list of new articles |
| 2.2 | Feed router | `backend/routers/feeds.py` — `GET /api/feeds`, `POST /api/feeds`, `DELETE /api/feeds/:id`, `PATCH /api/feeds/:id` |
| 2.3 | Feed validation | Validate RSS URL format, check feed is parseable before saving |
| 2.4 | Error handling | Graceful handling of unreachable feeds, malformed RSS, timeouts |
| 2.5 | Tests | `tests/test_collector.py` — collection, deduplication, error cases, feed CRUD |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Backend Developer | Implements collector service + Feed API |
| Planner | Verifies deduplication logic matches design (UNIQUE on `source_url`) |
| Code Reviewer | Reviews error handling, async patterns, code structure |
| QA Tester | Tests with various real RSS feeds (Hacker News, TechCrunch, etc.) |

### Acceptance Criteria

- [ ] `POST /api/feeds` adds a new RSS feed to the database
- [ ] `GET /api/feeds` returns all feeds with status
- [ ] `PATCH /api/feeds/:id` toggles active/inactive
- [ ] `DELETE /api/feeds/:id` removes a feed
- [ ] Collector fetches articles from all active feeds
- [ ] Duplicate articles (same `source_url`) are skipped
- [ ] Unreachable feeds are handled gracefully without crashing the pipeline
- [ ] Tests pass: `uv run pytest tests/test_collector.py`

### Reference

- Design doc §7, Stage 1 (RSS Collection)
- Design doc §5 (Feed Management endpoints)
- Design doc §4, `feeds` and `articles` tables

---

## Phase 3: AI Pipeline — Scoring & Summarization

### Goal

Integrate Gemini 2.5 Flash for relevance scoring and Korean summary generation.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 3.1 | scorer.py | `backend/services/scorer.py` — batch scoring (5–10 articles per call), interest profile injection, returns score (0.0–1.0) + categories + keywords |
| 3.2 | Scoring prompt | Design Gemini prompt: input = user interests + article title/content, output = JSON with score, categories, keywords |
| 3.3 | summarizer.py | `backend/services/summarizer.py` — basic summary (2–3 sentence Korean), detailed summary (background + 5 takeaways + keywords) |
| 3.4 | Summary prompts | Design basic and detailed summary prompts |
| 3.5 | Response parsing | Robust JSON parsing from Gemini responses with fallback handling |
| 3.6 | Rate limiting | Respect Gemini API rate limits, implement retry with backoff |
| 3.7 | Tests | `tests/test_scorer.py`, `tests/test_summarizer.py` — mocked Gemini responses |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Backend Developer | Implements services |
| AI Developer | **Lead** — designs prompts, batch strategy, response schema, cost optimization review |
| Code Reviewer | Reviews batch processing logic, error handling, retry patterns |
| Security Engineer | Validates API key management, no key leakage in logs |

### Acceptance Criteria

- [ ] Scorer processes articles in batches of 5–10
- [ ] Each article receives: relevance score (0.0–1.0), categories list, keywords list
- [ ] User interest profile is injected into scoring prompt
- [ ] Basic summary: 2–3 sentences in Korean, focuses on key takeaways
- [ ] Detailed summary: background context, 3–5 takeaways, related keywords
- [ ] Gemini API errors are handled gracefully (retry, fallback)
- [ ] API key is never logged or exposed
- [ ] Tests pass with mocked Gemini responses

### Key Design Decisions

- **Batch size**: 5–10 articles per scoring call (balance between cost and context quality)
- **Individual summaries**: One Gemini call per summary (ensures consistent quality)
- **Structured output**: Gemini returns JSON for reliable parsing

### Reference

- Design doc §2 (Data Flow, steps 2–4)
- Design doc §7, Stages 2–5
- Design doc §7 (Gemini API Cost Estimation)

---

## Phase 4: Daily Pipeline & Newsletter API

### Goal

Integrate all pipeline stages into a scheduled daily job and expose newsletter browsing API.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 4.1 | Pipeline orchestrator | Function that runs 6 stages sequentially: collect → load interests → score → filter → summarize → persist |
| 4.2 | Filtering logic | Discard articles below threshold (default 0.3), select top 20 by score |
| 4.3 | scheduler.py | `backend/scheduler.py` — APScheduler with daily 06:00 job |
| 4.4 | Manual trigger | `POST /api/pipeline/run` — manually trigger pipeline (dev/testing) |
| 4.5 | Newsletter router | `backend/routers/newsletters.py` — `GET /api/newsletters`, `/today`, `/:date` |
| 4.6 | Article router | `backend/routers/articles.py` — `GET /api/articles/:id` |
| 4.7 | Newsletter date | Set `newsletter_date` to today's date for each pipeline run |
| 4.8 | Feed timestamp | Update `feeds.last_fetched_at` after successful collection |
| 4.9 | Tests | Pipeline integration test, newsletter API tests |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Backend Developer | Implements orchestrator, scheduler, APIs |
| Planner | **Thorough review** — verifies all 6 pipeline stages match design doc exactly |
| AI Developer | Validates AI call flow within pipeline (interest loading → scoring → summarization) |
| Code Reviewer | Reviews integration logic, error propagation, transaction handling |
| QA Tester | E2E pipeline test: trigger → verify articles appear in newsletter API |

### Acceptance Criteria

- [ ] Pipeline runs all 6 stages in correct order
- [ ] Articles below relevance threshold (0.3) are excluded
- [ ] Top 20 articles are selected per newsletter
- [ ] `newsletter_date` is set correctly
- [ ] `feeds.last_fetched_at` is updated after collection
- [ ] APScheduler job is configured for daily 06:00
- [ ] `POST /api/pipeline/run` triggers pipeline manually
- [ ] `GET /api/newsletters/today` returns today's articles grouped by category
- [ ] `GET /api/newsletters/:date` returns a specific date's newsletter
- [ ] `GET /api/newsletters` returns paginated list of editions
- [ ] `GET /api/articles/:id` returns article detail

### Reference

- Design doc §7 (Scheduler — full pipeline description)
- Design doc §5 (Newsletter and Article endpoints)

---

## Phase 5: User Interactions & Feedback Loop

### Goal

Implement like/bookmark system with automatic interest profile updates — the personalization engine.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 5.1 | Interaction endpoints | `POST /api/articles/:id/like`, `POST /api/articles/:id/bookmark` — toggle behavior (create or delete) |
| 5.2 | interests.py | `backend/services/interests.py` — on like: extract keywords from article → upsert `user_interests` with weight +1 |
| 5.3 | Time decay | Decay function: weight *= 0.9 every 7 days, applied before each scoring cycle |
| 5.4 | Bookmarked articles | `GET /api/articles/bookmarked` — list bookmarked articles for current user |
| 5.5 | Async detailed summary | On bookmark create: launch background task to generate Gemini detailed summary → store in `articles.detailed_summary` |
| 5.6 | Interest API | `backend/routers/interests.py` — `GET /api/interests` returns profile sorted by weight desc |
| 5.7 | Tests | Toggle logic, interest upsert, time decay, async summary trigger |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Backend Developer | Implements all tasks |
| AI Developer | Reviews feedback loop integrity: like → interests → next scoring. Reviews detailed summary prompt |
| Planner | Verifies all 3 feedback mechanisms from design doc §3 (Like, Bookmark, Rewind) |
| Code Reviewer | Reviews concurrency handling, toggle idempotency, async task management |
| Security Engineer | Validates user authorization (user can only interact with own data), composite UNIQUE enforcement |

### Acceptance Criteria

- [ ] Like toggle: first call creates, second call deletes the interaction
- [ ] Bookmark toggle: same toggle behavior
- [ ] On like: article keywords extracted and upserted into `user_interests`
- [ ] Interest weights increment correctly (+1 per like signal)
- [ ] Time decay applies 0.9 factor per 7 days of inactivity
- [ ] On bookmark: background task generates detailed summary via Gemini
- [ ] Detailed summary stored in `articles.detailed_summary`
- [ ] `GET /api/articles/bookmarked` returns user's bookmarked articles
- [ ] `GET /api/interests` returns sorted interest profile
- [ ] Composite UNIQUE on `(user_id, article_id, type)` prevents duplicate interactions
- [ ] User cannot interact on behalf of another user

### Key Design Decisions

- **Toggle behavior**: POST creates if not exists, deletes if exists — no separate DELETE endpoint
- **Keyword extraction**: Done during like processing (not pre-computed)
- **Async summary**: Uses FastAPI BackgroundTasks to avoid blocking the bookmark response

### Reference

- Design doc §3 (Feedback Loop — all 3 mechanisms)
- Design doc §5 (Interaction endpoints)
- Design doc §4 (`interactions`, `user_interests` tables)

---

## Phase 6: Rewind Weekly Analysis

### Goal

Generate weekly interest trend reports with comparative analysis.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 6.1 | rewind.py | `backend/services/rewind.py` — collect 7-day liked articles → send to Gemini with previous report → generate structured JSON |
| 6.2 | Report structure | JSON schema: hot_topics, trend_changes (rising/declining), suggestions |
| 6.3 | Comparative analysis | Include previous Rewind report in Gemini prompt for trend comparison |
| 6.4 | Rewind router | `backend/routers/rewind.py` — `GET /api/rewind/latest`, `GET /api/rewind/:id`, `POST /api/rewind/generate` |
| 6.5 | Weekly scheduler | Add Sunday night job to `scheduler.py` |
| 6.6 | Edge cases | Handle: no likes this week, no previous report, first-ever report |
| 6.7 | Tests | Report generation, comparative logic, edge cases |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Backend Developer | Implements service + API |
| AI Developer | **Lead** — designs comparative analysis prompt, hot topics / rising / declining extraction strategy, JSON output schema |
| Code Reviewer | Reviews JSON structure, caching logic, error handling |
| QA Tester | Tests scenarios: normal week, no activity, first report, consecutive reports |

### Acceptance Criteria

- [ ] `POST /api/rewind/generate` creates a new weekly report
- [ ] Report contains: hot_topics, trend_changes (rising + declining), suggestions
- [ ] Previous report is included in Gemini prompt for comparison
- [ ] First report (no previous data) generates successfully
- [ ] Week with no likes generates a meaningful "no activity" report
- [ ] `GET /api/rewind/latest` returns most recent report
- [ ] `GET /api/rewind/:id` returns specific report
- [ ] Weekly scheduler job configured for Sunday night
- [ ] Report stored as JSON in `rewind_reports` table

### Reference

- Design doc §3-3 (Rewind — Weekly Interest Analysis)
- Design doc §5 (Rewind endpoints)
- Design doc §7 (Rewind Generation schedule)

---

## Phase 7: Frontend Foundation

### Goal

Set up React application shell — routing, layout, API client, and navigation.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 7.1 | Project setup | `npm create vite@latest frontend -- --template react-ts` |
| 7.2 | Tailwind CSS | Install and configure Tailwind CSS |
| 7.3 | Dependencies | Install: react-router-dom, @supabase/supabase-js, axios, lucide-react |
| 7.4 | Routing | `App.tsx` with routes: `/` (Today), `/archive`, `/bookmarks`, `/rewind`, `/settings` |
| 7.5 | API client | `src/api/client.ts` — Axios instance with base URL config, request/response interceptors |
| 7.6 | Supabase client | `src/lib/supabase.ts` — client initialization (Auth-ready for future) |
| 7.7 | NavBar | `src/components/NavBar.tsx` — top navigation with active route highlighting |
| 7.8 | Layout | App shell with NavBar + main content area + responsive container |
| 7.9 | Common components | Loading spinner, error display, empty state placeholder |
| 7.10 | TypeScript types | Shared type definitions matching backend Pydantic models |
| 7.11 | Vite proxy | Configure dev server proxy to FastAPI backend |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Frontend Developer | Builds everything |
| Designer | Reviews layout structure, navigation UX, color/typography system, responsive behavior |
| Code Reviewer | Reviews project structure, TypeScript config, component patterns |

### Acceptance Criteria

- [ ] `cd frontend && npm run dev` starts successfully
- [ ] Navigation between 5 pages works (Today, Archive, Bookmarks, Rewind, Settings)
- [ ] NavBar highlights current route
- [ ] API client configured with backend base URL
- [ ] Vite dev server proxies `/api/*` to FastAPI backend
- [ ] TypeScript types defined for all API entities
- [ ] Responsive layout works on mobile and desktop viewports
- [ ] Loading, error, and empty states have placeholder components

### Reference

- Design doc §6 (Frontend Pages — Route Map)
- Design doc §6 (Component Hierarchy — top level)
- Design doc §9 (Frontend dependencies)

---

## Phase 8: Today Page & Article Interactions

### Goal

Build the main newsletter view — category-grouped article cards with like/bookmark functionality.

### Tasks

| # | Task | Description |
|---|------|-------------|
| 8.1 | Today page | `src/pages/Today.tsx` — fetches today's newsletter, renders DateHeader + CategorySections |
| 8.2 | DateHeader | Displays date (e.g., "Thu, Feb 13, 2026") and article count |
| 8.3 | CategorySection | `src/components/CategorySection.tsx` — category header + list of ArticleCards |
| 8.4 | ArticleCard | `src/components/ArticleCard.tsx` — title, source, relevance score, summary, like/bookmark buttons |
| 8.5 | Like interaction | Click toggles like state, optimistic UI update, calls `POST /api/articles/:id/like` |
| 8.6 | Bookmark interaction | Click toggles bookmark state, optimistic UI update, calls `POST /api/articles/:id/bookmark` |
| 8.7 | Article link | Title links to original article URL (opens in new tab) |
| 8.8 | Responsive design | Card layout adapts to mobile/tablet/desktop |
| 8.9 | Data states | Loading skeleton, empty state ("No articles today"), error state |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Frontend Developer | Implements all components |
| Designer | **Lead** — card design, visual hierarchy (title > source > summary), interaction affordances, spacing/typography, color for relevance scores |
| Code Reviewer | Reviews component separation, state management, optimistic update patterns |
| QA Tester | Tests various data states: 0 articles, 1 article, 20 articles, multiple categories, long titles |

### Acceptance Criteria

- [ ] Today page loads and displays today's newsletter from API
- [ ] Articles are grouped by category with section headers
- [ ] Each card shows: title, source feed, relevance score, Korean summary
- [ ] Like button toggles with visual feedback (optimistic update)
- [ ] Bookmark button toggles with visual feedback (optimistic update)
- [ ] Article title opens original URL in new tab
- [ ] Empty state shown when no articles exist for today
- [ ] Loading skeleton shown while data is being fetched
- [ ] Layout is responsive across viewport sizes

### Visual Reference

```
┌───────────────────────────────────────────┐
│  GPT-5 Launch Imminent: Key Changes        │
│  TechCrunch · Relevance 0.95               │
│  GPT-5 is expected to launch soon with     │
│  major improvements in multimodal...       │
│                              👍 12   🔖    │
└───────────────────────────────────────────┘
```

### Reference

- Design doc §6 (Main Page Layout wireframe)
- Design doc §6 (Component Hierarchy — Today page)

---

## Phase 9: Archive, Bookmarks & Settings Pages

### Goal

Implement the three remaining content pages for browsing history, saved articles, and configuration.

### Tasks

| # | Task | Description |
|---|------|-------------|
| **Archive** | | |
| 9.1 | CalendarView | `src/pages/Archive.tsx` — month calendar with clickable dates (dates with newsletters are highlighted) |
| 9.2 | Date selection | Click a date → load that date's newsletter below the calendar |
| 9.3 | List fallback | Alternative list view showing newsletter editions sorted by date |
| **Bookmarks** | | |
| 9.4 | Bookmarks page | `src/pages/Bookmarks.tsx` — list of bookmarked articles from `GET /api/articles/bookmarked` |
| 9.5 | Detailed summary | Show expanded detailed summary (background + takeaways + keywords) for each bookmarked article |
| 9.6 | Summary loading | Show loading indicator while detailed summary is being generated |
| **Settings** | | |
| 9.7 | FeedManager | `src/pages/Settings.tsx` — add new feed (URL input), list all feeds, toggle active/inactive, delete |
| 9.8 | InterestProfile | Display keyword weights as a visual list (sorted by weight), allow viewing current profile |
| 9.9 | Feed validation UI | Show validation feedback when adding a feed URL |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Frontend Developer | Implements all pages |
| Designer | Calendar UX, bookmark layout (detailed summary readability), settings page usability |
| Code Reviewer | Code reuse (ArticleCard shared), performance (calendar rendering) |
| QA Tester | Edge cases: empty bookmarks, feed URL validation, months with no newsletters |
| Security Engineer | Feed URL input validation (XSS prevention, SSRF considerations) |

### Acceptance Criteria

- [ ] Archive: calendar shows months with highlighted newsletter dates
- [ ] Archive: clicking a date loads that newsletter's articles
- [ ] Archive: list view alternative available
- [ ] Bookmarks: displays all bookmarked articles with detailed summaries
- [ ] Bookmarks: shows loading state for summaries still being generated
- [ ] Settings: can add a new feed by URL
- [ ] Settings: can toggle feed active/inactive
- [ ] Settings: can delete a feed
- [ ] Settings: interest profile displayed sorted by weight
- [ ] Feed URL input is validated (format check, XSS prevention)

### Reference

- Design doc §6 (Route Map — Archive, Bookmarks, Settings)
- Design doc §6 (Component Hierarchy — full tree)

---

## Phase 10: Rewind UI & Polish

### Goal

Build the Rewind insights page and polish the entire application's UI/UX.

### Tasks

| # | Task | Description |
|---|------|-------------|
| **Rewind Page** | | |
| 10.1 | RewindReport | `src/components/RewindReport.tsx` — displays hot topics, rising/declining interests, suggestions |
| 10.2 | TrendChart | Visual chart showing interest weight changes over time (consider recharts or chart.js) |
| 10.3 | RewindHistory | Past reports list with expandable summaries |
| 10.4 | Manual generate | Button to trigger `POST /api/rewind/generate`, show loading state |
| **UI Polish** | | |
| 10.5 | Loading states | Consistent skeleton loaders across all pages |
| 10.6 | Error states | Unified error display with retry actions |
| 10.7 | Empty states | Meaningful empty state messages and illustrations for each page |
| 10.8 | Transitions | Smooth page transitions and interaction animations |
| 10.9 | Accessibility | Keyboard navigation, ARIA labels, color contrast compliance |
| 10.10 | Dark mode | Optional: Tailwind dark mode support |

### Active Roles

| Role | Responsibility |
|------|----------------|
| Frontend Developer | Implements all tasks |
| Designer | **Lead** — data visualization design, trend chart readability, overall UI consistency audit, accessibility review |
| Code Reviewer | Performance optimization (unnecessary re-renders, bundle size), code consistency |
| QA Tester | Full user scenario walkthrough across all pages |

### Acceptance Criteria

- [x] Rewind page displays latest weekly report with hot topics, trends, suggestions
- [x] Trend chart visualizes interest changes over time
- [x] Past Rewind reports are accessible and expandable
- [x] Manual Rewind generation works with appropriate loading feedback
- [x] All pages have consistent loading, error, and empty states
- [x] Smooth transitions between pages and on interactions
- [x] Keyboard navigation works throughout the app
- [x] ARIA labels present on interactive elements
- [x] Color contrast meets WCAG AA standards

### Reference

- Design doc §3-3 (Rewind report structure)
- Design doc §6 (Rewind page components)

---

## Phase 11: Integration Testing & Final QA

### Goal

Comprehensive end-to-end validation, security audit, and release preparation.

### Tasks

| # | Task | Description |
|---|------|-------------|
| **E2E Testing** | | |
| 11.1 | Full pipeline test | Trigger pipeline → verify articles in DB → verify API responses → verify UI rendering |
| 11.2 | Feedback loop test | Like articles → verify interest updates → trigger new pipeline → verify improved scoring |
| 11.3 | Rewind flow test | Like articles over time → generate Rewind → verify comparative analysis |
| **Security Audit** | | |
| 11.4 | OWASP check | Review against OWASP Top 10 (injection, XSS, CSRF, etc.) |
| 11.5 | Dependency scan | Check for known vulnerabilities in Python and Node dependencies |
| 11.6 | Secret review | Ensure no secrets in code, logs, or client-side bundles |
| **Performance** | | |
| 11.7 | API response times | Profile key endpoints under expected load |
| 11.8 | Frontend bundle | Analyze and optimize bundle size |
| 11.9 | Gemini cost | Verify actual API costs match estimates from design doc |
| **Documentation** | | |
| 11.10 | README update | Final setup instructions, architecture summary |
| 11.11 | Deployment guide | Steps for local macOS deployment |

### Active Roles — ALL TEAM MEMBERS

| Role | Responsibility |
|------|----------------|
| Planner | Design doc vs final implementation full comparison checklist |
| Backend Developer | Fix backend integration issues found during testing |
| Frontend Developer | Fix frontend integration issues found during testing |
| AI Developer | Gemini call cost/performance final validation, prompt quality review |
| Code Reviewer | Full architecture review — consistency, patterns, tech debt |
| Security Engineer | Complete security audit report |
| Designer | Final UI/UX inspection — consistency, accessibility, usability |
| QA Tester | Full regression test across all user scenarios |
| Decision Maker | **Release approval** based on all team members' sign-off |

### Acceptance Criteria

- [x] Full pipeline runs without errors from feed collection to UI display
- [x] Feedback loop demonstrably improves article scoring
- [x] Rewind reports generate with meaningful comparative analysis
- [x] No OWASP Top 10 vulnerabilities found
- [x] No known dependency vulnerabilities (or documented exceptions)
- [x] No secrets exposed in code, logs, or client bundles
- [x] API response times acceptable (< 500ms for read endpoints)
- [x] Frontend bundle size reasonable (< 500KB gzipped)
- [x] Gemini API costs align with design doc estimates
- [x] README accurately reflects final implementation
- [x] All team members approve release

### Reference

- Design doc (entire document — final cross-reference)

---

## Phase Execution Protocol

### Per-Phase Workflow

1. **Kickoff**: Decision Maker reviews phase requirements with active team members
2. **Implementation**: Developers execute tasks following TDD where applicable
3. **Review Round**: Code Reviewer + Security Engineer + relevant specialists review
4. **QA Validation**: QA Tester validates acceptance criteria
5. **Planner Check**: Planner verifies against design document requirements
6. **Gate Decision**: Decision Maker evaluates all feedback and decides:
   - ✅ **Proceed** — move to next phase
   - 🔄 **Revise** — address specific issues before proceeding
   - ⛔ **Block** — fundamental issue requires design re-evaluation

### Branch Strategy

Each phase should be developed on a dedicated branch:
```
feature/phase-01-foundation
feature/phase-02-rss-collection
feature/phase-03-ai-pipeline
...
```

Merge to `main` after Decision Maker approval.
