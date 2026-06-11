-- dim_video
-- One row per video — latest known metadata
-- Populated from staging.videos

INSERT INTO marts.dim_video (
    video_id,
    channel_id,
    title,
    published_at,
    duration_seconds
)
SELECT
    video_id,
    channel_id,
    title,
    published_at,
    duration_seconds
FROM staging.videos
ON CONFLICT (video_id) DO UPDATE SET
    title            = EXCLUDED.title,
    duration_seconds = EXCLUDED.duration_seconds,
    updated_at       = NOW();