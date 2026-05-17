from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.analyzer import analyze_audio
from app.logging import get_logger
from app.models.enums import JobStatus, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.services.queue_service import QueueService

logger = get_logger("ANALYZER")


class AnalysisService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def process_analyze_job(self, job: Job) -> None:
        track = self._get_track(job.source_path)
        if track is None:
            job.status = JobStatus.FAILED
            job.error_message = f"No track for source: {job.source_path}"
            self._db.commit()
            return

        if not track.processing_path or not Path(track.processing_path).is_file():
            job.status = JobStatus.FAILED
            job.error_message = "Processing file missing"
            track.status = TrackStatus.FAILED
            self._db.commit()
            return

        if self._already_analyzed(track):
            job.status = JobStatus.COMPLETED
            self._db.commit()
            QueueService(self._db).enqueue_fingerprint(job.source_path)
            logger.info("analyze_skipped_already_done", source=job.source_path)
            return

        audio_path = Path(track.processing_path)
        track.status = TrackStatus.PROCESSING
        self._db.commit()

        try:
            result = analyze_audio(audio_path)
        except Exception as exc:
            track.status = TrackStatus.FAILED
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            self._db.commit()
            logger.error("analyze_failed", source=job.source_path, error=str(exc))
            return

        track.bpm = result.bpm
        track.bpm_confidence = result.bpm_confidence
        track.musical_key = result.musical_key
        track.scale = result.scale
        track.camelot = result.camelot
        track.key_confidence = result.key_confidence
        track.energy = result.energy
        track.integrated_lufs = result.integrated_lufs
        track.true_peak_db = result.true_peak_db
        track.status = TrackStatus.INGESTED
        job.status = JobStatus.COMPLETED
        self._db.commit()

        logger.info(
            "analyze_complete",
            source=job.source_path,
            bpm=result.bpm,
            lufs=result.integrated_lufs,
        )
        QueueService(self._db).enqueue_fingerprint(job.source_path)

    @staticmethod
    def _already_analyzed(track: Track) -> bool:
        return track.integrated_lufs is not None

    def _get_track(self, source_path: str) -> Track | None:
        return self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()
