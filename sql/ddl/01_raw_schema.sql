-- ------------------------------------------------------------
-- One row per channel per day — daily snapshot of channel stats
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.channel_snapshots (
    id                  SERIAL PRIMARY KEY,
    channel_id          TEXT        NOT NULL,
    name                TEXT,
    description         TEXT,
    country             TEXT,
    published_at        TIMESTAMP,
    thumbnail_url       TEXT,
    subscriber_count    BIGINT,
    total_view_count    BIGINT,
    video_count         INTEGER,
    fetched_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uix_channel_snapshots_per_day
    ON raw.channel_snapshots (channel_id, DATE(fetched_at));

-- ------------------------------------------------------------
-- One row per video per day — daily snapshot of video stats
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.video_snapshots (
    id              SERIAL PRIMARY KEY,
    video_id        TEXT        NOT NULL,
    channel_id      TEXT        NOT NULL,
    title           TEXT,
    published_at    TIMESTAMP,
    duration        TEXT,
    view_count      BIGINT,
    like_count      BIGINT,
    comment_count   BIGINT,
    fetched_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uix_video_snapshots_per_day
    ON raw.video_snapshots (video_id, DATE(fetched_at));