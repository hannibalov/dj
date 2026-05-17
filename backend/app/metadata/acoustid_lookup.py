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
        results = list(
            acoustid.lookup(api_key, raw_fingerprint, int(duration_seconds), meta=["recordings"])
        )
    except acoustid.AcoustidError as exc:
        logger.warning("acoustid_lookup_failed", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("acoustid_lookup_error", error=str(exc))
        return None

    if not results:
        return None

    score, recording_id, title, artist = results[0]
    album: str | None = None
    mix_version: str | None = None

    return AcoustIdMatch(
        artist=artist or "Unknown Artist",
        title=title or "Unknown Title",
        album=album,
        mix_version=mix_version,
        recording_id=recording_id,
        score=float(score),
    )
