"""WAV/AIFF use ID3 chunks; easy mutagen tags must not be used for writes."""

import struct
from pathlib import Path

from mutagen.wave import WAVE

from app.metadata.tags import read_tags, write_tags


def _minimal_wav(path: Path) -> None:
    data = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt " + struct.pack("<I", 16)
    data += struct.pack("<HHIIHH", 1, 1, 44100, 88200, 2, 16)
    data += b"data" + struct.pack("<I", 0)
    path.write_bytes(data)


def test_write_tags_wav_uses_id3_frames(tmp_path: Path) -> None:
    path = tmp_path / "deadmau5 - Strobe (Original Mix).wav"
    _minimal_wav(path)

    write_tags(path, artist="deadmau5", title="Strobe (Original Mix)")

    audio = WAVE(path)
    assert audio.tags is not None
    assert str(audio.tags["TPE1"]) == "deadmau5"
    assert str(audio.tags["TIT2"]) == "Strobe (Original Mix)"


def test_read_tags_wav_reads_id3_frames(tmp_path: Path) -> None:
    path = tmp_path / "track.wav"
    _minimal_wav(path)
    write_tags(path, artist="Modeselektor", title="Cash")

    tags = read_tags(path)
    assert tags.artist == "Modeselektor"
    assert tags.title == "Cash"


def test_write_tags_wav_replaces_not_frame_error(tmp_path: Path) -> None:
    path = tmp_path / "song.wav"
    _minimal_wav(path)
    write_tags(path, artist="A", title="B")
    write_tags(path, artist="C", title="D")

    tags = read_tags(path)
    assert tags.artist == "C"
    assert tags.title == "D"
