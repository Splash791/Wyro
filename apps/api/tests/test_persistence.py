"""Regression test for the "flush but never commit" bug.

The `client`/`session`/`dev_user` fixtures used by the rest of the suite all
share a single per-test transaction that is rolled back at teardown (see
conftest.py). That makes writes visible to the test via `flush`, but it can
never detect a production bug where `get_session` fails to `commit()` before
`close()` rolls back the transaction -- the rollback happens either way.

This test deliberately avoids those fixtures. It wires up a *committing*
session factory bound to the real test engine (mirroring the fixed
`app.db.get_session`), drives a request through a real TestClient, and then
opens a brand-new, independent `Session` to read the row back. If the
request handler only flushed (the bug), the row would not exist in a
different session/connection and the test would fail.
"""

import uuid
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session
from app.main import app
from app.models import Trip, User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTH = {"Authorization": "Bearer dev-token"}

TRIP_BODY = {
    "title": "Japan",
    "start_date": "2026-04-01",
    "end_date": "2026-04-03",
    "cities": [
        {
            "city": "Tokyo",
            "country_code": "JP",
            "time_zone": "Asia/Tokyo",
            "arrive_date": "2026-04-01",
            "leave_date": "2026-04-02",
        },
        {
            "city": "Kyoto",
            "country_code": "JP",
            "time_zone": "Asia/Tokyo",
            "arrive_date": "2026-04-02",
            "leave_date": "2026-04-03",
        },
    ],
}


def test_created_trip_is_actually_committed(_engine):
    """POST /trips must survive the request's session being closed.

    Uses the real wyro_test engine (via the `_engine` fixture) with a
    committing session factory -- i.e. the same commit-on-success,
    rollback-on-exception behavior as the fixed `app.db.get_session` -- so
    this exercises the actual production persistence path instead of the
    shared-transaction test fixtures.
    """
    TestSessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)

    def committing_get_session() -> Iterator[Session]:
        session = TestSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Seed the dev user with its own real commit -- not the `dev_user`
    # fixture, which lives inside the rolled-back transaction.
    seed_session = TestSessionLocal()
    try:
        seed_session.add(User(id=DEV_USER_ID, email="dev@wyro.app", auth_provider="dev"))
        seed_session.commit()
    finally:
        seed_session.close()

    app.dependency_overrides[get_session] = committing_get_session
    trip_id: uuid.UUID | None = None
    try:
        with TestClient(app) as client:
            r = client.post("/trips", json=TRIP_BODY, headers=AUTH)
        assert r.status_code == 201, r.text
        trip_id = uuid.UUID(r.json()["id"])

        # The request's session has been committed and closed by now. Read
        # the trip back from a brand-new, independent session to prove the
        # row actually persisted -- this is the assertion that the old,
        # commit-less `get_session` would fail.
        verify_session = TestSessionLocal()
        try:
            persisted = verify_session.get(Trip, trip_id)
            assert persisted is not None, "trip was not committed to the database"
            assert persisted.title == "Japan"
            cities = sorted(persisted.cities, key=lambda c: c.arrive_date)
            assert [c.city for c in cities] == ["Tokyo", "Kyoto"]
        finally:
            verify_session.close()
    finally:
        app.dependency_overrides.clear()
        # Mandatory cleanup: this test commits real rows to wyro_test, and
        # _engine only drops/recreates tables once per pytest session, so
        # leftovers would leak into other tests (e.g. test_list_trips).
        cleanup_session = TestSessionLocal()
        try:
            if trip_id is not None:
                trip = cleanup_session.get(Trip, trip_id)
                if trip is not None:
                    cleanup_session.delete(trip)  # cascades to trip_cities
            dev_user = cleanup_session.get(User, DEV_USER_ID)
            if dev_user is not None:
                cleanup_session.delete(dev_user)
            cleanup_session.commit()
        finally:
            cleanup_session.close()
