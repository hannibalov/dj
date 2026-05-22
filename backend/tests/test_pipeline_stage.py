from datetime import UTC, datetime

import pytest

from app.models.enums import TrackStatus
from app.models.track import Track
from app.utils.pipeline_stage import resolve_pipeline_stage


def _track(**kwargs: object) -> Track:
    defaults: dict[str, object] = {
        "source_path": "/watch/song.mp3",
        "status": TrackStatus.INGESTED,
    }
    defaults.update(kwargs)
    return Track(**defaults)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (TrackStatus.QUEUED, "queued"),
        (TrackStatus.PROCESSING, "ingesting"),
        (TrackStatus.READY, "ready"),
        (TrackStatus.REVIEW, "review"),
        (TrackStatus.DUPLICATE, "duplicate"),
        (TrackStatus.FAILED, "failed"),
        (TrackStatus.ARCHIVED, "archived"),
    ],
)
def test_terminal_statuses_map_directly(status: TrackStatus, expected: str) -> None:
    assert resolve_pipeline_stage(_track(status=status), has_fingerprint=False) == expected


def test_terminal_status_ignores_partial_progress_fields() -> None:
    """Ready/review tracks keep their terminal stage even without analysis metadata."""
    ready = _track(status=TrackStatus.READY, integrated_lufs=None, tagged_at=None)
    assert resolve_pipeline_stage(ready, has_fingerprint=False) == "ready"


@pytest.mark.parametrize(
    ("integrated_lufs", "has_fingerprint", "tagged_at", "expected"),
    [
        (None, False, None, "awaiting_analyze"),
        (None, True, None, "awaiting_analyze"),  # reanalyze: LUFS cleared, fp row kept
        (-14.0, False, None, "awaiting_fingerprint"),
        (-14.0, True, None, "awaiting_tag"),  # analyze done; tag is next (fp may be reused)
        (-14.0, True, datetime.now(UTC), "awaiting_route"),
    ],
)
def test_ingested_sub_stages_follow_worker_chain(
    integrated_lufs: float | None,
    has_fingerprint: bool,
    tagged_at: datetime | None,
    expected: str,
) -> None:
    track = _track(
        status=TrackStatus.INGESTED,
        integrated_lufs=integrated_lufs,
        tagged_at=tagged_at,
    )
    assert resolve_pipeline_stage(track, has_fingerprint=has_fingerprint) == expected
