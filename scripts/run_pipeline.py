import sys
sys.path.insert(0, '.')

from datetime import date
from src.extractors.youtube_client import YouTubeExtractor
from src.transformers.channel_transformer import ChannelTransformer
from src.transformers.video_transformer import VideoTransformer
from src.loaders.postgres_loader import PostgresLoader
from src.utils.validators import DataValidator
from src.utils.logging_config import get_logger
from config.channels import CHANNELS

logger = get_logger("pipeline")


def run():
    extractor          = YouTubeExtractor()
    loader             = PostgresLoader()
    channel_transformer = ChannelTransformer()
    video_transformer  = VideoTransformer()
    validator          = DataValidator()
    today              = date.today()

    # ── Step 1: resolve handles ────────────────────────────────────
    logger.info("=== Step 1: Resolving handles ===")
    already_resolved = loader.get_resolved_handles()

    for channel in CHANNELS:
        handle = channel["handle"]
        if handle in already_resolved:
            continue
        channel_id = extractor.resolve_handle(handle)
        if channel_id:
            loader.save_channel_handle(handle, channel_id)

    resolved = loader.get_resolved_handles()
    logger.info("Total resolved: %d channels", len(resolved))

    # ── Step 2: fetch and load channel snapshots ───────────────────
    logger.info("=== Step 2: Fetching channel snapshots ===")
    channel_records = []

    for channel in CHANNELS:
        handle     = channel["handle"]
        channel_id = resolved.get(handle)

        if not channel_id:
            continue

        if loader.is_already_run(channel_id, today):
            logger.info("Already ran today for @%s — skipping", handle)
            continue

        run_id = loader.mark_run_started(channel_id, today)

        try:
            raw = extractor.fetch_channel_stats(channel_id)
            if not raw:
                loader.mark_run_failed(run_id, "No data")
                continue

            loader.save_channel_snapshot(raw)

            staged_channel          = channel_transformer.transform_channel(raw)
            staged_channel["category"] = channel["category"]
            staged_snapshot         = channel_transformer.transform_snapshot(raw, today)

            loader.upsert_staging_channel(staged_channel)
            loader.upsert_staging_channel_snapshot(staged_snapshot)

            channel_records.append(staged_snapshot)
            loader.mark_run_success(run_id, records_fetched=1)

        except Exception as e:
            logger.error("Failed for @%s: %s", handle, str(e))
            loader.mark_run_failed(run_id, str(e))

    # ── Step 3: fetch and load video stats ────────────────────────
    logger.info("=== Step 3: Fetching video stats ===")
    video_records = []

    for channel in CHANNELS:
        handle     = channel["handle"]
        channel_id = resolved.get(handle)

        if not channel_id:
            continue

        try:
            video_ids = extractor.fetch_video_ids(channel_id, max_results=10)
            if not video_ids:
                continue

            raw_stats = extractor.fetch_video_stats(video_ids)
            loader.save_video_snapshots(raw_stats)

            for raw in raw_stats:
                staged_video    = video_transformer.transform_video(raw)
                staged_snapshot = video_transformer.transform_snapshot(raw, today)

                loader.upsert_staging_video(staged_video)
                loader.upsert_staging_video_snapshot(staged_snapshot)
                video_records.append(staged_snapshot)

            logger.info("Loaded %d videos for @%s", len(raw_stats), handle)

        except Exception as e:
            logger.error("Video fetch failed for @%s: %s", handle, str(e))

    # ── Step 4: quality checks ─────────────────────────────────────
# ── Step 4: quality checks ─────────────────────────────────────
    logger.info("=== Step 4: Running quality checks ===")
    from sqlalchemy import text

    with loader.engine.connect() as conn:
        channel_rows = conn.execute(text("""
            SELECT channel_id, snapshot_date,
                   subscriber_count, total_view_count, video_count
            FROM staging.channel_snapshots
            WHERE snapshot_date = :today
        """), {"today": today}).fetchall()

        video_rows = conn.execute(text("""
            SELECT video_id, channel_id, snapshot_date,
                   view_count, like_count, comment_count
            FROM staging.video_snapshots
            WHERE snapshot_date = :today
        """), {"today": today}).fetchall()

    channel_records = [dict(row._mapping) for row in channel_rows]
    video_records   = [dict(row._mapping) for row in video_rows]

    channel_ok = validator.validate_channel_snapshots(channel_records)
    video_ok   = validator.validate_video_snapshots(video_records)

    if not channel_ok:
        logger.error("Quality checks failed — aborting marts load")
        return
    # ── Step 5: load to marts ──────────────────────────────────────
    logger.info("=== Step 5: Loading to marts ===")
    from sqlalchemy import text

    with loader.engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO marts.dim_channel (
                channel_id, name, country, category, thumbnail_url, published_at
            )
            SELECT channel_id, name, country, category, thumbnail_url, published_at
            FROM staging.channels
            ON CONFLICT (channel_id) DO UPDATE SET
                name          = EXCLUDED.name,
                country       = EXCLUDED.country,
                thumbnail_url = EXCLUDED.thumbnail_url,
                updated_at    = NOW()
        """))

        conn.execute(text("""
            INSERT INTO marts.dim_video (
                video_id, channel_id, title, published_at, duration_seconds
            )
            SELECT video_id, channel_id, title, published_at, duration_seconds
            FROM staging.videos
            ON CONFLICT (video_id) DO UPDATE SET
                title            = EXCLUDED.title,
                duration_seconds = EXCLUDED.duration_seconds,
                updated_at       = NOW()
        """))

        conn.execute(text("""
            INSERT INTO marts.fct_channel_snapshots (
                channel_id, date_key,
                subscriber_count, total_view_count, video_count
            )
            SELECT channel_id, snapshot_date,
                   subscriber_count, total_view_count, video_count
            FROM staging.channel_snapshots
            WHERE snapshot_date = :today
            ON CONFLICT (channel_id, date_key) DO UPDATE SET
                subscriber_count = EXCLUDED.subscriber_count,
                total_view_count = EXCLUDED.total_view_count,
                video_count      = EXCLUDED.video_count
        """), {"today": today})

        conn.execute(text("""
            INSERT INTO marts.fct_video_stats (
                video_id, channel_id, date_key,
                view_count, like_count, comment_count, engagement_rate
            )
            SELECT
                video_id, channel_id, snapshot_date,
                view_count, like_count, comment_count,
                CASE
                    WHEN view_count > 0
                    THEN ROUND((like_count + comment_count)::NUMERIC / view_count, 4)
                    ELSE 0
                END
            FROM staging.video_snapshots
            WHERE snapshot_date = :today
            ON CONFLICT (video_id, date_key) DO UPDATE SET
                view_count      = EXCLUDED.view_count,
                like_count      = EXCLUDED.like_count,
                comment_count   = EXCLUDED.comment_count,
                engagement_rate = EXCLUDED.engagement_rate
        """), {"today": today})

    logger.info("=== Pipeline complete for %s ===", today)


if __name__ == "__main__":
    run()