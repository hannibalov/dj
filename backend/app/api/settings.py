from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SettingsResponse:
    return SettingsService(db).get_all()


@router.put("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
) -> SettingsResponse:
    return SettingsService(db).update(payload)
