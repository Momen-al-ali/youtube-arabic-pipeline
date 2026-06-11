-- ============================================================
-- fct_channel_snapshots
-- Daily channel metrics — one row per channel per day
-- Filtered by :snapshot_date parameter at runtime
-- ============================================================

INSERT INTO marts.fct_channel_snapshots (
    channel_id,
    date_key,
    subscriber_count,
    total_view_count,
    video_count
)
SELECT
    channel_id,
    snapshot_date,
    subscriber_count,
    total_view_count,
    video_count
FROM staging.channel_snapshots
WHERE snapshot_date = CURRENT_DATE
ON CONFLICT (channel_id, date_key) DO UPDATE SET
    subscriber_count = EXCLUDED.subscriber_count,
    total_view_count = EXCLUDED.total_view_count,
    video_count      = EXCLUDED.video_count;