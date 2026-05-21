from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TrackStatus
from app.models.track import Track
from app.schemas.track import TrackResponse
from app.schemas.track_summary import TrackStatusSummary
from app.utils.audio_format import get_format_info


class TrackService:
    # Dashboard table cap; pipeline counts use count_by_status() for full totals.
    DEFAULT_LIST_LIMIT = 500

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_tracks(self, limit: int | None = None) -> list[TrackResponse]:
        cap = limit if limit is not None else self.DEFAULT_LIST_LIMIT
        rows = (
            self._db.execute(select(Track).order_by(Track.updated_at.desc()).limit(cap))
            .scalars()
            .all()
        )
        return [self._to_response(r) for r in rows]

    def status_summary(self) -> TrackStatusSummary:
        rows = self._db.execute(
            select(Track.status, func.count()).group_by(Track.status)
        ).all()
        by_status = {status.value: count for status, count in rows}
        total = sum(by_status.values())
        return TrackStatusSummary(total=total, by_status=by_status)

    def get_track(self, track_id: int) -> TrackResponse | None:
        row = self._db.get(Track, track_id)
        return self._to_response(row) if row else None

    @staticmethod
    def _to_response(track: Track) -> TrackResponse:
        response = TrackResponse.model_validate(track)
        audio_path = _resolve_track_audio_path(track)
        if audio_path is None:
            return response
        info = get_format_info(audio_path)
        return response.model_copy(
            update={
                "format_extension": info.extension,
                "audio_family": info.family,
                "bitrate_kbps": info.bitrate_kbps,
                "sample_rate_hz": info.sample_rate_hz,
                "bits_per_sample": info.bits_per_sample,
            }
        )


def _resolve_track_audio_path(track: Track) -> Path | None:
    for path_str in (track.final_path, track.processing_path, track.source_path):
        if not path_str:
            continue
        path = Path(path_str)
        if path.is_file():
            return path
    return None
