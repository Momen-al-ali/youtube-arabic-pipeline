-- ============================================================
-- MARTS SCHEMA
-- Star schema — optimized for dashboard queries.
-- All time-window filtering happens here via snapshot_date.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS marts;

-- ------------------------------------------------------------
-- dim_channel — one row per channel, slowly changing
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marts.dim_channel (
    channel_id          TEXT        PRIMARY KEY,
    name                TEXT        NOT NULL,
    country             TEXT,
    category            TEXT,
    thumbnail_url       TEXT,
    published_at        TIMESTAMP,
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- dim_video — one row per video
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marts.dim_video (
    video_id            TEXT        PRIMARY KEY,
    channel_id          TEXT        NOT NULL REFERENCES marts.dim_channel(channel_id),
    title               TEXT        NOT NULL,
    published_at        TIMESTAMP,
    duration_seconds    INTEGER,
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- dim_date — one row per calendar day
-- Pre-populated, never changes
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marts.dim_date (
    date_key            DATE        PRIMARY KEY,
    day                 INTEGER     NOT NULL,
    week                INTEGER     NOT NULL,
    month               INTEGER     NOT NULL,
    quarter             INTEGER     NOT NULL,
    year                INTEGER     NOT NULL,
    month_name          TEXT        NOT NULL,
    day_name            TEXT        NOT NULL,
    is_weekend          BOOLEAN     NOT NULL
);

-- ------------------------------------------------------------
-- fct_channel_snapshots — daily channel metrics
-- This is what drives the line chart and metrics strip
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marts.fct_channel_snapshots (
    id                  SERIAL      PRIMARY KEY,
    channel_id          TEXT        NOT NULL REFERENCES marts.dim_channel(channel_id),
    date_key            DATE        NOT NULL REFERENCES marts.dim_date(date_key),
    subscriber_count    BIGINT      NOT NULL DEFAULT 0,
    total_view_count    BIGINT      NOT NULL DEFAULT 0,
    video_count         INTEGER     NOT NULL DEFAULT 0,
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),

    UNIQUE (channel_id, date_key)
);

-- ------------------------------------------------------------
-- fct_video_stats — daily video metrics
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marts.fct_video_stats (
    id                  SERIAL      PRIMARY KEY,
    video_id            TEXT        NOT NULL REFERENCES marts.dim_video(video_id),
    channel_id          TEXT        NOT NULL REFERENCES marts.dim_channel(channel_id),
    date_key            DATE        NOT NULL REFERENCES marts.dim_date(date_key),
    view_count          BIGINT      NOT NULL DEFAULT 0,
    like_count          BIGINT      NOT NULL DEFAULT 0,
    comment_count       BIGINT      NOT NULL DEFAULT 0,
    engagement_rate     NUMERIC(6,4),
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),

    UNIQUE (video_id, date_key)
);