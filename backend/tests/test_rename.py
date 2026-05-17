from app.metadata.rename import (
    build_library_filename,
    extract_mix_from_title,
    sanitize_filename_part,
)


def test_sanitize_removes_unsafe_characters() -> None:
    assert sanitize_filename_part('AC/DC: "Highway"') == "ACDC Highway"


def test_sanitize_empty_becomes_unknown() -> None:
    assert sanitize_filename_part("///") == "Unknown"


def test_extract_mix_from_title() -> None:
    title, mix = extract_mix_from_title("Cola (Club Mix)")
    assert title == "Cola"
    assert mix == "Club Mix"


def test_build_library_filename_default_template() -> None:
    name = build_library_filename(
        artist="Eric Prydz",
        title="Generate",
        extension=".flac",
    )
    assert name == "Generate - Eric Prydz (Original Mix).flac"


def test_extract_mix_ignores_official_music_video() -> None:
    title, mix = extract_mix_from_title("The Space In Between (Official Music Video)")
    assert title == "The Space In Between (Official Music Video)"
    assert mix is None


def test_build_library_filename_uses_existing_mix_in_title() -> None:
    name = build_library_filename(
        artist="CamelPhat",
        title="Cola (Club Mix)",
        extension=".mp3",
    )
    assert name == "Cola - CamelPhat (Club Mix).mp3"
