"""AcoustID fingerprint lookup (optional API key)."""

from dataclasses import dataclass

from app.logging import get_logger

logger = get_logger("TAGGER")

try:
    import acoustid  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    acoustid = None


@dataclass(frozen=True)
class AcoustIdMatch:
    artist: str
    title: str
    album: str | None
    mix_version: str | None
    recording_id: str | None
    score: float


def lookup_by_fingerprint(
    api_key: str,
    raw_fingerprint: str,
    duration_seconds: float,
) -> AcoustIdMatch | None:
    if not api_key or acoustid is None:
        return None

    try:
        response = acoustid.lookup(
            api_key,
            raw_fingerprint,
            int(duration_seconds),
            meta=["recordings"],
        )
        matches = list(acoustid.parse_lookup_result(response))
    except acoustid.AcoustidError as exc:
        logger.warning("acoustid_lookup_failed", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("acoustid_lookup_error", error=str(exc))
        return None

    if not matches:
        return None

    try:
        score, recording_id, title, artist = matches[0]
    except (ValueError, TypeError) as exc:
        logger.warning("acoustid_parse_match_failed", error=str(exc))
        return None

    return AcoustIdMatch(
        artist=artist or "Unknown Artist",
        title=title or "Unknown Title",
        album=None,
        mix_version=None,
        recording_id=recording_id,
        score=float(score),
    )
