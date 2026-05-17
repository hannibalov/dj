from pathlib import Path

from app.utils.workspace_files import clear_stale_processing_copy, move_into_destination


def test_move_into_destination_removes_source(tmp_path: Path) -> None:
    source = tmp_path / "processing" / "song.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"audio")
    dest = tmp_path / "ready" / "song.mp3"

    move_into_destination(source, dest)

    assert dest.is_file()
    assert not source.exists()


def test_clear_stale_processing_copy_deletes_extra_copy(tmp_path: Path) -> None:
    processing = tmp_path / "processing" / "song.mp3"
    ready = tmp_path / "ready" / "song.mp3"
    processing.parent.mkdir(parents=True)
    ready.parent.mkdir(parents=True)
    processing.write_bytes(b"processing")
    ready.write_bytes(b"ready")

    updated = clear_stale_processing_copy(
        processing_path=str(processing),
        final_path=str(ready),
    )

    assert updated is None
    assert not processing.exists()
    assert ready.is_file()
