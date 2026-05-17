from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisResult:
    bpm: float | None = None
    bpm_confidence: float | None = None
    musical_key: str | None = None
    scale: str | None = None
    camelot: str | None = None
    key_confidence: float | None = None
    energy: int | None = None
    integrated_lufs: float | None = None
    true_peak_db: float | None = None

    @property
    def musical_key_label(self) -> str | None:
        if not self.musical_key or not self.scale:
            return None
        return f"{self.musical_key} {self.scale}"
