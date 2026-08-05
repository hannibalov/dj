from collections.abc import Generator
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    parsed = urlparse(database_url)
    if parsed.path in ("", ":memory:"):
        return
    db_path = Path(unquote(parsed.path))
    if db_path.name:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def init_engine(database_url: str) -> None:
    global _engine, _SessionLocal
    _ensure_sqlite_parent_dir(database_url)
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    _engine = create_engine(database_url, connect_args=connect_args)

    if is_sqlite:

        @event.listens_for(_engine, "connect")
        def _sqlite_pragmas(dbapi_conn: Any, connection_record: object) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine not initialized")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        raise RuntimeError("Database session factory not initialized")
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    from app.db.migrate import run_migrations

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
