"""Download YouTube audio as MP3 via yt-dlp."""

import re
import shutil
import subprocess
import time
from pathlib import Path

from app.download.linear_gain import LinearGainError, apply_linear_gain
from app.logging import get_logger

logger = get_logger("ROUTER")

# Best available YouTube audio, then transcode for the DJ library pipeline.
_YOUTUBE_BEST_AUDIO_FORMAT = "bestaudio/best"
_MP3_TARGET_BITRATE = "320K"
_OUTPUT_SAMPLE_RATE_HZ = 44100

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
    """ffmpeg transcode flags for yt-dlp — no loudness filters (gain is applied later)."""
    return f"-ar {_OUTPUT_SAMPLE_RATE_HZ} -c:a libmp3lame -b:a {_MP3_TARGET_BITRATE.lower()}"


def build_youtube_download_command(url: str, output_dir: Path) -> list[str]:
    """Build yt-dlp argv for a single YouTube video → 320k MP3 in watch folder."""
    output_template = str(output_dir / "%(artist,channel,uploader)s - %(title)s.%(ext)s")
    cmd: list[str] = [
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

    if shutil.which("node"):
        # Enable Node.js runtime and allow fetching yt-dlp EJS remote components
        # (needed for signature/challenge solvers on some YouTube pages).
        cmd[1:1] = ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    elif shutil.which("deno"):
        # Deno support may also require remote components to be allowed.
        cmd[1:1] = ["--js-runtimes", "deno", "--remote-components", "ejs:github"]

    return cmd


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
    base_cmd = build_youtube_download_command(url, output_dir)

    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise YouTubeDownloadError(f"yt-dlp failed: {exc}") from exc

    # Attempt sequence: original → UA/Referer/geo-bypass → combined EJS+UA
    attempts = []
    # 0: original
    attempts.append((base_cmd, "original"))

    # 1: UA + Referer + geo-bypass
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    )
    attempts.append((base_cmd + ["--user-agent", ua, "--add-header", "Referer: https://www.youtube.com/", "--geo-bypass"], "ua_referer"))

    # 2: combined - ensure remote components are allowed and include UA/Referer
    combined_cmd = list(base_cmd)
    # If Node/Deno present, add explicit runtimes + remote components
    if shutil.which("node"):
        combined_cmd[1:1] = ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    elif shutil.which("deno"):
        combined_cmd[1:1] = ["--js-runtimes", "deno", "--remote-components", "ejs:github"]
    else:
        # Add remote-components hint even if runtime not detected — yt-dlp will skip if unavailable.
        combined_cmd[1:1] = ["--remote-components", "ejs:github,ejs:npm"]

    combined_cmd += ["--user-agent", ua, "--add-header", "Referer: https://www.youtube.com/", "--geo-bypass"]
    attempts.append((combined_cmd, "combined_ejs_ua"))

    last_detail = None
    proc = None
    for idx, (cmd, label) in enumerate(attempts, start=1):
        logger.info("youtube_download_attempt", url=url, attempt=idx, label=label)
        proc = _run(cmd)
        if proc.returncode == 0:
            break

        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        last_detail = stderr or stdout or f"exit code {proc.returncode}"

        # Quick backoff between attempts
        if idx < len(attempts):
            time.sleep(1)

    if proc is None or proc.returncode != 0:
        # Surface best available output for diagnostics
        raise YouTubeDownloadError(last_detail or "yt-dlp failed")

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise YouTubeDownloadError("yt-dlp did not report an output file")

    output_path = Path(lines[-1])
    if not output_path.is_file():
        raise YouTubeDownloadError(f"Downloaded file missing: {output_path}")

    try:
        gain_result = apply_linear_gain(output_path, timeout_seconds=timeout_seconds)
    except LinearGainError as exc:
        raise YouTubeDownloadError(f"Linear gain failed: {exc}") from exc

    logger.info(
        "youtube_download_gain",
        path=str(output_path),
        gain_db=gain_result.gain_db,
        applied=gain_result.applied,
        measured_lufs=gain_result.measured_lufs,
    )

    return output_path
