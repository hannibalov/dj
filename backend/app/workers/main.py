"""Process queued jobs: download → ingest → analyze → fingerprint → tag → route."""

import time
from pathlib import Path

from app.config import get_settings
from app.db.session import get_engine, get_session_factory, init_engine
from app.logging import configure_logging, get_logger
from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.services.analysis_service import AnalysisService
from app.services.download_service import DownloadService
from app.services.fingerprint_service import FingerprintService
from app.services.ingest import IngestService
from app.services.notify import notify_pipeline_changed
from app.services.queue_service import QueueService
from app.services.routing_service import RoutingService
from app.services.tag_service import TagService

logger = get_logger("ANALYZER")


def _basename(path: str) -> str:
    return Path(path).name


def _job_label(job: Job) -> str:
    if job.job_type == JobType.DOWNLOAD:
        url = job.source_path
        return url if len(url) <= 60 else f"{url[:57]}..."
    return _basename(job.source_path)


def _chain_after_ingest(queue: QueueService, job: Job) -> None:
    if job.status != JobStatus.COMPLETED:
        return
    result = queue.enqueue_analyze(job.source_path)
    if result.enqueued:
        logger.info("analyze_enqueued", source=job.source_path)


def _chain_after_download(queue: QueueService, job: Job, output_path: str) -> None:
    if job.status != JobStatus.COMPLETED:
        return
    result = queue.enqueue_ingest(output_path)
    if result.enqueued:
        logger.info("ingest_enqueued_after_download", source=output_path)


def run_once() -> bool:
    db = get_session_factory()()
    try:
        queue = QueueService(db)
        job = queue.claim_next_pending()
        if job is None:
            return False
        notify_pipeline_changed(f"Started {job.job_type.value}: {_job_label(job)}")
        try:
            if job.job_type == JobType.DOWNLOAD:
                output_path = DownloadService(db).process_download_job(job)
                db.refresh(job)
                if output_path:
                    _chain_after_download(queue, job, output_path)
                if job.status == JobStatus.COMPLETED:
                    notify_pipeline_changed(
                        f"YouTube download complete: {_basename(output_path or job.source_path)}"
                    )
                elif job.status == JobStatus.FAILED:
                    notify_pipeline_changed(
                        f"YouTube download failed: {_job_label(job)} — {job.error_message}"
                    )
            elif job.job_type == JobType.INGEST:
                IngestService(db).process_ingest_job(job)
                db.refresh(job)
                _chain_after_ingest(queue, job)
                if job.status == JobStatus.COMPLETED:
                    notify_pipeline_changed(f"Ingest complete: {_job_label(job)}")
                elif job.status == JobStatus.FAILED:
                    notify_pipeline_changed(
                        f"Ingest failed: {_job_label(job)} — {job.error_message}"
                    )
            elif job.job_type == JobType.ANALYZE:
                AnalysisService(db).process_analyze_job(job)
                db.refresh(job)
                if job.status == JobStatus.COMPLETED:
                    notify_pipeline_changed(f"Analysis complete: {_job_label(job)}")
                elif job.status == JobStatus.FAILED:
                    notify_pipeline_changed(
                        f"Analysis failed: {_job_label(job)} — {job.error_message}"
                    )
            elif job.job_type == JobType.FINGERPRINT:
                FingerprintService(db).process_fingerprint_job(job)
                db.refresh(job)
                if job.status == JobStatus.COMPLETED:
                    notify_pipeline_changed(f"Fingerprint complete: {_job_label(job)}")
                elif job.status == JobStatus.FAILED:
                    notify_pipeline_changed(
                        f"Fingerprint failed: {_job_label(job)} — {job.error_message}"
                    )
            elif job.job_type == JobType.TAG:
                TagService(db).process_tag_job(job)
                db.refresh(job)
                if job.status == JobStatus.COMPLETED:
                    notify_pipeline_changed(f"Tagged: {_job_label(job)}")
                elif job.status == JobStatus.FAILED:
                    notify_pipeline_changed(f"Tag failed: {_job_label(job)} — {job.error_message}")
            elif job.job_type == JobType.ROUTE:
                RoutingService(db).process_route_job(job)
                db.refresh(job)
                if job.status == JobStatus.COMPLETED:
                    notify_pipeline_changed(f"Routed: {_job_label(job)}")
                elif job.status == JobStatus.FAILED:
                    notify_pipeline_changed(
                        f"Route failed: {_job_label(job)} — {job.error_message}"
                    )
            else:
                job.status = JobStatus.FAILED
                job.error_message = f"Unsupported job type: {job.job_type}"
                db.commit()
                notify_pipeline_changed(f"Job failed: unsupported type {job.job_type}")
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.attempts += 1
            db.commit()
            logger.error("job_failed", job_id=job.id, error=str(exc))
            notify_pipeline_changed(f"Job failed: {_job_label(job)} — {exc}")
        else:
            pending = queue.count_pending()
            if pending == 0:
                notify_pipeline_changed("Worker idle")
            else:
                notify_pipeline_changed(f"Worker between jobs ({pending} still pending in queue)")
        return True
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    get_engine()
    db = get_session_factory()()
    try:
        reset_count = QueueService(db).reset_interrupted_jobs()
        if reset_count:
            logger.info("worker_reset_interrupted_jobs", count=reset_count)
    finally:
        db.close()
    logger.info("worker_started")
    while True:
        processed = run_once()
        if not processed:
            time.sleep(2)


if __name__ == "__main__":
    main()
