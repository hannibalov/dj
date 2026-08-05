"""Library-wide sanity audit: flag tracks with likely-reversed or artist-polluted metadata."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.metadata.known_artists import load_known_artists
from app.metadata.sanity import detect_possible_swap, title_contains_artist
from app.models.track import Track
from app.services.notify import notify_pipeline_changed

logger = get_logger("TAGGER")

# If more than this fraction of scanned tracks look like artist-in-title pollution,
# something is systemically wrong (e.g. a bad bulk import) rather than a few one-off tags.
ANOMALY_RATIO_THRESHOLD = 0.15


@dataclass(frozen=True)
class MetadataSanityResult:
    status: str
    scanned: int
    flagged_possible_swap: int
    flagged_artist_in_title: int
    artist_in_title_ratio: float
    anomaly: bool


class MetadataSanityService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def run_check(self) -> MetadataSanityResult:
        known_artists = load_known_artists(self._db)

        tracks = (
            self._db.execute(
                select(Track).where(
                    Track.artist.isnot(None),
                    Track.artist != "",
                    Track.title.isnot(None),
                    Track.title != "",
                )
            )
            .scalars()
            .all()
        )

        scanned = 0
        flagged_possible_swap = 0
        flagged_artist_in_title = 0
        changed = 0

        for track in tracks:
            artist = track.artist
            title = track.title
            if not artist or not title:
                continue
            scanned += 1

            possible_swap = detect_possible_swap(artist, title, known_artists)
            artist_in_title = title_contains_artist(artist, title)

            if possible_swap:
                flagged_possible_swap += 1
            if artist_in_title:
                flagged_artist_in_title += 1

            if possible_swap:
                new_issue = "possible_swap"
            elif artist_in_title:
                new_issue = "artist_in_title"
            else:
                new_issue = None
            if track.metadata_issue != new_issue:
                track.metadata_issue = new_issue
                changed += 1

        ratio = flagged_artist_in_title / scanned if scanned else 0.0
        anomaly = ratio > ANOMALY_RATIO_THRESHOLD

        self._db.commit()

        if changed:
            summary = (
                f"Metadata sanity check: scanned {scanned}, "
                f"{flagged_possible_swap} possible swap, {flagged_artist_in_title} artist-in-title"
            )
            if anomaly:
                summary += " — anomaly ratio exceeded, check for a systemic tagging issue"
            logger.info(
                "metadata_sanity_checked",
                scanned=scanned,
                flagged_possible_swap=flagged_possible_swap,
                flagged_artist_in_title=flagged_artist_in_title,
                anomaly=anomaly,
                changed=changed,
            )
            notify_pipeline_changed(summary)

        return MetadataSanityResult(
            status="ok",
            scanned=scanned,
            flagged_possible_swap=flagged_possible_swap,
            flagged_artist_in_title=flagged_artist_in_title,
            artist_in_title_ratio=ratio,
            anomaly=anomaly,
        )
