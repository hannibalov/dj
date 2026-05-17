"""Chromaprint fingerprinting and duplicate detection."""

from app.fingerprint.chromaprint import FingerprintData, compute_fingerprint
from app.fingerprint.version_priority import preferred_track_ids

__all__ = ["FingerprintData", "compute_fingerprint", "preferred_track_ids"]
