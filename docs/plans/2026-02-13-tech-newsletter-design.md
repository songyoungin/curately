# Curately Design Document

> "My own GeekNews" — an AI-curated tech newsletter tailored to your interests.

## 1. Overview

### Concept

Curately is a personal tech newsletter platform that automatically collects articles from RSS feeds,
filters them by relevance to your interests, and generates concise Korean-language summaries — all
powered by Gemini 2.5 Flash.

**Core value propositions:**

- **Automated curation** — Fresh tech news delivered every morning with zero manual effort
- **Personalization through feedback** — Likes and bookmarks continuously refine what surfaces next
- **Rewind insights** — Weekly analysis of your reading patterns reveals evolving interests
- **Minimal cost** — Gemini 2.5 Flash keeps API expenses negligible

### Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Backend | FastAPI + Uvicorn | REST API server |
| Frontend | React (Vite) + Tailwind CSS | Single-page web application |
| Database | Supabase (PostgreSQL) | Persistent storage + real-time capabilities |
| Auth | Supabase Auth | Google OAuth integration |
| LLM | Gemini 2.5 Flash | Relevance scoring, summarization, trend analysis |
| RSS Parsing | feedparser | Article collection from RSS feeds |
| Scheduling | APScheduler | Daily pipeline orchestration |
| Deployment | Local macOS (initial) | Development-first, server-ready later |

---

## 2. Architecture

### System Diagram

```
┌────────────┐     ┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  RSS Feeds │────→│  Collector   │────→│  Gemini 2.5 Flash │────→│ Supabase DB │
└────────────┘     └─────────────┘     └──────────────────┘     └──────┬──────┘
                                         │  Scoring &                  │
                                         │  Summarization              │
                                         └─────────────────────────────│
                                                                       ↓
                                                                ┌─────────────┐
                                                                │ FastAPI API │
                                                                └──────┬──────┘
                                                                       ↓
                                                                ┌──────────────┐
                                                                │   React +    │
                                                                │  Tailwind UI │
                                                                └──────────────┘
                                                                  Feed · Likes
                                                                  Bookmarks
                                                                  Archive
                                                                  Rewind
```

### Data Flow

1. **Collect** — A daily cron job fetches new articles from all active RSS feeds.
2. **Score** — Gemini evaluates each article's relevance against the user's interest profile and assigns a score from 0.0 to 1.0.
3. **Filter** — Only articles scoring above the configured threshold (default: 0.3) pass through; the top 20 are selected.
4. **Summarize** — Gemini generates a concise Korean summary (2–3 sentences) for each selected article.
5. **Store** — Articles, summaries, scores, and metadata are persisted to Supabase.
6. **Browse** — Users view today's newsletter or past issues through the React web app.
7. **Interact** — Likes and bookmarks feed back into the interest profile, improving future curation.

---

## 3. Feedback Loop

The feedback loop is what transforms Curately from a static aggregator into a personalized curation engine. There are three mechanisms:

### 3-1. Likes → Improved Filtering

When a user likes an article:

1. The system extracts keywords, source, and categories from the liked article.
2. These are upserted into the `user_interests` table with incremented weights.
3. On the next collection cycle, the interest profile is injected into the Gemini scoring prompt, resulting in higher relevance scores for similar content.

**Time-decay:** Interest weights decay by a factor of 0.9 every 7 days, ensuring that stale preferences gradually fade while recent signals stay strong.

### 3-2. Bookmarks → Detailed Summaries

Bookmarking signals that the user finds an article worth revisiting. Since they're unlikely to re-read the original, the system provides a richer summary:

1. On bookmark, an async background task sends the article to Gemini with a "detailed summary" prompt.
2. The detailed summary includes:
   - Background context and why this topic matters
   - 3–5 key takeaways
   - Related concepts and keywords
3. The result is stored in the `detailed_summary` column and displayed on the Bookmarks page.

### 3-3. Rewind — Weekly Interest Analysis

Rewind aggregates the user's recent activity into an insightful weekly report:

1. Collect all liked articles from the past 7 days.
2. Send them to Gemini with the previous Rewind report (if available) for comparative analysis.
3. Generate a structured report containing:
   - **Hot topics** — The dominant themes of the week (e.g., "LLM Agents", "Kubernetes Security")
   - **Rising interests** — Topics with increased engagement compared to last week
   - **Declining interests** — Topics with decreased engagement
   - **Suggestions** — Recommended keywords or feeds to track based on emerging patterns
4. Store the report in `rewind_reports` as cached JSON to avoid redundant re-analysis.

Rewind reports are generated automatically once a week, with an option for manual on-demand generation.

---

## 4. Database Schema (Supabase / PostgreSQL)

### Design Principles

- **Shared vs. per-user data:** `articles` and `feeds` are shared across all users (everyone sees the same article pool). `interactions`, `user_interests`, and `rewind_reports` are scoped per user.
- **Multi-user readiness:** The `users` table exists from day one. For MVP, a single default user is auto-created and the app operates without authentication. When Google OAuth is enabled later, no schema migration is needed.
- **Deduplication:** `articles.source_url` has a UNIQUE constraint to prevent collecting the same article twice.
- **One interaction per type:** The composite UNIQUE on `(user_id, article_id, type)` ensures a user can like and bookmark an article, but not like it twice.

### Tables

```sql
-- ============================================================
-- Users
-- ============================================================
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    name            TEXT,
    picture_url     TEXT,
    google_sub      TEXT UNIQUE,             -- Google OAuth subject ID
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

-- ============================================================
-- RSS Feed Sources
-- ============================================================
CREATE TABLE feeds (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,            -- Display name (e.g., "Hacker News")
    url             TEXT UNIQUE NOT NULL,     -- RSS feed URL
    is_active       BOOLEAN DEFAULT TRUE,
    last_fetched_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Articles
-- ============================================================
CREATE TABLE articles (
    id               BIGSERIAL PRIMARY KEY,
    source_feed      TEXT NOT NULL,           -- Feed name at time of collection
    source_url       TEXT UNIQUE NOT NULL,    -- Original article URL (dedup key)
    title            TEXT NOT NULL,
    author           TEXT,
    published_at     TIMESTAMPTZ,
    raw_content      TEXT,                    -- Original content/description
    summary          TEXT,                    -- Gemini basic summary (2-3 sentences)
    detailed_summary TEXT,                    -- Gemini detailed summary (on bookmark)
    relevance_score  FLOAT,                  -- 0.0 to 1.0
    categories       JSONB DEFAULT '[]',     -- e.g., ["AI/ML", "DevOps"]
    keywords         JSONB DEFAULT '[]',     -- Extracted keyword list
    newsletter_date  DATE,                   -- Which newsletter edition includes this
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- User Interactions (likes & bookmarks)
-- ============================================================
CREATE TABLE interactions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    article_id      BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    type            TEXT NOT NULL CHECK (type IN ('like', 'bookmark')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, article_id, type)
);

-- ============================================================
-- Interest Profile (auto-updated from likes)
-- ============================================================
CREATE TABLE user_interests (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    keyword         TEXT NOT NULL,
    weight          FLOAT DEFAULT 1.0,       -- Accumulated weight with time decay
    source          TEXT,                    -- Origin of this interest signal
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, keyword)
);

-- ============================================================
-- Rewind Reports (weekly interest analysis)
-- ============================================================
CREATE TABLE rewind_reports (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    report_content  JSONB,                   -- Full Gemini analysis result
    hot_topics      JSONB,                   -- e.g., ["LLM Agents", "K8s Security"]
    trend_changes   JSONB,                   -- Rising/declining interests
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexes (recommended)

```sql
CREATE INDEX idx_articles_newsletter_date ON articles(newsletter_date);
CREATE INDEX idx_articles_relevance ON articles(relevance_score DESC);
CREATE INDEX idx_interactions_user_type ON interactions(user_id, type);
CREATE INDEX idx_user_interests_user_weight ON user_interests(user_id, weight DESC);
CREATE INDEX idx_rewind_reports_user_period ON rewind_reports(user_id, period_end DESC);
```

---

## 5. API Endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/google` | Handle Google OAuth callback |
| `GET` | `/api/auth/me` | Return the currently authenticated user |

### Newsletters

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/newsletters` | List all newsletter editions (paginated, sorted by date descending) |
| `GET` | `/api/newsletters/today` | Return today's newsletter with its articles |
| `GET` | `/api/newsletters/:date` | Return a specific date's newsletter (format: `YYYY-MM-DD`) |

### Articles

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/articles/:id` | Return article detail including summary and original link |
| `GET` | `/api/articles/bookmarked` | List all bookmarked articles for the current user |

### Interactions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/articles/:id/like` | Toggle like on an article (creates or deletes the interaction) |
| `POST` | `/api/articles/:id/bookmark` | Toggle bookmark (on create, triggers async detailed summary generation) |

### Rewind

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/rewind/latest` | Return the most recent weekly report |
| `GET` | `/api/rewind/:id` | Return a specific report by ID |
| `POST` | `/api/rewind/generate` | Manually trigger a new Rewind report |

### Feed Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/feeds` | List all subscribed feeds with status |
| `POST` | `/api/feeds` | Add a new RSS feed |
| `DELETE` | `/api/feeds/:id` | Remove a feed |
| `PATCH` | `/api/feeds/:id` | Toggle a feed's active/inactive status |

### Interests

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/interests` | Return the current interest profile sorted by weight descending |

---

## 6. Frontend Pages

### Route Map

| Route | Page | Description |
|-------|------|-------------|
| `/` | Today | Today's newsletter — article cards grouped by category, sorted by relevance |
| `/archive` | Archive | Browse past newsletters via calendar or list view |
| `/bookmarks` | Bookmarks | All bookmarked articles with their detailed summaries |
| `/rewind` | Rewind | Weekly interest report with trend visualizations |
| `/settings` | Settings | Manage RSS feeds, review and adjust interest profile |

### Main Page Layout

```
┌──────────────────────────────────────────────────┐
│  Curately                          🔖  ⚙️  👤    │
├──────────────────────────────────────────────────┤
│  [Today]  [Archive]  [Bookmarks]  [Rewind]       │
├──────────────────────────────────────────────────┤
│                                                   │
│  Thu, Feb 13, 2026                  12 articles   │
│                                                   │
│  ── AI/ML ─────────────────────────────────────  │
│  ┌───────────────────────────────────────────┐   │
│  │  GPT-5 Launch Imminent: Key Changes        │   │
│  │  TechCrunch · Relevance 0.95               │   │
│  │  GPT-5 is expected to launch soon with     │   │
│  │  major improvements in multimodal...       │   │
│  │                              👍 12   🔖    │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  ── DevOps ────────────────────────────────────  │
│  ┌───────────────────────────────────────────┐   │
│  │  K8s 1.33 Release Notes: What You Need     │   │
│  │  to Know                                   │   │
│  │  ...                                       │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
└──────────────────────────────────────────────────┘
```

### Component Hierarchy

```
App
├── NavBar                         (top navigation + user avatar)
├── Pages
│   ├── Today
│   │   ├── DateHeader             (date display + article count)
│   │   └── CategorySection[]      (one per category)
│   │       └── ArticleCard[]      (title, source, summary, like/bookmark buttons)
│   ├── Archive
│   │   ├── CalendarView           (month calendar with clickable dates)
│   │   └── NewsletterList         (fallback list view)
│   ├── Bookmarks
│   │   └── ArticleCard[]          (with detailed summary expanded)
│   ├── Rewind
│   │   ├── RewindReport           (current week's analysis)
│   │   ├── TrendChart             (rising/declining visualization)
│   │   └── RewindHistory          (past reports)
│   └── Settings
│       ├── FeedManager            (add/remove/toggle feeds)
│       └── InterestProfile        (keyword weights, manual adjustment)
```

---

## 7. Scheduler — Collection & Summary Pipeline

### Daily Morning Pipeline

The pipeline runs every day at 06:00 and proceeds through six sequential stages:

```
06:00 ┌──────────────────────────────────────────────────────────────┐
      │ Stage 1: RSS Collection                                      │
      │ Fetch articles from all active feeds via feedparser.          │
      │ Deduplicate against existing articles using source_url.       │
      │ Output: list of new, unseen articles.                        │
      └──────────────────────────┬───────────────────────────────────┘
                                 ↓
06:01 ┌──────────────────────────────────────────────────────────────┐
      │ Stage 2: Load Interest Profile                               │
      │ Query user_interests for the top 20 keywords by weight.      │
      │ Format them as context for the Gemini scoring prompt.        │
      └──────────────────────────┬───────────────────────────────────┘
                                 ↓
06:02 ┌──────────────────────────────────────────────────────────────┐
      │ Stage 3: Relevance Scoring (batched)                         │
      │ Send articles to Gemini in batches of 5–10.                  │
      │ Prompt includes user interests + article title/content.      │
      │ Returns: relevance score (0.0–1.0), categories, keywords.   │
      └──────────────────────────┬───────────────────────────────────┘
                                 ↓
06:03 ┌──────────────────────────────────────────────────────────────┐
      │ Stage 4: Filtering                                           │
      │ Discard articles below the relevance threshold (default 0.3).│
      │ Select the top 20 articles by score.                         │
      └──────────────────────────┬───────────────────────────────────┘
                                 ↓
06:04 ┌──────────────────────────────────────────────────────────────┐
      │ Stage 5: Summary Generation (individual)                     │
      │ For each selected article, request a Korean summary from     │
      │ Gemini (2–3 sentences, focusing on key takeaways).           │
      │ Individual calls ensure consistent summary quality.          │
      └──────────────────────────┬───────────────────────────────────┘
                                 ↓
06:05 ┌──────────────────────────────────────────────────────────────┐
      │ Stage 6: Persist to Database                                 │
      │ Insert articles into the articles table with today's date    │
      │ as newsletter_date. Update feeds.last_fetched_at.            │
      └──────────────────────────────────────────────────────────────┘
```

### Async Triggers (from web app interactions)

| Trigger | Action | Storage |
|---------|--------|---------|
| Bookmark click | Request detailed summary from Gemini in a background task | `articles.detailed_summary` |
| Like click | Extract keywords from the liked article, upsert into `user_interests` with weight +1 | `user_interests` |

### Rewind Generation

- **Automatic:** Runs once per week (Sunday night) via APScheduler.
- **Manual:** Users can trigger on-demand via the `POST /api/rewind/generate` endpoint.
- **Process:** Collects 7-day liked articles → sends to Gemini with the previous report for comparative analysis → stores structured JSON in `rewind_reports`.

### Gemini API Cost Estimation

| Operation | Calls per day | Notes |
|-----------|--------------|-------|
| Relevance scoring | 3–5 (batched) | 5–10 articles per call |
| Basic summaries | 15–20 (individual) | One per selected article |
| Detailed summaries | 0–5 (on demand) | Triggered by bookmarks |
| Rewind analysis | ~0.14 (weekly) | Once per week |

With Gemini 2.5 Flash pricing, the total daily cost is negligible.

### Scheduling Implementation

- **Local macOS:** APScheduler runs as a background task inside the FastAPI process. No separate worker process needed.
- **Future server deployment:** Can be swapped to Celery with Redis broker or system-level cron, with no changes to the pipeline logic itself.

---

## 8. Project Directory Structure

```
curately/
├── pyproject.toml                    # Python project config & dependencies
├── CLAUDE.md                         # AI assistant project instructions
├── .env                              # Secrets: GEMINI_API_KEY, SUPABASE_* (gitignored)
├── .env.example                      # Environment variable template (committed)
├── config.yaml                       # RSS feed list, schedule settings, thresholds
│
├── backend/
│   ├── __init__.py
│   ├── main.py                       # FastAPI application entrypoint
│   ├── config.py                     # Loads config.yaml + .env into typed settings
│   ├── supabase_client.py            # Supabase client initialization & helpers
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                   # /api/auth/* — Supabase Auth wrapper
│   │   ├── newsletters.py            # /api/newsletters/*
│   │   ├── articles.py               # /api/articles/* + interaction endpoints
│   │   ├── feeds.py                  # /api/feeds/*
│   │   ├── interests.py              # /api/interests/*
│   │   └── rewind.py                 # /api/rewind/*
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── collector.py              # RSS feed fetching & deduplication
│   │   ├── scorer.py                 # Gemini relevance scoring (batched)
│   │   ├── summarizer.py             # Gemini summary generation (basic + detailed)
│   │   ├── interests.py              # Interest profile updates & time decay
│   │   └── rewind.py                 # Rewind report generation & caching
│   │
│   └── scheduler.py                  # APScheduler job definitions
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx                  # React app bootstrap
│       ├── App.tsx                   # Root component with routing
│       ├── api/
│       │   └── client.ts            # Axios-based API client
│       ├── lib/
│       │   └── supabase.ts          # Supabase JS client (Auth + Realtime)
│       ├── pages/
│       │   ├── Today.tsx             # Main newsletter view
│       │   ├── Archive.tsx           # Past newsletters browser
│       │   ├── Bookmarks.tsx         # Bookmarked articles with detailed summaries
│       │   ├── Rewind.tsx            # Weekly interest analysis
│       │   └── Settings.tsx          # Feed management & interest profile
│       └── components/
│           ├── ArticleCard.tsx       # Individual article display
│           ├── CategorySection.tsx   # Grouped articles under a category header
│           ├── NavBar.tsx            # Top navigation bar
│           └── RewindReport.tsx      # Rewind report display
│
├── tests/
│   ├── test_collector.py
│   ├── test_scorer.py
│   ├── test_summarizer.py
│   └── test_api.py
│
└── docs/
    └── plans/
        └── 2026-02-13-tech-newsletter-design.md
```

---

## 9. Dependencies

### Backend (Python)

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework for the REST API |
| `uvicorn` | ASGI server to run FastAPI |
| `supabase` | Supabase Python client for DB and auth |
| `feedparser` | RSS/Atom feed parsing |
| `google-genai` | Gemini API client |
| `apscheduler` | In-process job scheduling |
| `pyyaml` | YAML config file parsing |
| `pydantic` | Data validation and settings management |
| `httpx` | Async HTTP client (used by FastAPI and services) |

### Frontend (Node)

| Package | Purpose |
|---------|---------|
| `react`, `react-dom` | UI framework |
| `react-router-dom` | Client-side routing |
| `@supabase/supabase-js` | Supabase client for auth and realtime |
| `tailwindcss` | Utility-first CSS framework |
| `axios` | HTTP client for API calls |
| `lucide-react` | Icon library |

---

## 10. Authentication Flow (Supabase Auth)

### Sequence

```
┌──────────┐          ┌──────────┐          ┌──────────┐
│ Frontend │          │ Supabase │          │ FastAPI  │
└────┬─────┘          └────┬─────┘          └────┬─────┘
     │  signInWithOAuth()  │                     │
     │────────────────────→│                     │
     │                     │ Google OAuth flow    │
     │←────────────────────│                     │
     │  JWT token returned │                     │
     │                     │                     │
     │  API request + Authorization: Bearer JWT  │
     │──────────────────────────────────────────→│
     │                     │  Verify JWT via      │
     │                     │←─────────────────────│
     │                     │  supabase-py         │
     │                     │─────────────────────→│
     │                     │  user_id confirmed   │
     │  API response                              │
     │←──────────────────────────────────────────│
```

### MVP Strategy

- A single default user is created on first run (seeded in the database).
- All API endpoints operate as this default user without requiring authentication.
- When Google OAuth is enabled, the existing `users` table and per-user data separation work immediately with no schema changes.

### Enabling Google OAuth

1. Enable Google provider in the Supabase Dashboard under Authentication → Providers.
2. Configure the OAuth consent screen and credentials in Google Cloud Console.
3. Set the redirect URL in Supabase to match the frontend's callback route.
4. Add a login button to the frontend that calls `supabase.auth.signInWithOAuth({ provider: 'google' })`.
5. Add JWT verification middleware to FastAPI that extracts `user_id` from the token.
