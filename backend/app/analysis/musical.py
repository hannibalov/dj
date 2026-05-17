from pathlib import Path

from app.analysis.camelot import to_camelot
from app.logging import get_logger

logger = get_logger("ANALYZER")

MusicalMetrics = tuple[
    float | None,
    float | None,
    str | None,
    str | None,
    str | None,
    float | None,
    int | None,
]


def measure_musical(audio_path: Path) -> MusicalMetrics:
    """BPM, bpm_confidence, key, scale, camelot, key_confidence, energy (0-100)."""
    try:
        import essentia.standard as es  # type: ignore[import-not-found]
    except ImportError:
        logger.info("essentia_unavailable", path=str(audio_path))
        return None, None, None, None, None, None, None

    try:
        loader = es.MonoLoader(filename=str(audio_path))
        audio = loader()
    except Exception as exc:
        logger.warning("essentia_load_failed", path=str(audio_path), error=str(exc))
        return None, None, None, None, None, None, None

    bpm, bpm_confidence = _extract_bpm(audio, es)
    key, scale, key_confidence = _extract_key(audio, es)
    camelot = to_camelot(key, scale) if key and scale else None
    energy = _extract_energy(audio, es)
    return bpm, bpm_confidence, key, scale, camelot, key_confidence, energy


def _extract_bpm(audio: object, es: object) -> tuple[float | None, float | None]:
    rhythm = es.RhythmExtractor2013(method="multifeature")  # type: ignore[attr-defined]
    bpm, _, confidence, _, _ = rhythm(audio)
    if bpm <= 0:
        return None, None
    return round(float(bpm), 1), round(float(confidence), 3)


def _extract_key(audio: object, es: object) -> tuple[str | None, str | None, float | None]:
    key_extractor = es.KeyExtractor()  # type: ignore[attr-defined]
    key, scale, strength = key_extractor(audio)
    if not key or key == "unknown":
        return None, None, None
    return str(key), str(scale), round(float(strength), 3)


def _extract_energy(audio: object, es: object) -> int | None:
    energy_algo = es.Energy()  # type: ignore[attr-defined]
    raw = float(energy_algo(audio))
    # Essentia Energy is mean square; map to 0-100 for DJ UI
    score = min(100, max(0, int(raw * 500)))
    return score
