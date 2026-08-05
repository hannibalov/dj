from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.track import Track
from app.services.metadata_sanity_service import MetadataSanityService


def _known_artist_track(tmp_path: Path, name: str, artist: str) -> Track:
    return Track(
        source_path=str(tmp_path / name),
        artist=artist,
        title=f"Unrelated Song Title {name}",
        status=TrackStatus.READY,
        tagged_at=datetime.now(UTC),
        tag_confidence=0.9,
    )


def test_reversed_artist_title_flagged_possible_swap(db_session: Session, tmp_path: Path) -> None:
    known = _known_artist_track(tmp_path, "known.mp3", "Eric Prydz")
    reversed_track = Track(
        source_path=str(tmp_path / "reversed.mp3"),
        artist="Opus",
        title="Eric Prydz",
        status=TrackStatus.INGESTED,
    )
    db_session.add_all([known, reversed_track])
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = MetadataSanityService(db_session).run_check()

    assert result.flagged_possible_swap == 1
    db_session.refresh(reversed_track)
    assert reversed_track.metadata_issue == "possible_swap"


def test_title_contains_artist_flagged(db_session: Session, tmp_path: Path) -> None:
    track = Track(
        source_path=str(tmp_path / "polluted.mp3"),
        artist="Daft Punk",
        title="Daft Punk - One More Time",
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = MetadataSanityService(db_session).run_check()

    assert result.flagged_artist_in_title == 1
    db_session.refresh(track)
    assert track.metadata_issue == "artist_in_title"


def test_clean_track_has_no_issue(db_session: Session, tmp_path: Path) -> None:
    track = Track(
        source_path=str(tmp_path / "clean.mp3"),
        artist="Daft Punk",
        title="One More Time",
        status=TrackStatus.INGESTED,
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = MetadataSanityService(db_session).run_check()

    assert result.flagged_possible_swap == 0
    assert result.flagged_artist_in_title == 0
    db_session.refresh(track)
    assert track.metadata_issue is None


def test_anomaly_ratio_flips_true_past_threshold(db_session: Session, tmp_path: Path) -> None:
    tracks = []
    for i in range(8):
        tracks.append(
            Track(
                source_path=str(tmp_path / f"clean_{i}.mp3"),
                artist="Some Artist",
                title=f"Clean Title {i}",
                status=TrackStatus.INGESTED,
            )
        )
    for i in range(2):
        tracks.append(
            Track(
                source_path=str(tmp_path / f"polluted_{i}.mp3"),
                artist="Some Artist",
                title=f"Some Artist - Track {i}",
                status=TrackStatus.INGESTED,
            )
        )
    db_session.add_all(tracks)
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = MetadataSanityService(db_session).run_check()

    # 2 flagged out of 10 scanned = 0.2 > 0.15 threshold
    assert result.scanned == 10
    assert result.flagged_artist_in_title == 2
    assert result.artist_in_title_ratio == 0.2
    assert result.anomaly is True


def test_anomaly_ratio_false_below_threshold(db_session: Session, tmp_path: Path) -> None:
    tracks = [
        Track(
            source_path=str(tmp_path / f"clean_{i}.mp3"),
            artist="Some Artist",
            title=f"Clean Title {i}",
            status=TrackStatus.INGESTED,
        )
        for i in range(9)
    ]
    tracks.append(
        Track(
            source_path=str(tmp_path / "polluted.mp3"),
            artist="Some Artist",
            title="Some Artist - Track",
            status=TrackStatus.INGESTED,
        )
    )
    db_session.add_all(tracks)
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = MetadataSanityService(db_session).run_check()

    assert result.scanned == 10
    assert result.flagged_artist_in_title == 1
    assert result.anomaly is False


def test_previously_flagged_track_cleared_after_fix(db_session: Session, tmp_path: Path) -> None:
    track = Track(
        source_path=str(tmp_path / "fixed.mp3"),
        artist="Daft Punk",
        title="One More Time",
        status=TrackStatus.INGESTED,
        metadata_issue="artist_in_title",
    )
    db_session.add(track)
    db_session.commit()

    with patch("app.services.metadata_sanity_service.notify_pipeline_changed"):
        result = MetadataSanityService(db_session).run_check()

    assert result.flagged_artist_in_title == 0
    db_session.refresh(track)
    assert track.metadata_issue is None
