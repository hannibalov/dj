from pathlib import Path

from app.metadata.tags import parse_filename_metadata


def test_parse_filename_metadata_strips_library_mix_suffix(tmp_path: Path) -> None:
    path = tmp_path / "Wonderwall - Oaisis (Original Mix).mp3"
    path.write_bytes(b"fake")
    parsed = parse_filename_metadata(path, known_artists=frozenset({"Oasis"}))
    assert parsed.artist == "Oasis"
    assert parsed.title == "Wonderwall"
