"""Essentia / ffmpeg audio analysis."""

from app.analysis.analyzer import analyze_audio
from app.analysis.result import AnalysisResult

__all__ = ["AnalysisResult", "analyze_audio"]
