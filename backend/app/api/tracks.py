from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.track import TrackResponse
from app.schemas.track_actions import TrackActionResponse, TrackDeleteResponse
from app.services.track_lifecycle_service import TrackLifecycleError, TrackLifecycleService
from app.services.track_service import TrackService

router = APIRouter()


@router.get("", response_model=list[TrackResponse])
def list_tracks(db: Session = Depends(get_db)) -> list[TrackResponse]:
    return TrackService(db).list_tracks()


@router.post("/delete-failed", response_model=TrackDeleteResponse)
def delete_all_failed_tracks(db: Session = Depends(get_db)) -> TrackDeleteResponse:
    count = TrackLifecycleService(db).delete_all_failed_tracks()
    if count == 0:
        return TrackDeleteResponse(
            status="ok",
            message="No failed tracks to delete",
            deleted_count=0,
        )
    return TrackDeleteResponse(
        status="ok",
        message=f"Removed {count} failed track(s)",
        deleted_count=count,
    )


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


@router.delete("/{track_id}", response_model=TrackDeleteResponse)
def delete_failed_track(track_id: int, db: Session = Depends(get_db)) -> TrackDeleteResponse:
    try:
        TrackLifecycleService(db).delete_failed_track(track_id)
    except TrackLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrackDeleteResponse(status="ok", message="Failed track removed")


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
