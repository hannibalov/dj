from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.analyzer import analyze_audio
from app.logging import get_logger
from app.models.enums import JobStatus, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.utils.job_payload import job_payload
from app.utils.workspace_files import move_into_destination

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

        payload = job_payload(job)
        if payload.get("reprocess") or payload.get("reroute"):
            self._prepare_processing_from_final(track)

        audio_path = self._resolve_audio_path(track)
        if audio_path is None:
            job.status = JobStatus.FAILED
            job.error_message = "Processing file missing"
            track.status = TrackStatus.FAILED
            self._db.commit()
            return

        if self._already_analyzed(track):
            job.status = JobStatus.COMPLETED
            self._db.commit()
            self._enqueue_after_analyze(job, track)
            logger.info("analyze_skipped_already_done", source=job.source_path)
            return

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
        self._enqueue_after_analyze(job, track)

    def _enqueue_after_analyze(self, job: Job, track: Track) -> None:
        payload = job_payload(job)
        if payload.get("reprocess") or payload.get("reroute"):
            self._enqueue_reprocess_chain(job.source_path)
        else:
            QueueService(self._db).enqueue_fingerprint(job.source_path)

    def _enqueue_reprocess_chain(self, source_path: str) -> None:
        queue = QueueService(self._db)
        result = queue.enqueue_fingerprint(source_path, force=True)
        if not result.enqueued:
            queue.enqueue_tag(source_path, force=True)

    def _prepare_processing_from_final(self, track: Track) -> None:
        """Move the library copy back to processing so analysis and routing can re-run."""
        if not track.final_path:
            return
        final = Path(track.final_path)
        if not final.is_file():
            return

        settings = SettingsService(self._db).get_all()
        processing_root = Path(settings.processing_folder)
        processing_root.mkdir(parents=True, exist_ok=True)
        dest = processing_root / final.name

        processing = Path(track.processing_path) if track.processing_path else None
        if processing and processing.is_file() and processing.resolve() == final.resolve():
            track.final_path = None
            track.status = TrackStatus.INGESTED
            self._db.commit()
            return

        if processing and processing.is_file() and processing.resolve() != final.resolve():
            processing.unlink()

        if dest.exists() and dest.resolve() != final.resolve():
            dest = processing_root / f"{final.stem}_{track.id}{final.suffix}"

        if final.resolve() != dest.resolve():
            dest = move_into_destination(final, dest)

        track.processing_path = str(dest)
        track.final_path = None
        track.status = TrackStatus.INGESTED
        self._db.commit()

    def _resolve_audio_path(self, track: Track) -> Path | None:
        if track.processing_path:
            path = Path(track.processing_path)
            if path.is_file():
                return path
        if track.final_path:
            path = Path(track.final_path)
            if path.is_file():
                return path
        return None

    @staticmethod
    def _already_analyzed(track: Track) -> bool:
        return track.integrated_lufs is not None

    def _get_track(self, source_path: str) -> Track | None:
        return self._db.execute(
            select(Track).where(Track.source_path == source_path)
        ).scalar_one_or_none()
