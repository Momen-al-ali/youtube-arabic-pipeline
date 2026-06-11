from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataValidator:

    def validate_channel_snapshots(self, records: list[dict]) -> bool:
        """
        Validate channel snapshots before loading to marts.
        Returns True if all checks pass, False if any fail.
        """
        passed = True

        # Check 1: not empty
        if not records:
            logger.error("QUALITY CHECK FAILED: channel_snapshots is empty")
            return False

        # Check 2: no null channel_id
        nulls = [r for r in records if not r.get("channel_id")]
        if nulls:
            logger.error(
                "QUALITY CHECK FAILED: %d records have null channel_id", len(nulls)
            )
            passed = False

        # Check 3: no negative subscriber counts
        negatives = [r for r in records if r.get("subscriber_count", 0) < 0]
        if negatives:
            logger.error(
                "QUALITY CHECK FAILED: %d records have negative subscriber_count",
                len(negatives),
            )
            passed = False

        # Check 4: no duplicates on channel_id + snapshot_date
        seen = set()
        dupes = []
        for r in records:
            key = (r.get("channel_id"), r.get("snapshot_date"))
            if key in seen:
                dupes.append(key)
            seen.add(key)
        if dupes:
            logger.error(
                "QUALITY CHECK FAILED: %d duplicate (channel_id, snapshot_date) pairs",
                len(dupes),
            )
            passed = False

        if passed:
            logger.info(
                "QUALITY CHECK PASSED: channel_snapshots — %d records", len(records)
            )

        return passed

    def validate_video_snapshots(self, records: list[dict]) -> bool:
        """
        Validate video snapshots before loading to marts.
        Returns True if all checks pass, False if any fail.
        """
        passed = True

        # Check 1: not empty
        if not records:
            logger.warning("QUALITY CHECK WARNING: video_snapshots is empty")
            return True  # empty videos is a warning, not a blocker

        # Check 2: no null video_id
        nulls = [r for r in records if not r.get("video_id")]
        if nulls:
            logger.error(
                "QUALITY CHECK FAILED: %d records have null video_id", len(nulls)
            )
            passed = False

        # Check 3: no negative view counts
        negatives = [r for r in records if r.get("view_count", 0) < 0]
        if negatives:
            logger.error(
                "QUALITY CHECK FAILED: %d records have negative view_count",
                len(negatives),
            )
            passed = False

        # Check 4: no duplicates on video_id + snapshot_date
        seen = set()
        dupes = []
        for r in records:
            key = (r.get("video_id"), r.get("snapshot_date"))
            if key in seen:
                dupes.append(key)
            seen.add(key)
        if dupes:
            logger.error(
                "QUALITY CHECK FAILED: %d duplicate (video_id, snapshot_date) pairs",
                len(dupes),
            )
            passed = False

        if passed:
            logger.info(
                "QUALITY CHECK PASSED: video_snapshots — %d records", len(records)
            )

        return passed