import time
from pathlib import Path


class FileStabilityChecker:
    """Wait until a file's size and mtime stop changing (sync complete)."""

    def __init__(self, poll_seconds: float, required_stable_seconds: float) -> None:
        self._poll_seconds = poll_seconds
        self._required_stable_seconds = required_stable_seconds

    def wait_until_stable(self, path: Path) -> bool:
        if not path.exists() or not path.is_file():
            return False

        stable_since: float | None = None
        last_sig: tuple[int, float] | None = None

        while True:
            if not path.exists():
                return False
            stat = path.stat()
            sig = (stat.st_size, stat.st_mtime)
            now = time.monotonic()

            if last_sig == sig:
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= self._required_stable_seconds:
                    return True
            else:
                stable_since = None
                last_sig = sig

            time.sleep(self._poll_seconds)
