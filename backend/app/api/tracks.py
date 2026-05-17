from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.track import TrackResponse
from app.schemas.track_actions import TrackActionResponse
from app.services.track_lifecycle_service import TrackLifecycleError, TrackLifecycleService
from app.services.track_service import TrackService

router = APIRouter()


@router.get("", response_model=list[TrackResponse])
def list_tracks(db: Session = Depends(get_db)) -> list[TrackResponse]:
    return TrackService(db).list_tracks()


@router.get("/{track_id}", response_model=TrackResponse)
def get_track(track_id: int, db: Session = Depends(get_db)) -> TrackResponse:
    track = TrackService(db).get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@router.post("/{track_id}/reset", response_model=TrackActionResponse)
def reset_track(track_id: int, db: Session = Depends(get_db)) -> TrackActionResponse:
    try:
        track = TrackLifecycleService(db).reset_track(track_id)
    except TrackLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrackActionResponse(
        status="ok",
        track=TrackResponse.model_validate(track),
        message="Pipeline reset; ingest job enqueued",
    )


@router.post("/{track_id}/confirm-review", response_model=TrackActionResponse)
def confirm_review(track_id: int, db: Session = Depends(get_db)) -> TrackActionResponse:
    try:
        track = TrackLifecycleService(db).confirm_review(track_id)
    except TrackLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrackActionResponse(
        status="ok",
        track=TrackResponse.model_validate(track),
        message="Moved to ready; other copies removed",
    )
