from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.ws import broadcast_snapshot
from app.db.session import get_db
from app.schemas.download import YouTubeDownloadRequest, YouTubeDownloadResponse
from app.services.queue_service import QueueService

router = APIRouter()


@router.post("/youtube", response_model=YouTubeDownloadResponse)
async def download_youtube(
    body: YouTubeDownloadRequest,
    db: Session = Depends(get_db),
) -> YouTubeDownloadResponse:
    result = QueueService(db).enqueue_download(body.url)
    if result.enqueued and result.job is not None:
        message = "YouTube download queued — worker will ingest when complete"
        await broadcast_snapshot(message)
        return YouTubeDownloadResponse(
            status="ok",
            enqueued=True,
            job_id=result.job.id,
            message=message,
        )

    skip = result.skip_reason or "unknown"
    message = f"Download not queued ({skip})"
    await broadcast_snapshot(message)
    return YouTubeDownloadResponse(
        status="ok",
        enqueued=False,
        skip_reason=skip,
        message=message,
    )
