from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.duplicate import (
    DuplicateGroupResponse,
    DuplicateResolveRequest,
    DuplicateResolveResponse,
)
from app.schemas.song_duplicate import (
    SongDuplicateGroupResponse,
    SongDuplicateResolveRequest,
    SongDuplicateResolveResponse,
)
from app.services.duplicate_resolve_service import DuplicateResolveError, DuplicateResolveService
from app.services.duplicate_service import DuplicateService
from app.services.song_duplicate_resolve_service import (
    SongDuplicateResolveError,
    SongDuplicateResolveService,
)
from app.services.song_duplicate_service import SongDuplicateService

router = APIRouter()


@router.get("", response_model=list[DuplicateGroupResponse])
def list_duplicates(db: Session = Depends(get_db)) -> list[DuplicateGroupResponse]:
    return DuplicateService(db).list_groups()


@router.get("/songs", response_model=list[SongDuplicateGroupResponse])
def list_song_duplicates(db: Session = Depends(get_db)) -> list[SongDuplicateGroupResponse]:
    return SongDuplicateService(db).list_groups()


@router.post("/resolve", response_model=DuplicateResolveResponse)
def resolve_duplicate(
    body: DuplicateResolveRequest,
    db: Session = Depends(get_db),
) -> DuplicateResolveResponse:
    try:
        return DuplicateResolveService(db).resolve(body)
    except DuplicateResolveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/songs/resolve", response_model=SongDuplicateResolveResponse)
def resolve_song_duplicate(
    body: SongDuplicateResolveRequest,
    db: Session = Depends(get_db),
) -> SongDuplicateResolveResponse:
    try:
        return SongDuplicateResolveService(db).resolve(body)
    except SongDuplicateResolveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
