from datetime import date, datetime
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ChannelTransformer:

    def transform_channel(self, raw: dict) -> dict:
        """
        Transform raw channel snapshot into staging.channels format.
        """
        return {
            "channel_id":     raw.get("channel_id"),
            "name":           self._clean_text(raw.get("name")),
            "description":    self._clean_text(raw.get("description")),
            "country":        raw.get("country"),
            "published_at":   self._parse_datetime(raw.get("published_at")),
            "thumbnail_url":  raw.get("thumbnail_url"),
        }

    def transform_snapshot(self, raw: dict, snapshot_date: date) -> dict:
        """
        Transform raw channel snapshot into staging.channel_snapshots format.
        """
        return {
            "channel_id":       raw.get("channel_id"),
            "snapshot_date":    snapshot_date,
            "subscriber_count": self._safe_int(raw.get("subscriber_count")),
            "total_view_count": self._safe_int(raw.get("total_view_count")),
            "video_count":      self._safe_int(raw.get("video_count")),
        }

# Helper

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        return value.strip()

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning("Could not parse datetime: %s", value)
            return None

    def _safe_int(self, value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0