"""Periodic maintenance tasks: automatic metadata sanity audits."""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_session_factory, init_engine
from app.logging import configure_logging, get_logger

logger = get_logger("API")

_POLL_INTERVAL_SECONDS = 30


def run_scheduled_check(
    db: Session,
    *,
    last_run: datetime | None,
    now: datetime,
    interval_minutes: float,
) -> datetime | None:
    """Run the metadata sanity check if enough time has passed.

    Returns the new last-run timestamp, or the unchanged one when it's not time yet.
    """
    if last_run is not None and (now - last_run) < timedelta(minutes=interval_minutes):
        return last_run

    from app.services.metadata_sanity_service import MetadataSanityService

    MetadataSanityService(db).run_check()
    return now


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    logger.info("scheduler_started")

    last_run: datetime | None = None
    while True:
        db = get_session_factory()()
        try:
            last_run = run_scheduled_check(
                db,
                last_run=last_run,
                now=datetime.now(UTC),
                interval_minutes=settings.metadata_sanity_interval_minutes,
            )
        finally:
            db.close()
        logger.debug("scheduler_tick")
        time.sleep(_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
