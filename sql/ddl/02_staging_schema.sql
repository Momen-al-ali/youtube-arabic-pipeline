-- ============================================================
-- STAGING SCHEMA
-- Cleaned, typed, and deduplicated data from raw.
-- Safe to truncate and rebuild from raw at any time.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- ------------------------------------------------------------
-- One row per channel — latest known attributes
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.channels (
    channel_id          TEXT        PRIMARY KEY,
    name                TEXT        NOT NULL,
    description         TEXT,
    country             TEXT,
    published_at        TIMESTAMP,
    thumbnail_url       TEXT,
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- One row per channel per day — cleaned numeric snapshot
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.channel_snapshots (
    id                  SERIAL      PRIMARY KEY,
    channel_id          TEXT        NOT NULL REFERENCES staging.channels(channel_id),
    snapshot_date       DATE        NOT NULL,
    subscriber_count    BIGINT      NOT NULL DEFAULT 0,
    total_view_count    BIGINT      NOT NULL DEFAULT 0,
    video_count         INTEGER     NOT NULL DEFAULT 0,
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),

    UNIQUE (channel_id, snapshot_date)
);

-- ------------------------------------------------------------
-- One row per video — latest known metadata
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.videos (
    video_id            TEXT        PRIMARY KEY,
    channel_id          TEXT        NOT NULL REFERENCES staging.channels(channel_id),
    title               TEXT        NOT NULL,
    published_at        TIMESTAMP,
    duration_seconds    INTEGER,
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- One row per video per day — cleaned numeric snapshot
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.video_snapshots (
    id              SERIAL      PRIMARY KEY,
    video_id        TEXT        NOT NULL REFERENCES staging.videos(video_id),
    channel_id      TEXT        NOT NULL REFERENCES staging.channels(channel_id),
    snapshot_date   DATE        NOT NULL,
    view_count      BIGINT      NOT NULL DEFAULT 0,
    like_count      BIGINT      NOT NULL DEFAULT 0,
    comment_count   BIGINT      NOT NULL DEFAULT 0,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),

    UNIQUE (video_id, snapshot_date)
);
