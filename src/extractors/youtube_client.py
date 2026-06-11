import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.utils.base import BaseExtractor
from src.utils.config import get_config


class YouTubeExtractor(BaseExtractor):

    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self):
        super().__init__()
        config = get_config()
        self.youtube = build("youtube", "v3", developerKey=config.youtube_api_key)

    def extract(self) -> list[dict]:
        """
        Required by BaseExtractor — not used directly.
        Use fetch_channel_stats() and fetch_video_stats() instead.
        """
        return []

    #  Channel handle → channel_id resolution                             

    def resolve_handle(self, handle: str) -> str | None:
        """Convert a YouTube handle (e.g. 'alarabiya') to a channel_id."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = (
                    self.youtube.channels()
                    .list(part="id", forHandle=handle)
                    .execute()
                )
                items = response.get("items", [])
                if items:
                    return items[0]["id"]
                self.logger.warning("No channel found for handle: @%s", handle)
                return None

            except HttpError as e:
                self._handle_http_error(e, handle, attempt)

        return None

    #  Channel statistics snapshot                                         
    

    def fetch_channel_stats(self, channel_id: str) -> dict | None:
        """
        Fetch current stats for one channel.
        Returns a flat dict ready to insert into raw_channel_snapshots.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                response = (
                    self.youtube.channels()
                    .list(
                        part="snippet,statistics",
                        id=channel_id,
                    )
                    .execute()
                )
                items = response.get("items", [])
                if not items:
                    self.logger.warning("No data returned for channel_id: %s", channel_id)
                    return None

                item = items[0]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                return {
                    "channel_id":        channel_id,
                    "name":              snippet.get("title"),
                    "description":       snippet.get("description"),
                    "country":           snippet.get("country"),
                    "published_at":      snippet.get("publishedAt"),
                    "thumbnail_url":     snippet.get("thumbnails", {})
                                                .get("high", {})
                                                .get("url"),
                    "subscriber_count":  int(stats.get("subscriberCount", 0)),
                    "total_view_count":  int(stats.get("viewCount", 0)),
                    "video_count":       int(stats.get("videoCount", 0)),
                }

            except HttpError as e:
                self._handle_http_error(e, channel_id, attempt)

        return None

    #  Video list for a channel                                            

    def fetch_video_ids(self, channel_id: str, max_results: int = 10) -> list[str]:
        """
        Fetch latest video IDs using the uploads playlist — no quota restrictions.
        Every channel has an uploads playlist: channel_id UC... → playlist UU...
        """
        # Convert channel_id to uploads playlist_id
        playlist_id = "UU" + channel_id[2:]

        video_ids = []

        for attempt in range(self.MAX_RETRIES):
            try:
                response = (
                    self.youtube.playlistItems()
                    .list(
                        part="contentDetails",
                        playlistId=playlist_id,
                        maxResults=min(max_results, 50),
                    )
                    .execute()
                )

                for item in response.get("items", []):
                    video_ids.append(item["contentDetails"]["videoId"])

                return video_ids

            except HttpError as e:
                self._handle_http_error(e, channel_id, attempt)

        return video_ids                                                

    def fetch_video_stats(self, video_ids: list[str]) -> list[dict]:
        """
        Fetch stats for a list of video IDs.
        YouTube allows max 50 IDs per request — we batch automatically.
        """
        if not video_ids:
            return []

        results = []
        # batch into chunks of 50
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            results.extend(self._fetch_video_stats_batch(chunk))

        return results

    def _fetch_video_stats_batch(self, video_ids: list[str]) -> list[dict]:
        for attempt in range(self.MAX_RETRIES):
            try:
                response = (
                    self.youtube.videos()
                    .list(
                        part="snippet,statistics,contentDetails",
                        id=",".join(video_ids),
                    )
                    .execute()
                )

                results = []
                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    stats   = item.get("statistics", {})
                    content = item.get("contentDetails", {})

                    results.append({
                        "video_id":       item["id"],
                        "channel_id":     snippet.get("channelId"),
                        "title":          snippet.get("title"),
                        "published_at":   snippet.get("publishedAt"),
                        "duration":       content.get("duration"),
                        "view_count":     int(stats.get("viewCount",    0)),
                        "like_count":     int(stats.get("likeCount",    0)),
                        "comment_count":  int(stats.get("commentCount", 0)),
                    })

                return results

            except HttpError as e:
                self._handle_http_error(e, str(video_ids[:2]), attempt)

        return []

    #  Shared error handler                                                

    def _handle_http_error(self, error: HttpError, context: str, attempt: int):
        status = error.resp.status

        if status == 403:
            self.logger.error("API quota exceeded. Context: %s", context)
            raise error  # quota errors — stop immediately, no point retrying

        if status == 404:
            self.logger.warning("Resource not found: %s", context)
            return  # not found — skip silently

        self.logger.warning(
            "HTTP %s on attempt %d/%d for %s — retrying in %ds",
            status, attempt + 1, self.MAX_RETRIES, context, self.RETRY_DELAY,
        )
        time.sleep(self.RETRY_DELAY)