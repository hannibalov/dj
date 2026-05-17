from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.duplicate import DuplicateGroupResponse, DuplicateResolveResponse
from app.services.duplicate_service import DuplicateService

router = APIRouter()


@router.get("", response_model=list[DuplicateGroupResponse])
def list_duplicates(db: Session = Depends(get_db)) -> list[DuplicateGroupResponse]:
    return DuplicateService(db).list_groups()


@router.post("/resolve", response_model=DuplicateResolveResponse)
def resolve_duplicate() -> DuplicateResolveResponse:
    """Manual duplicate resolution ships in a later phase."""
    return DuplicateResolveResponse(status="not_implemented")
