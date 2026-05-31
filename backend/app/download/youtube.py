"""Download YouTube audio as MP3 via yt-dlp."""

import re
import shutil
import subprocess
from pathlib import Path

# Best available YouTube audio, then transcode for the DJ library pipeline.
_YOUTUBE_BEST_AUDIO_FORMAT = "bestaudio/best"
_MP3_TARGET_BITRATE = "320K"
_OUTPUT_SAMPLE_RATE_HZ = 44100
# Club-oriented loudness: hot masters around -9 LUFS with tight dynamics.
_LOUDNORM_TARGET_LUFS = -9.0
_LOUDNORM_TRUE_PEAK = -0.5
_LOUDNORM_LRA = 7.0

_YOUTUBE_HOST = re.compile(
    r"^https?://(?:"
    r"(?:www\.|m\.|music\.)?youtube\.com/"
    r"|youtu\.be/"
    r")",
    re.IGNORECASE,
)


class YouTubeDownloadError(Exception):
    pass


def is_youtube_url(url: str) -> bool:
    cleaned = url.strip()
    if not cleaned:
        return False
    return bool(_YOUTUBE_HOST.match(cleaned))


def ffmpeg_postprocessor_args() -> str:
    """ffmpeg flags for club-style loudness normalization and DJ-friendly sample rate."""
    loudnorm = (
        f"loudnorm=I={_LOUDNORM_TARGET_LUFS:.1f}:"
        f"TP={_LOUDNORM_TRUE_PEAK:.1f}:"
        f"LRA={_LOUDNORM_LRA:.0f}"
    )
    return f"-af {loudnorm} -ar {_OUTPUT_SAMPLE_RATE_HZ}"


def build_youtube_download_command(url: str, output_dir: Path) -> list[str]:
    """Build yt-dlp argv for a single YouTube video → normalized 320k MP3."""
    output_template = str(output_dir / "%(artist,channel,uploader)s - %(title)s.%(ext)s")
    return [
        "yt-dlp",
        "--no-playlist",
        "-f",
        _YOUTUBE_BEST_AUDIO_FORMAT,
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        _MP3_TARGET_BITRATE,
        "--embed-metadata",
        "--embed-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--parse-metadata",
        "artist:%(artist,uploader,channel,creator)s",
        "--parse-metadata",
        "title:%(title)s",
        "--postprocessor-args",
        f"ffmpeg:{ffmpeg_postprocessor_args()}",
        "--restrict-filenames",
        "-o",
        output_template,
        "--print",
        "after_move:filepath",
        url.strip(),
    ]


def download_youtube_audio(
    url: str,
    output_dir: Path,
    *,
    timeout_seconds: int = 600,
) -> Path:
    """Download a single YouTube video as MP3 into output_dir.

    Returns the path to the downloaded file.
    """
    if not is_youtube_url(url):
        raise YouTubeDownloadError("Not a supported YouTube URL")

    if shutil.which("yt-dlp") is None:
        raise YouTubeDownloadError("yt-dlp not found on PATH")

    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_youtube_download_command(url, output_dir)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise YouTubeDownloadError(f"yt-dlp failed: {exc}") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        detail = stderr or stdout or f"exit code {proc.returncode}"
        raise YouTubeDownloadError(detail)

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise YouTubeDownloadError("yt-dlp did not report an output file")

    output_path = Path(lines[-1])
    if not output_path.is_file():
        raise YouTubeDownloadError(f"Downloaded file missing: {output_path}")

    return output_path
