"""Move audio out of the processing workspace (no duplicate disk copies)."""

import shutil
from pathlib import Path


def move_into_destination(source: Path, dest: Path) -> Path:
    """
    Move source to dest, creating parent directories.

    The file must not already exist at dest unless it is the same path as source.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if source.resolve() == dest.resolve():
            return dest
        raise FileExistsError(dest)
    shutil.move(str(source), str(dest))
    return dest


def path_is_under_root(path: Path, root: Path) -> bool:
    """True when path is root or a descendant of root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def remove_watch_source(source_path: str, watch_folder: Path) -> bool:
    """Delete the watch-folder copy after the track is accepted into ready/."""
    source = Path(source_path)
    if not source.is_file():
        return False
    if not path_is_under_root(source, watch_folder):
        return False
    source.unlink()
    return True


def restore_library_file_to_watch(
    library_file: Path,
    watch_path: Path,
    *,
    watch_folder: Path,
) -> Path:
    """Move a ready/ review library copy back to the original watch path for reset."""
    if not path_is_under_root(watch_path, watch_folder):
        raise ValueError(f"Watch path must be under watch folder: {watch_path}")
    watch_path.parent.mkdir(parents=True, exist_ok=True)
    if watch_path.exists() and watch_path.resolve() != library_file.resolve():
        watch_path.unlink()
    if library_file.resolve() == watch_path.resolve():
        return watch_path
    return move_into_destination(library_file, watch_path)


def remove_workspace_file(path: Path | None) -> None:
    """Delete a workspace file if it exists (ignore missing)."""
    if path is None:
        return
    if path.is_file():
        path.unlink()


def clear_stale_processing_copy(
    *,
    processing_path: str | None,
    final_path: str | None,
) -> str | None:
    """
    Drop processing_path when final library file exists elsewhere.

    Returns updated processing_path (None if workspace copy was removed).
    """
    if not processing_path or not final_path:
        return processing_path
    processing = Path(processing_path)
    final = Path(final_path)
    if not processing.is_file():
        return None
    if processing.resolve() == final.resolve():
        return None
    remove_workspace_file(processing)
    return None
