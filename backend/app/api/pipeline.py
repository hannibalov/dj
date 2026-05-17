from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pipeline import PipelineSnapshot
from app.services.pipeline_service import PipelineService

router = APIRouter()


@router.get("/status", response_model=PipelineSnapshot)
def get_pipeline_status(db: Session = Depends(get_db)) -> PipelineSnapshot:
    return PipelineService(db).get_snapshot()
