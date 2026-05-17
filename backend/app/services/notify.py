"""Notify the API process so WebSocket clients receive pipeline updates."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.logging import get_logger

logger = get_logger("API")


def notify_pipeline_changed(message: str) -> None:
    settings = get_settings()
    url = f"{settings.api_internal_url.rstrip('/')}/internal/pipeline-notify"
    try:
        response = httpx.post(
            url,
            json={"message": message},
            timeout=2.0,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("pipeline_notify_failed", url=url, error=str(exc))
