from pathlib import Path

from app.utils.workspace_files import remove_watch_source, restore_library_file_to_watch


def test_remove_watch_source_only_under_watch_root(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    source = watch / "song.mp3"
    source.write_bytes(b"x")
    outside = tmp_path / "other.mp3"
    outside.write_bytes(b"y")

    assert remove_watch_source(str(source), watch) is True
    assert not source.exists()
    assert remove_watch_source(str(outside), watch) is False
    assert outside.is_file()


def test_restore_library_file_to_watch(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    ready = tmp_path / "ready" / "Song - Artist (Original Mix).mp3"
    ready.parent.mkdir(parents=True)
    ready.write_bytes(b"ready")
    watch_target = watch / "Song - Artist.mp3"

    restore_library_file_to_watch(ready, watch_target, watch_folder=watch)

    assert watch_target.is_file()
    assert not ready.exists()
