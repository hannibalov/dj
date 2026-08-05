from pathlib import Path

from app.analysis.loudness import measure_loudness
from app.analysis.musical import measure_musical
from app.analysis.result import AnalysisResult


def analyze_audio(audio_path: Path) -> AnalysisResult:
    integrated_lufs, true_peak_db = measure_loudness(audio_path)
    bpm, bpm_confidence, key, scale, camelot, key_confidence = measure_musical(audio_path)

    # DJ energy 0-100 from loudness (Essentia Energy is sum-of-squares over the
    # file, so it always clips to 100).
    energy = _energy_from_lufs(integrated_lufs) if integrated_lufs is not None else None

    return AnalysisResult(
        bpm=bpm,
        bpm_confidence=bpm_confidence,
        musical_key=key,
        scale=scale,
        camelot=camelot,
        key_confidence=key_confidence,
        energy=energy,
        integrated_lufs=integrated_lufs,
        true_peak_db=true_peak_db,
    )


def _energy_from_lufs(integrated_lufs: float) -> int:
    """Rough DJ energy score when Essentia is unavailable."""
    # Typical club masters sit around -9 to -14 LUFS
    score = int((integrated_lufs + 24) * (100 / 18))
    return min(100, max(0, score))
