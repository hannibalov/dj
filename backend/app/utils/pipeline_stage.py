"""Derive a display pipeline step from track status and progress fields."""

from app.models.enums import TrackStatus
from app.models.track import Track


def resolve_pipeline_stage(track: Track, *, has_fingerprint: bool) -> str:
    """
    Map a track to the next pipeline step it is waiting on.

    Terminal statuses mirror ``TrackStatus``. ``INGESTED`` tracks show where they
    are in analyze → fingerprint → tag → route based on completed fields, not
    retained DB rows alone (e.g. reanalyze keeps fingerprint rows but still shows
    ``awaiting_fingerprint`` until analyze has run again).
    """
    status = track.status
    if status == TrackStatus.PROCESSING:
        return "ingesting"
    if status == TrackStatus.QUEUED:
        return "queued"
    if status == TrackStatus.READY:
        return "ready"
    if status == TrackStatus.REVIEW:
        return "review"
    if status == TrackStatus.DUPLICATE:
        return "duplicate"
    if status == TrackStatus.FAILED:
        return "failed"
    if status == TrackStatus.ARCHIVED:
        return "archived"

    if track.integrated_lufs is None:
        return "awaiting_analyze"
    if not has_fingerprint:
        return "awaiting_fingerprint"
    if track.tagged_at is None:
        return "awaiting_tag"
    return "awaiting_route"
