from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.duplicate import (
    DuplicateGroupResponse,
    DuplicateResolveRequest,
    DuplicateResolveResponse,
)
from app.services.duplicate_resolve_service import DuplicateResolveError, DuplicateResolveService
from app.services.duplicate_service import DuplicateService

router = APIRouter()


@router.get("", response_model=list[DuplicateGroupResponse])
def list_duplicates(db: Session = Depends(get_db)) -> list[DuplicateGroupResponse]:
    return DuplicateService(db).list_groups()


@router.post("/resolve", response_model=DuplicateResolveResponse)
def resolve_duplicate(
    body: DuplicateResolveRequest,
    db: Session = Depends(get_db),
) -> DuplicateResolveResponse:
    try:
        return DuplicateResolveService(db).resolve(body)
    except DuplicateResolveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
