import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType, TrackStatus
from app.models.fingerprint import Fingerprint
from app.models.job import Job
from app.models.track import Track
from app.schemas.queue import JobResponse, QueueResponse, RescanResponse
from app.services.settings_service import SettingsService
from app.utils.audio_extensions import is_audio_file

ACTIVE_JOB_STATUSES = (JobStatus.PENDING, JobStatus.RUNNING)
SKIP_ALREADY_INGESTED = "already_ingested"
SKIP_ALREADY_QUEUED = "already_queued"
SKIP_ALREADY_ANALYZED = "already_analyzed"
SKIP_ALREADY_ROUTED = "already_routed"
SKIP_ALREADY_FINGERPRINTED = "already_fingerprinted"
SKIP_ALREADY_TAGGED = "already_tagged"


@dataclass
class EnqueueResult:
    job: Job | None
    enqueued: bool
    skip_reason: str | None = None


class QueueService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def skip_reason_for_ingest(self, source_path: str) -> str | None:
        active_job = self._db.execute(
            select(Job).where(
                Job.source_path == source_path,
                Job.job_type == JobType.INGEST,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        ).scalar_one_or_none()
        if active_job is not None:
            return SKIP_ALREADY_QUEUED

        track = self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()
        if track is None:
            return None

        if track.status == TrackStatus.FAILED:
            return None

        if track.processing_path:
            processing_file = Path(track.processing_path)
            if processing_file.is_file():
                return SKIP_ALREADY_INGESTED

        if track.status in (
            TrackStatus.INGESTED,
            TrackStatus.READY,
            TrackStatus.REVIEW,
            TrackStatus.DUPLICATE,
            TrackStatus.ARCHIVED,
        ):
            return SKIP_ALREADY_INGESTED

        return None

    def enqueue_ingest(self, source_path: str) -> EnqueueResult:
        skip = self.skip_reason_for_ingest(source_path)
        if skip:
            return EnqueueResult(job=None, enqueued=False, skip_reason=skip)

        job = Job(job_type=JobType.INGEST, status=JobStatus.PENDING, source_path=source_path)
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return EnqueueResult(job=job, enqueued=True)

    def skip_reason_for_download(self, url: str) -> str | None:
        active_job = self._db.execute(
            select(Job).where(
                Job.source_path == url,
                Job.job_type == JobType.DOWNLOAD,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        ).scalar_one_or_none()
        if active_job is not None:
            return SKIP_ALREADY_QUEUED
        return None

    def enqueue_download(self, url: str) -> EnqueueResult:
        skip = self.skip_reason_for_download(url)
        if skip:
            return EnqueueResult(job=None, enqueued=False, skip_reason=skip)

        job = Job(
            job_type=JobType.DOWNLOAD,
            status=JobStatus.PENDING,
            source_path=url,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return EnqueueResult(job=job, enqueued=True)

    def skip_reason_for_analyze(self, source_path: str, *, force: bool = False) -> str | None:
        active_job = self._db.execute(
            select(Job).where(
                Job.source_path == source_path,
                Job.job_type == JobType.ANALYZE,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        ).scalar_one_or_none()
        if active_job is not None:
            return SKIP_ALREADY_QUEUED

        track = self._get_track(source_path)
        if track is None:
            return None
        if force:
            return None
        if track.integrated_lufs is not None:
            return SKIP_ALREADY_ANALYZED
        if track.status in (TrackStatus.READY, TrackStatus.REVIEW, TrackStatus.DUPLICATE):
            return SKIP_ALREADY_ROUTED
        return None

    def enqueue_analyze(
        self,
        source_path: str,
        *,
        force: bool = False,
        payload: dict[str, object] | None = None,
    ) -> EnqueueResult:
        skip = self.skip_reason_for_analyze(source_path, force=force)
        if skip:
            return EnqueueResult(job=None, enqueued=False, skip_reason=skip)

        job = Job(
            job_type=JobType.ANALYZE,
            status=JobStatus.PENDING,
            source_path=source_path,
            payload=json.dumps(payload) if payload else None,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return EnqueueResult(job=job, enqueued=True)

    def skip_reason_for_fingerprint(self, source_path: str, *, force: bool = False) -> str | None:
        active_job = self._db.execute(
            select(Job).where(
                Job.source_path == source_path,
                Job.job_type == JobType.FINGERPRINT,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        ).scalar_one_or_none()
        if active_job is not None:
            return SKIP_ALREADY_QUEUED

        if force:
            return None

        track = self._get_track(source_path)
        if track is None:
            return None

        fp = self._db.execute(
            select(Fingerprint).where(Fingerprint.track_id == track.id)
        ).scalar_one_or_none()
        if fp is not None:
            return SKIP_ALREADY_FINGERPRINTED

        if (
            track.status == TrackStatus.DUPLICATE
            and track.final_path
            and Path(track.final_path).is_file()
        ):
            return SKIP_ALREADY_ROUTED

        if track.status in (TrackStatus.READY, TrackStatus.REVIEW):
            return SKIP_ALREADY_ROUTED
        return None

    def enqueue_fingerprint(self, source_path: str, *, force: bool = False) -> EnqueueResult:
        skip = self.skip_reason_for_fingerprint(source_path, force=force)
        if skip:
            return EnqueueResult(job=None, enqueued=False, skip_reason=skip)

        payload = {"reprocess": True} if force else None
        job = Job(
            job_type=JobType.FINGERPRINT,
            status=JobStatus.PENDING,
            source_path=source_path,
            payload=json.dumps(payload) if payload else None,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return EnqueueResult(job=job, enqueued=True)

    def skip_reason_for_route(self, source_path: str, *, force: bool = False) -> str | None:
        active_job = self._db.execute(
            select(Job).where(
                Job.source_path == source_path,
                Job.job_type == JobType.ROUTE,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        ).scalar_one_or_none()
        if active_job is not None:
            return SKIP_ALREADY_QUEUED

        if force:
            return None

        track = self._get_track(source_path)
        if track is None:
            return None
        if (
            track.status in (TrackStatus.READY, TrackStatus.REVIEW, TrackStatus.DUPLICATE)
            and track.final_path
            and Path(track.final_path).is_file()
        ):
            return SKIP_ALREADY_ROUTED
        return None

    def skip_reason_for_tag(self, source_path: str, *, force: bool = False) -> str | None:
        active_job = self._db.execute(
            select(Job).where(
                Job.source_path == source_path,
                Job.job_type == JobType.TAG,
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        ).scalar_one_or_none()
        if active_job is not None:
            return SKIP_ALREADY_QUEUED

        if force:
            return None

        track = self._get_track(source_path)
        if track is None:
            return None
        if track.tagged_at is not None:
            return SKIP_ALREADY_TAGGED

        if track.status == TrackStatus.DUPLICATE:
            return SKIP_ALREADY_ROUTED

        if track.status in (TrackStatus.READY, TrackStatus.REVIEW):
            return SKIP_ALREADY_ROUTED
        return None

    def enqueue_tag(self, source_path: str, *, force: bool = False) -> EnqueueResult:
        skip = self.skip_reason_for_tag(source_path, force=force)
        if skip:
            return EnqueueResult(job=None, enqueued=False, skip_reason=skip)

        payload = {"reprocess": True} if force else None
        job = Job(
            job_type=JobType.TAG,
            status=JobStatus.PENDING,
            source_path=source_path,
            payload=json.dumps(payload) if payload else None,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return EnqueueResult(job=job, enqueued=True)

    def enqueue_route(self, source_path: str, *, force: bool = False) -> EnqueueResult:
        skip = self.skip_reason_for_route(source_path, force=force)
        if skip:
            return EnqueueResult(job=None, enqueued=False, skip_reason=skip)

        job = Job(job_type=JobType.ROUTE, status=JobStatus.PENDING, source_path=source_path)
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return EnqueueResult(job=job, enqueued=True)

    def _get_track(self, source_path: str) -> Track | None:
        return self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()

    def get_queue_summary(self, limit: int = 200) -> QueueResponse:
        pending = self._count(JobStatus.PENDING)
        running = self._count(JobStatus.RUNNING)
        failed = self._count(JobStatus.FAILED)
        completed = self._count(JobStatus.COMPLETED)
        jobs = (
            self._db.execute(select(Job).order_by(Job.created_at.desc()).limit(limit))
            .scalars()
            .all()
        )
        return QueueResponse(
            pending=pending,
            running=running,
            failed=failed,
            completed=completed,
            jobs=[JobResponse.model_validate(j) for j in jobs],
        )

    def _count(self, status: JobStatus) -> int:
        stmt = select(func.count()).select_from(Job).where(Job.status == status)
        return self._db.scalar(stmt) or 0

    def count_pending(self) -> int:
        return self._count(JobStatus.PENDING)

    def clear_failed_jobs(self) -> int:
        jobs = self._db.execute(select(Job).where(Job.status == JobStatus.FAILED)).scalars().all()
        for job in jobs:
            self._db.delete(job)
        if jobs:
            self._db.commit()
        return len(jobs)

    def enqueue_watch_folder_scan(self) -> RescanResponse:
        settings = SettingsService(self._db).get_all()
        watch = Path(settings.watch_folder)
        if not watch.exists():
            return RescanResponse(status="ok", enqueued=0, skipped=0)

        enqueued = 0
        skipped = 0
        for path in watch.rglob("*"):
            if not path.is_file() or not is_audio_file(path):
                continue
            result = self.enqueue_ingest(str(path))
            if result.enqueued:
                enqueued += 1
            else:
                skipped += 1
        return RescanResponse(status="ok", enqueued=enqueued, skipped=skipped)

    def enqueue_pending_analysis(self) -> RescanResponse:
        """Enqueue ANALYZE for ingested tracks that have not been analyzed yet."""
        tracks = (
            self._db.execute(
                select(Track).where(
                    Track.status == TrackStatus.INGESTED,
                    Track.integrated_lufs.is_(None),
                )
            )
            .scalars()
            .all()
        )
        enqueued = 0
        skipped = 0
        for track in tracks:
            result = self.enqueue_analyze(track.source_path)
            if result.enqueued:
                enqueued += 1
            else:
                skipped += 1
        return RescanResponse(status="ok", enqueued=enqueued, skipped=skipped)

    def enqueue_reanalyze_all(self) -> RescanResponse:
        """Re-run analysis (and re-route) for tracks with a library or processing file."""
        tracks = self._db.execute(select(Track)).scalars().all()
        enqueued = 0
        skipped = 0
        for track in tracks:
            if track.status in (TrackStatus.DUPLICATE, TrackStatus.ARCHIVED):
                skipped += 1
                continue
            if not self._track_has_analyzable_audio(track):
                skipped += 1
                continue

            track.bpm = None
            track.bpm_confidence = None
            track.musical_key = None
            track.scale = None
            track.camelot = None
            track.key_confidence = None
            track.energy = None
            track.integrated_lufs = None
            track.true_peak_db = None
            track.artist = None
            track.title = None
            track.album = None
            track.genre = None
            track.subgenre = None
            track.mix_version = None
            track.musicbrainz_recording_id = None
            track.tag_confidence = None
            track.needs_metadata_review = False
            track.tagged_at = None
            track.status = TrackStatus.INGESTED
            self._repair_paths_before_reanalyze(track)

            self.cancel_active_jobs(track.source_path)
            result = self.enqueue_analyze(
                track.source_path,
                force=True,
                payload={"reprocess": True},
            )
            if result.enqueued:
                enqueued += 1
            else:
                skipped += 1
        self._db.commit()
        return RescanResponse(status="ok", enqueued=enqueued, skipped=skipped)

    @staticmethod
    def _repair_paths_before_reanalyze(track: Track) -> None:
        """Drop stale processing_path so analyze can use final_path or fail clearly."""
        if track.processing_path and not Path(track.processing_path).is_file():
            track.processing_path = None

    @staticmethod
    def _track_has_analyzable_audio(track: Track) -> bool:
        if track.processing_path and Path(track.processing_path).is_file():
            return True
        return bool(track.final_path and Path(track.final_path).is_file())

    def cancel_active_jobs(self, source_path: str) -> int:
        jobs = (
            self._db.execute(
                select(Job).where(
                    Job.source_path == source_path,
                    Job.status.in_(ACTIVE_JOB_STATUSES),
                )
            )
            .scalars()
            .all()
        )
        for job in jobs:
            job.status = JobStatus.CANCELLED
        if jobs:
            self._db.commit()
        return len(jobs)

    def reset_interrupted_jobs(self) -> int:
        """Return RUNNING jobs to PENDING (e.g. after worker crash or container restart)."""
        jobs = self._db.execute(select(Job).where(Job.status == JobStatus.RUNNING)).scalars().all()
        for job in jobs:
            job.status = JobStatus.PENDING
        if jobs:
            self._db.commit()
        return len(jobs)

    def claim_next_pending(self) -> Job | None:
        job = (
            self._db.execute(
                select(Job)
                .where(Job.status == JobStatus.PENDING)
                .order_by(Job.created_at.asc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if job is None:
            return None
        job.status = JobStatus.RUNNING
        self._db.commit()
        self._db.refresh(job)
        return job
