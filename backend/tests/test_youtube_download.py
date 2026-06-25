from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.download.linear_gain import LinearGainResult
from app.download.youtube import (
    YouTubeDownloadError,
    build_youtube_download_command,
    download_youtube_audio,
    ffmpeg_postprocessor_args,
    is_youtube_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/shorts/dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=abc123",
    ],
)
def test_is_youtube_url_accepts_valid_urls(url: str) -> None:
    assert is_youtube_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://example.com/watch?v=abc",
        "https://vimeo.com/123",
        "not-a-url",
    ],
)
def test_is_youtube_url_rejects_invalid_urls(url: str) -> None:
    assert not is_youtube_url(url)


def test_ffmpeg_postprocessor_args_transcode_only_no_loudnorm() -> None:
    args = ffmpeg_postprocessor_args()
    assert "-ar 44100" in args
    assert "libmp3lame" in args
    assert "320k" in args
    assert "loudnorm" not in args


def test_build_youtube_download_command_quality_options(tmp_path: Path) -> None:
    url = "https://www.youtube.com/watch?v=abc123"
    cmd = build_youtube_download_command(url, tmp_path)

    assert cmd[0] == "yt-dlp"
    assert "bestaudio/best" in cmd
    assert "320K" in cmd
    assert "--embed-thumbnail" in cmd
    assert "--embed-metadata" in cmd
    assert not any("loudnorm" in part for part in cmd)
    assert url in cmd


def test_download_youtube_audio_missing_binary(tmp_path: Path) -> None:
    with (
        patch("app.download.youtube.shutil.which", return_value=None),
        pytest.raises(YouTubeDownloadError, match="yt-dlp not found"),
    ):
        download_youtube_audio("https://www.youtube.com/watch?v=abc", tmp_path)


def test_download_youtube_audio_applies_linear_gain(tmp_path: Path) -> None:
    output = tmp_path / "Artist - Track.mp3"
    output.write_bytes(b"mp3")

    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = f"{output}\n"
    proc.stderr = ""

    gain_result = LinearGainResult(
        gain_db=6.0,
        measured_lufs=-15.0,
        measured_peak_db=-2.0,
        applied=True,
    )

    with (
        patch("app.download.youtube.shutil.which", return_value="/usr/bin/yt-dlp"),
        patch("app.download.youtube.subprocess.run", return_value=proc),
        patch("app.download.youtube.apply_linear_gain", return_value=gain_result) as gain,
    ):
        result = download_youtube_audio(
            "https://www.youtube.com/watch?v=abc123",
            tmp_path,
        )

    assert result == output
    gain.assert_called_once_with(output, timeout_seconds=600)


def test_download_youtube_audio_reports_ytdlp_error(tmp_path: Path) -> None:
    proc = MagicMock()
    proc.returncode = 1
    proc.stdout = ""
    proc.stderr = "Video unavailable"

    with (
        patch("app.download.youtube.shutil.which", return_value="/usr/bin/yt-dlp"),
        patch("app.download.youtube.subprocess.run", return_value=proc),
        pytest.raises(YouTubeDownloadError, match="Video unavailable"),
    ):
        download_youtube_audio("https://www.youtube.com/watch?v=abc123", tmp_path)
