"""Regression test for the "flush but never commit" bug.

The `client`/`session`/`dev_user` fixtures used by the rest of the suite all
share a single per-test transaction that is rolled back at teardown (see
conftest.py). That makes writes visible to the test via `flush`, but it can
never detect a production bug where `get_session` fails to `commit()` before
`close()` rolls back the transaction -- the rollback happens either way.

This test deliberately avoids those fixtures AND does not override the
`get_session` dependency. Instead it repoints `app.db.SessionLocal` at the real
test engine, so the genuine `app.db.get_session` generator runs through a real
TestClient request -- including its post-yield `commit()`. It then opens a
brand-new, independent `Session` to read the row back. If `get_session` only
flushed (the bug, or a future regression that removes the commit), the row
would not exist in a different session/connection and this test would fail.
"""

import uuid

import app.db as db
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

    This exercises the REAL `app.db.get_session` (no dependency override) by
    repointing `app.db.SessionLocal` at the wyro_test engine. If the real
    `get_session` ever stops committing, this test fails -- which is the whole
    point (the override-based version could not catch that regression).
    """
    TestSessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)

    # Guard: no stray dependency override should shadow the real get_session.
    assert get_session not in app.dependency_overrides

    original_session_local = db.SessionLocal
    db.SessionLocal = TestSessionLocal  # the real get_session reads this global

    # Seed the dev user with a real commit (not the rolled-back `dev_user` fixture).
    seed_session = TestSessionLocal()
    try:
        seed_session.add(User(id=DEV_USER_ID, email="dev@wyro.app", auth_provider="dev"))
        seed_session.commit()
    finally:
        seed_session.close()

    trip_id: uuid.UUID | None = None
    try:
        with TestClient(app) as client:
            r = client.post("/trips", json=TRIP_BODY, headers=AUTH)
        assert r.status_code == 201, r.text
        trip_id = uuid.UUID(r.json()["id"])

        # The request's session has been committed and closed by the real
        # get_session by now. Read the trip back from a brand-new, independent
        # session to prove the row actually persisted -- the commit-less
        # get_session would fail this assertion.
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
        db.SessionLocal = original_session_local
        # Mandatory cleanup: this test commits real rows to wyro_test, and
        # _engine only drops/recreates tables once per pytest session, so
        # leftovers would leak into other tests (e.g. test_list_trips).
        cleanup_session = TestSessionLocal()
        try:
            if trip_id is not None:
                trip = cleanup_session.get(Trip, trip_id)
                if trip is not None:
                    cleanup_session.delete(trip)  # ORM cascade removes trip_cities
            dev_user = cleanup_session.get(User, DEV_USER_ID)
            if dev_user is not None:
                cleanup_session.delete(dev_user)
            cleanup_session.commit()
        finally:
            cleanup_session.close()
