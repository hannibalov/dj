"""Initialize database schema. Run: python -m app.db.init_db"""

import app.models  # noqa: F401 — register ORM models
from app.config import get_settings
from app.db.session import create_tables, init_engine
from app.logging import configure_logging, get_logger


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    create_tables()  # includes migrate_tracks_analysis_columns
    get_logger("API").info("database_initialized", url=settings.database_url)


if __name__ == "__main__":
    main()
