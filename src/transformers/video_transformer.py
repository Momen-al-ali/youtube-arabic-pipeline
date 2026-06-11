import re
from datetime import date, datetime
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class VideoTransformer:

    def transform_video(self, raw: dict) -> dict:
        """
        Transform raw video metadata into staging.videos format.
        """
        return {
            "video_id":         raw.get("video_id"),
            "channel_id":       raw.get("channel_id"),
            "title":            self._clean_text(raw.get("title")),
            "published_at":     self._parse_datetime(raw.get("published_at")),
            "duration_seconds": self._parse_duration(raw.get("duration")),
        }

    def transform_snapshot(self, raw: dict, snapshot_date: date) -> dict:
        """
        Transform raw video stats into staging.video_snapshots format.
        """
        view_count    = self._safe_int(raw.get("view_count"))
        like_count    = self._safe_int(raw.get("like_count"))
        comment_count = self._safe_int(raw.get("comment_count"))

        return {
            "video_id":      raw.get("video_id"),
            "channel_id":    raw.get("channel_id"),
            "snapshot_date": snapshot_date,
            "view_count":    view_count,
            "like_count":    like_count,
            "comment_count": comment_count,
        }

    #  Helpers                                                             
    

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

    def _parse_duration(self, duration: str | None) -> int | None:
        """
        Convert ISO 8601 duration (PT1H2M3S) to total seconds.
        Examples:
            PT5M30S  → 330
            PT1H     → 3600
            PT2M     → 120
        """
        if not duration:
            return None
        try:
            pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
            match = re.match(pattern, duration)
            if not match:
                return None
            hours   = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            logger.warning("Could not parse duration: %s", duration)
            return None