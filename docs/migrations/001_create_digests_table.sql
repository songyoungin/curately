-- Migration: Create digests table for daily digest feature
-- Run via: Supabase Dashboard > SQL Editor > New query
-- Date: 2026-02-18

CREATE TABLE digests (
    id              BIGSERIAL PRIMARY KEY,
    digest_date     DATE UNIQUE NOT NULL,
    content         JSONB NOT NULL,
    article_ids     JSONB DEFAULT '[]',
    article_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_digests_date ON digests(digest_date DESC);
