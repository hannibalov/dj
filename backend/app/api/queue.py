from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.ws import broadcast_snapshot
from app.db.session import get_db
from app.schemas.queue import (
    AnalyzeBacklogResponse,
    ClearFailedJobsResponse,
    GenreBackfillResponse,
    LibrarySyncResponse,
    QueueResponse,
    RescanResponse,
)
from app.services.genre_backfill_service import GenreBackfillService
from app.services.library_sync_service import LibrarySyncService
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


@router.post("/unstick", response_model=RescanResponse)
async def unstick_queue(db: Session = Depends(get_db)) -> RescanResponse:
    """Reset jobs stuck in `running` (e.g. after worker crash) back to `pending`."""
    count = QueueService(db).reset_interrupted_jobs()
    await broadcast_snapshot(
        f"Unstick: reset {count} interrupted job(s) to pending"
        if count
        else "Unstick: no interrupted jobs"
    )
    return RescanResponse(status="ok", enqueued=count, skipped=0)


@router.post("/clear-failed-jobs", response_model=ClearFailedJobsResponse)
async def clear_failed_jobs(db: Session = Depends(get_db)) -> ClearFailedJobsResponse:
    count = QueueService(db).clear_failed_jobs()
    message = (
        f"Removed {count} failed job(s) from history"
        if count
        else "No failed jobs to clear"
    )
    await broadcast_snapshot(message)
    return ClearFailedJobsResponse(status="ok", deleted_count=count, message=message)


@router.post("/reanalyze-all", response_model=AnalyzeBacklogResponse)
async def reanalyze_all(db: Session = Depends(get_db)) -> AnalyzeBacklogResponse:
    result = QueueService(db).enqueue_reanalyze_all()
    await broadcast_snapshot(
        f"Reanalyze all: {result.enqueued} enqueued, {result.skipped} skipped"
    )
    return AnalyzeBacklogResponse(
        status=result.status,
        enqueued=result.enqueued,
        skipped=result.skipped,
    )


@router.post("/genre-backfill", response_model=GenreBackfillResponse)
async def genre_backfill(db: Session = Depends(get_db)) -> GenreBackfillResponse:
    result = GenreBackfillService(db).backfill_missing_genres()
    await broadcast_snapshot(
        f"Genre backfill: enriched {result.enriched}, skipped {result.skipped}"
    )
    return GenreBackfillResponse(
        status=result.status,
        enriched=result.enriched,
        skipped=result.skipped,
    )


@router.post("/library-sync", response_model=LibrarySyncResponse)
async def library_sync(db: Session = Depends(get_db)) -> LibrarySyncResponse:
    result = LibrarySyncService(db).sync_library()
    await broadcast_snapshot(
        "Library sync: "
        f"{result.enqueued} enqueued, {result.paths_repaired} paths repaired, "
        f"{result.metadata_updated} metadata updated, "
        f"{result.missing_files} missing, {result.orphan_files} orphan files"
    )
    return LibrarySyncResponse(
        status=result.status,
        enqueued=result.enqueued,
        skipped=result.skipped,
        paths_repaired=result.paths_repaired,
        metadata_updated=result.metadata_updated,
        missing_files=result.missing_files,
        orphan_files=result.orphan_files,
    )
