-- ============================================================
-- fct_video_stats
-- Daily video metrics — one row per video per day
-- engagement_rate = (likes + comments) / views
-- ============================================================

INSERT INTO marts.fct_video_stats (
    video_id,
    channel_id,
    date_key,
    view_count,
    like_count,
    comment_count,
    engagement_rate
)
SELECT
    video_id,
    channel_id,
    snapshot_date,
    view_count,
    like_count,
    comment_count,
    CASE
        WHEN view_count > 0
        THEN ROUND((like_count + comment_count)::NUMERIC / view_count, 4)
        ELSE 0
    END AS engagement_rate
FROM staging.video_snapshots
WHERE snapshot_date = CURRENT_DATE
ON CONFLICT (video_id, date_key) DO UPDATE SET
    view_count      = EXCLUDED.view_count,
    like_count      = EXCLUDED.like_count,
    comment_count   = EXCLUDED.comment_count,
    engagement_rate = EXCLUDED.engagement_rate;