from pathlib import Path

from app.config import get_settings


def ensure_runtime_folders() -> list[Path]:
    settings = get_settings()
    folders = [
        settings.watch_folder,
        settings.incoming_folder,
        settings.processing_folder,
        settings.ready_folder,
        settings.review_folder,
        settings.duplicates_folder,
        settings.archive_folder,
        settings.failed_folder,
        settings.logs_folder,
        settings.rekordbox_export_folder,
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    return folders
