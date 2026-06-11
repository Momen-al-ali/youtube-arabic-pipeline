from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.utils.config import get_config
from src.utils.logging_config import get_logger


class PostgresLoader:

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        config = get_config()
        self.engine: Engine = create_engine(config.postgres_conn_string)

    # ------------------------------------------------------------------ #
    #  Idempotency                                                         #
    # ------------------------------------------------------------------ #

    def is_already_run(self, channel_id: str, run_date: date) -> bool:
        """Return True if this channel already has a successful run today."""
        sql = text("""
            SELECT 1 FROM raw.pipeline_runs
            WHERE channel_id = :channel_id
              AND run_date   = :run_date
              AND status     = 'success'
        """)
        with self.engine.connect() as conn:
            result = conn.execute(sql, {"channel_id": channel_id, "run_date": run_date})
            return result.fetchone() is not None

    def mark_run_started(self, channel_id: str, run_date: date) -> int:
        """Insert a 'started' run record, return its id."""
        sql = text("""
            INSERT INTO raw.pipeline_runs (run_date, channel_id, status)
            VALUES (:run_date, :channel_id, 'started')
            ON CONFLICT (run_date, channel_id) DO UPDATE
                SET status = 'started', error_message = NULL
            RETURNING id
        """)
        with self.engine.begin() as conn:
            result = conn.execute(sql, {"run_date": run_date, "channel_id": channel_id})
            return result.fetchone()[0]

    def mark_run_success(self, run_id: int, records_fetched: int):
        sql = text("""
            UPDATE raw.pipeline_runs
            SET status = 'success', records_fetched = :records
            WHERE id = :run_id
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, {"records": records_fetched, "run_id": run_id})

    def mark_run_failed(self, run_id: int, error: str):
        sql = text("""
            UPDATE raw.pipeline_runs
            SET status = 'failed', error_message = :error
            WHERE id = :run_id
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, {"error": error, "run_id": run_id})

    # ------------------------------------------------------------------ #
    #  Raw layer                                                           #
    # ------------------------------------------------------------------ #

    def save_channel_handle(self, handle: str, channel_id: str):
        """Store resolved handle → channel_id. Skip if already exists."""
        sql = text("""
            INSERT INTO raw.channel_handles (handle, channel_id)
            VALUES (:handle, :channel_id)
            ON CONFLICT (handle) DO NOTHING
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, {"handle": handle, "channel_id": channel_id})

    def get_resolved_handles(self) -> dict[str, str]:
        """Return all already-resolved handle → channel_id mappings."""
        sql = text("SELECT handle, channel_id FROM raw.channel_handles")
        with self.engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return {row[0]: row[1] for row in rows}

    def save_channel_snapshot(self, data: dict):
        """Insert one channel snapshot. Skip if already fetched today."""
        sql = text("""
            INSERT INTO raw.channel_snapshots (
                channel_id, name, description, country,
                published_at, thumbnail_url,
                subscriber_count, total_view_count, video_count
            ) VALUES (
                :channel_id, :name, :description, :country,
                :published_at, :thumbnail_url,
                :subscriber_count, :total_view_count, :video_count
            )
            ON CONFLICT DO NOTHING
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, data)
        self.logger.info("Saved channel snapshot: %s", data.get("name"))

    def save_video_snapshots(self, records: list[dict]):
        """Bulk insert video snapshots. Skip duplicates."""
        if not records:
            return
        sql = text("""
            INSERT INTO raw.video_snapshots (
                video_id, channel_id, title,
                published_at, duration,
                view_count, like_count, comment_count
            ) VALUES (
                :video_id, :channel_id, :title,
                :published_at, :duration,
                :view_count, :like_count, :comment_count
            )
            ON CONFLICT DO NOTHING
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, records)
        self.logger.info("Saved %d video snapshots", len(records))

    # ------------------------------------------------------------------ #
    #  Staging layer                                                       #
    # ------------------------------------------------------------------ #

    def upsert_staging_channel(self, data: dict):
        sql = text("""
            INSERT INTO staging.channels (
                channel_id, name, description,
                country, published_at, thumbnail_url
            ) VALUES (
                :channel_id, :name, :description,
                :country, :published_at, :thumbnail_url
            )
            ON CONFLICT (channel_id) DO UPDATE SET
                name          = EXCLUDED.name,
                description   = EXCLUDED.description,
                country       = EXCLUDED.country,
                thumbnail_url = EXCLUDED.thumbnail_url,
                updated_at    = NOW()
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, data)

    def upsert_staging_channel_snapshot(self, data: dict):
        sql = text("""
            INSERT INTO staging.channel_snapshots (
                channel_id, snapshot_date,
                subscriber_count, total_view_count, video_count
            ) VALUES (
                :channel_id, :snapshot_date,
                :subscriber_count, :total_view_count, :video_count
            )
            ON CONFLICT (channel_id, snapshot_date) DO UPDATE SET
                subscriber_count = EXCLUDED.subscriber_count,
                total_view_count = EXCLUDED.total_view_count,
                video_count      = EXCLUDED.video_count
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, data)

    def upsert_staging_video(self, data: dict):
        sql = text("""
            INSERT INTO staging.videos (
                video_id, channel_id, title,
                published_at, duration_seconds
            ) VALUES (
                :video_id, :channel_id, :title,
                :published_at, :duration_seconds
            )
            ON CONFLICT (video_id) DO UPDATE SET
                title            = EXCLUDED.title,
                duration_seconds = EXCLUDED.duration_seconds,
                updated_at       = NOW()
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, data)

    def upsert_staging_video_snapshot(self, data: dict):
        sql = text("""
            INSERT INTO staging.video_snapshots (
                video_id, channel_id, snapshot_date,
                view_count, like_count, comment_count
            ) VALUES (
                :video_id, :channel_id, :snapshot_date,
                :view_count, :like_count, :comment_count
            )
            ON CONFLICT (video_id, snapshot_date) DO UPDATE SET
                view_count    = EXCLUDED.view_count,
                like_count    = EXCLUDED.like_count,
                comment_count = EXCLUDED.comment_count
        """)
        with self.engine.begin() as conn:
            conn.execute(sql, data)