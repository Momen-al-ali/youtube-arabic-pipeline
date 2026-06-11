from datetime import datetime, date, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.utils.config import get_config
from src.utils.logging_config import get_logger
from src.extractors.youtube_client import YouTubeExtractor
from src.transformers.channel_transformer import ChannelTransformer
from src.transformers.video_transformer import VideoTransformer
from src.loaders.postgres_loader import PostgresLoader
from src.utils.validators import DataValidator
from config.channels import CHANNELS

logger = get_logger(__name__)

#  Default args                                                        

default_args = {
    "owner": "momen",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


#  Task functions                                                      

def resolve_handles():
    """Resolve all channel handles to channel_ids — skips already resolved."""
    extractor = YouTubeExtractor()
    loader    = PostgresLoader()

    already_resolved = loader.get_resolved_handles()
    logger.info("%d handles already resolved", len(already_resolved))

    for channel in CHANNELS:
        handle = channel["handle"]

        if handle in already_resolved:
            logger.info("Skipping already resolved handle: @%s", handle)
            continue

        channel_id = extractor.resolve_handle(handle)
        if channel_id:
            loader.save_channel_handle(handle, channel_id)
            logger.info("Resolved @%s → %s", handle, channel_id)


def fetch_and_load_channel_snapshots():
    """Fetch channel stats and load into raw + staging."""
    extractor   = YouTubeExtractor()
    loader      = PostgresLoader()
    transformer = ChannelTransformer()
    config      = get_config()
    today       = date.today()

    resolved = loader.get_resolved_handles()

    for channel in CHANNELS:
        handle     = channel["handle"]
        channel_id = resolved.get(handle)

        if not channel_id:
            logger.warning("No channel_id for handle @%s — skipping", handle)
            continue

        if loader.is_already_run(channel_id, today):
            logger.info("Already ran today for %s — skipping", handle)
            continue

        run_id = loader.mark_run_started(channel_id, today)

        try:
            raw = extractor.fetch_channel_stats(channel_id)
            if not raw:
                loader.mark_run_failed(run_id, "No data returned from API")
                continue

            # Save to raw
            loader.save_channel_snapshot(raw)

            # Transform and save to staging
            staged_channel  = transformer.transform_channel(raw)
            staged_snapshot = transformer.transform_snapshot(raw, today)

            # Add category from our config (API doesn't provide this)
            staged_channel["category"] = channel.get("category")

            loader.upsert_staging_channel(staged_channel)
            loader.upsert_staging_channel_snapshot(staged_snapshot)

            loader.mark_run_success(run_id, records_fetched=1)

        except Exception as e:
            logger.error("Failed for channel %s: %s", handle, str(e))
            loader.mark_run_failed(run_id, str(e))


def fetch_and_load_video_stats():
    """Fetch video stats for each channel and load into raw + staging."""
    extractor   = YouTubeExtractor()
    loader      = PostgresLoader()
    transformer = VideoTransformer()
    today       = date.today()

    resolved = loader.get_resolved_handles()

    for channel in CHANNELS:
        handle     = channel["handle"]
        channel_id = resolved.get(handle)

        if not channel_id:
            continue

        try:
            video_ids = extractor.fetch_video_ids(channel_id, max_results=20)
            if not video_ids:
                logger.warning("No videos found for %s", handle)
                continue

            raw_stats = extractor.fetch_video_stats(video_ids)
            loader.save_video_snapshots(raw_stats)

            for raw in raw_stats:
                staged_video    = transformer.transform_video(raw)
                staged_snapshot = transformer.transform_snapshot(raw, today)

                loader.upsert_staging_video(staged_video)
                loader.upsert_staging_video_snapshot(staged_snapshot)

            logger.info("Loaded %d videos for %s", len(raw_stats), handle)

        except Exception as e:
            logger.error("Video fetch failed for %s: %s", handle, str(e))


def run_quality_checks():
    """Validate staging data before loading to marts."""
    from sqlalchemy import text
    loader    = PostgresLoader()
    validator = DataValidator()
    today     = date.today()

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

    channel_records = [row._mapping for row in channel_rows]
    video_records   = [row._mapping for row in video_rows]

    channel_ok = validator.validate_channel_snapshots(channel_records)
    video_ok   = validator.validate_video_snapshots(video_records)

    if not channel_ok:
        raise ValueError("Channel quality checks failed — marts load aborted")


def load_to_marts():
    """Load validated staging data into the marts star schema."""
    from sqlalchemy import text
    loader = PostgresLoader()
    today  = date.today()

    with loader.engine.begin() as conn:

        # dim_channel
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

        # dim_video
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

        # fct_channel_snapshots
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

        # fct_video_stats
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
                END AS engagement_rate
            FROM staging.video_snapshots
            WHERE snapshot_date = :today
            ON CONFLICT (video_id, date_key) DO UPDATE SET
                view_count      = EXCLUDED.view_count,
                like_count      = EXCLUDED.like_count,
                comment_count   = EXCLUDED.comment_count,
                engagement_rate = EXCLUDED.engagement_rate
        """), {"today": today})

    logger.info("Marts load complete for %s", today)


#  DAG definition                                                      

with DAG(
    dag_id="youtube_arabic_pipeline",
    default_args=default_args,
    description="Daily ETL for Arabic YouTube channels (1M+ subscribers)",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["youtube", "arabic", "etl"],
) as dag:

    t1 = PythonOperator(
        task_id="resolve_handles",
        python_callable=resolve_handles,
    )

    t2 = PythonOperator(
        task_id="fetch_channel_snapshots",
        python_callable=fetch_and_load_channel_snapshots,
    )

    t3 = PythonOperator(
        task_id="fetch_video_stats",
        python_callable=fetch_and_load_video_stats,
    )

    t4 = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks,
    )

    t5 = PythonOperator(
        task_id="load_to_marts",
        python_callable=load_to_marts,
    )

    t1 >> t2 >> t3 >> t4 >> t5