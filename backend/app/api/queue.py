from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.ws import broadcast_snapshot
from app.db.session import get_db
from app.schemas.queue import AnalyzeBacklogResponse, QueueResponse, RescanResponse
from app.services.queue_service import QueueService

router = APIRouter()


@router.get("", response_model=QueueResponse)
def get_queue(db: Session = Depends(get_db)) -> QueueResponse:
    return QueueService(db).get_queue_summary()


@router.post("/rescan", response_model=RescanResponse)
async def rescan_queue(db: Session = Depends(get_db)) -> RescanResponse:
    result = QueueService(db).enqueue_watch_folder_scan()
    await broadcast_snapshot(
        f"Rescan finished: {result.enqueued} enqueued, {result.skipped} skipped"
    )
    return result


@router.post("/analyze-backlog", response_model=AnalyzeBacklogResponse)
async def analyze_backlog(db: Session = Depends(get_db)) -> AnalyzeBacklogResponse:
    result = QueueService(db).enqueue_pending_analysis()
    await broadcast_snapshot(
        f"Analyze backlog: {result.enqueued} enqueued, {result.skipped} skipped"
    )
    return AnalyzeBacklogResponse(
        status=result.status,
        enqueued=result.enqueued,
        skipped=result.skipped,
    )
