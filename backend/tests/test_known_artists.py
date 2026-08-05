from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.metadata.artist_title import resolve_artist_title
from app.metadata.known_artists import load_known_artists, match_known_artist
from app.metadata.tags import parse_filename_metadata
from app.models.enums import TrackStatus
from app.models.track import Track


def test_match_known_artist_exact_and_fuzzy() -> None:
    known = frozenset({"Eric Prydz", "CamelPhat"})
    assert match_known_artist("Eric Prydz", known) == "Eric Prydz"
    assert match_known_artist("camelphat", known) == "CamelPhat"
    assert match_known_artist("Eric Prydz", known) == "Eric Prydz"
    assert match_known_artist("Eric Prydzz", known) == "Eric Prydz"
    assert match_known_artist("Unknown Act", known) is None


def test_resolve_artist_title_uses_known_artists_for_reversed_filename() -> None:
    known = frozenset({"Oasis", "Eric Prydz"})
    artist, title = resolve_artist_title(
        "Wonderwall",
        "Oasis",
        known_artists=known,
    )
    assert artist == "Oasis"
    assert title == "Wonderwall"


def test_resolve_artist_title_corrects_misspelled_known_artist() -> None:
    known = frozenset({"Oasis"})
    artist, title = resolve_artist_title(
        "Wonderwall",
        "Oaisis",
        known_artists=known,
    )
    assert artist == "Oasis"
    assert title == "Wonderwall"


def test_parse_filename_metadata_with_known_artists(tmp_path: Path) -> None:
    path = tmp_path / "Wonderwall - Oaisis.mp3"
    path.write_bytes(b"fake")
    parsed = parse_filename_metadata(path, known_artists=frozenset({"Oasis"}))
    assert parsed.artist == "Oasis"
    assert parsed.title == "Wonderwall"


def test_load_known_artists_from_tagged_tracks(db_session: Session, tmp_path: Path) -> None:
    db_session.add(
        Track(
            source_path=str(tmp_path / "a.mp3"),
            artist="Eric Prydz",
            status=TrackStatus.READY,
            tagged_at=datetime.now(UTC),
            tag_confidence=0.92,
        )
    )
    db_session.add(
        Track(
            source_path=str(tmp_path / "b.mp3"),
            artist="Untagged Artist",
            status=TrackStatus.INGESTED,
        )
    )
    db_session.add(
        Track(
            source_path=str(tmp_path / "c.mp3"),
            artist="Wonderwall",
            title="Oasis",
            status=TrackStatus.READY,
            tagged_at=datetime.now(UTC),
            needs_metadata_review=True,
        )
    )
    db_session.commit()

    known = load_known_artists(db_session)
    assert "Eric Prydz" in known
    assert "Untagged Artist" not in known
    assert "Wonderwall" not in known
