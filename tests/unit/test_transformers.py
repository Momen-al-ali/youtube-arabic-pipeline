import pytest
from datetime import date
from src.transformers.channel_transformer import ChannelTransformer
from src.transformers.video_transformer import VideoTransformer


# ------------------------------------------------------------------ #
#  ChannelTransformer tests                                            #
# ------------------------------------------------------------------ #

class TestChannelTransformer:

    def setup_method(self):
        self.transformer = ChannelTransformer()
        self.raw = {
            "channel_id":       "UC123",
            "name":             "  Test Channel  ",
            "description":      "A test channel",
            "country":          "SA",
            "published_at":     "2020-01-01T00:00:00Z",
            "thumbnail_url":    "https://example.com/thumb.jpg",
            "subscriber_count": 1000000,
            "total_view_count": 50000000,
            "video_count":      500,
        }

    def test_transform_channel_cleans_name(self):
        result = self.transformer.transform_channel(self.raw)
        assert result["name"] == "Test Channel"

    def test_transform_channel_parses_datetime(self):
        result = self.transformer.transform_channel(self.raw)
        assert result["published_at"] is not None

    def test_transform_channel_handles_null_name(self):
        self.raw["name"] = None
        result = self.transformer.transform_channel(self.raw)
        assert result["name"] is None

    def test_transform_snapshot_types(self):
        result = self.transformer.transform_snapshot(self.raw, date.today())
        assert isinstance(result["subscriber_count"], int)
        assert isinstance(result["total_view_count"], int)
        assert isinstance(result["video_count"], int)

    def test_transform_snapshot_handles_null_counts(self):
        self.raw["subscriber_count"] = None
        result = self.transformer.transform_snapshot(self.raw, date.today())
        assert result["subscriber_count"] == 0


# ------------------------------------------------------------------ #
#  VideoTransformer tests                                              #
# ------------------------------------------------------------------ #

class TestVideoTransformer:

    def setup_method(self):
        self.transformer = VideoTransformer()
        self.raw = {
            "video_id":     "vid123",
            "channel_id":   "UC123",
            "title":        "  Test Video  ",
            "published_at": "2024-01-15T10:00:00Z",
            "duration":     "PT5M30S",
            "view_count":   100000,
            "like_count":   4000,
            "comment_count": 200,
        }

    def test_parse_duration_minutes_seconds(self):
        result = self.transformer.transform_video(self.raw)
        assert result["duration_seconds"] == 330

    def test_parse_duration_hours(self):
        self.raw["duration"] = "PT1H"
        result = self.transformer.transform_video(self.raw)
        assert result["duration_seconds"] == 3600

    def test_parse_duration_full(self):
        self.raw["duration"] = "PT1H2M3S"
        result = self.transformer.transform_video(self.raw)
        assert result["duration_seconds"] == 3723

    def test_parse_duration_none(self):
        self.raw["duration"] = None
        result = self.transformer.transform_video(self.raw)
        assert result["duration_seconds"] is None

    def test_transform_video_cleans_title(self):
        result = self.transformer.transform_video(self.raw)
        assert result["title"] == "Test Video"

    def test_transform_snapshot_counts(self):
        result = self.transformer.transform_snapshot(self.raw, date.today())
        assert result["view_count"] == 100000
        assert result["like_count"] == 4000
        assert result["comment_count"] == 200

    def test_transform_snapshot_handles_null_counts(self):
        self.raw["view_count"] = None
        result = self.transformer.transform_snapshot(self.raw, date.today())
        assert result["view_count"] == 0