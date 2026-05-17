from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db, init_engine
from app.main import create_app


@pytest.fixture
def db_engine() -> Engine:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    from app.db.migrate import run_migrations

    run_migrations(engine)
    return engine


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine: Engine, db_session: Session) -> Generator[TestClient, None, None]:
    init_engine("sqlite://")
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
