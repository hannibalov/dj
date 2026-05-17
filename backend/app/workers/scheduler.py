"""Periodic maintenance tasks (retries, rescans). Phase 1: heartbeat only."""

import time

from app.config import get_settings
from app.db.session import init_engine
from app.logging import configure_logging, get_logger

logger = get_logger("API")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    logger.info("scheduler_started")
    while True:
        logger.debug("scheduler_tick")
        time.sleep(60)


if __name__ == "__main__":
    main()
