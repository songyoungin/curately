-- ============================================================
-- Curately Database Schema
-- Reference: docs/plans/2026-02-13-tech-newsletter-design.md §4
-- ============================================================

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

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX idx_articles_newsletter_date ON articles(newsletter_date);
CREATE INDEX idx_articles_relevance ON articles(relevance_score DESC);
CREATE INDEX idx_interactions_user_type ON interactions(user_id, type);
CREATE INDEX idx_user_interests_user_weight ON user_interests(user_id, weight DESC);
CREATE INDEX idx_rewind_reports_user_period ON rewind_reports(user_id, period_end DESC);
