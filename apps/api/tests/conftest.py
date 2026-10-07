import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import Base, get_session
from app.main import app
from app.models import User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# A separate database for tests; created fresh each session.
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/wyro_test"


@pytest.fixture(scope="session")
def _engine() -> Iterator:
    # Ensure the test database exists.
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.exec_driver_sql(
            "SELECT 1 FROM pg_database WHERE datname = 'wyro_test'"
        ).scalar()
        if not exists:
            conn.exec_driver_sql("CREATE DATABASE wyro_test")
    admin.dispose()

    engine = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(_engine) -> Iterator[Session]:
    connection = _engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection, expire_on_commit=False)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def dev_user(session) -> User:
    user = User(
        id=DEV_USER_ID,
        email="dev@wyro.app",
        auth_provider="dev",
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def client(session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
