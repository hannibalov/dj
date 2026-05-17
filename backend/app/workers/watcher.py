"""Filesystem watcher — enqueues jobs only; never processes in place."""

import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import get_settings
from app.db.session import get_session_factory, init_engine
from app.logging import configure_logging, get_logger
from app.services.notify import notify_pipeline_changed
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.utils.audio_extensions import is_audio_file

logger = get_logger("WATCHER")


class AudioFileHandler(FileSystemEventHandler):
    def _maybe_enqueue(self, src_path: str) -> None:
        path = Path(src_path)
        if not path.is_file() or not is_audio_file(path):
            return
        session_factory = get_session_factory()
        db = session_factory()
        try:
            result = QueueService(db).enqueue_ingest(src_path)
            if result.enqueued:
                logger.info("file_enqueued", path=src_path)
                notify_pipeline_changed(f"Queued for ingest: {path.name}")
            else:
                logger.debug("file_enqueue_skipped", path=src_path, reason=result.skip_reason)
        finally:
            db.close()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._maybe_enqueue(str(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._maybe_enqueue(str(event.src_path))


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)

    session_factory = get_session_factory()
    db = session_factory()
    try:
        folder_settings = SettingsService(db).get_all()
        watch_path = Path(folder_settings.watch_folder)
    finally:
        db.close()

    watch_path.mkdir(parents=True, exist_ok=True)
    handler = AudioFileHandler()
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=True)
    observer.start()
    logger.info("watcher_started", path=str(watch_path))

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
