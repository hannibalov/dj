import threading
import time
from pathlib import Path

from app.services.stability import FileStabilityChecker


def test_wait_until_stable_detects_unchanged_file(tmp_path: Path) -> None:
    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"fake-audio")
    checker = FileStabilityChecker(poll_seconds=0.1, required_stable_seconds=0.3)
    assert checker.wait_until_stable(audio) is True


def test_wait_until_stable_fails_for_missing_file(tmp_path: Path) -> None:
    checker = FileStabilityChecker(poll_seconds=0.1, required_stable_seconds=0.2)
    assert checker.wait_until_stable(tmp_path / "missing.mp3") is False


def test_wait_until_stable_waits_for_changes(tmp_path: Path) -> None:
    audio = tmp_path / "growing.mp3"
    audio.write_bytes(b"a")
    checker = FileStabilityChecker(poll_seconds=0.1, required_stable_seconds=0.5)

    def grow_file() -> None:
        time.sleep(0.15)
        audio.write_bytes(b"abcdef")

    thread = threading.Thread(target=grow_file)
    thread.start()
    result = checker.wait_until_stable(audio)
    thread.join()
    assert result is True
