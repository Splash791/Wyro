import uuid

from app.models import Trip, User
from app.seed import seed_dev_user

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


def test_requires_auth(client):
    assert client.get("/trips").status_code == 401


def test_me(client, session):
    seed_dev_user(session)
    r = client.get("/me", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["email"] == "dev@wyro.app"


def test_create_and_read_trip_with_days(client, session):
    seed_dev_user(session)
    r = client.post("/trips", json=TRIP_BODY, headers=AUTH)
    assert r.status_code == 201, r.text
    trip = r.json()
    assert trip["title"] == "Japan"
    assert len(trip["cities"]) == 2
    # Days derived: Tokyo 4/1, 4/2; Kyoto 4/2, 4/3
    assert [(d["date"], d["city"]) for d in trip["days"]] == [
        ("2026-04-01", "Tokyo"),
        ("2026-04-02", "Tokyo"),
        ("2026-04-02", "Kyoto"),
        ("2026-04-03", "Kyoto"),
    ]

    trip_id = trip["id"]
    got = client.get(f"/trips/{trip_id}", headers=AUTH)
    assert got.status_code == 200
    assert got.json()["id"] == trip_id


def test_list_trips(client, session):
    seed_dev_user(session)
    client.post("/trips", json=TRIP_BODY, headers=AUTH)
    r = client.get("/trips", headers=AUTH)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_missing_trip_404(client, session):
    seed_dev_user(session)
    r = client.get("/trips/00000000-0000-0000-0000-0000000000ff", headers=AUTH)
    assert r.status_code == 404


def test_other_users_trip_is_404(client, session):
    seed_dev_user(session)
    other = User(id=uuid.uuid4(), email="other@test.app", auth_provider="dev")
    session.add(other)
    session.flush()
    other_trip = Trip(
        user_id=other.id,
        title="Not yours",
        start_date="2026-05-01",
        end_date="2026-05-02",
    )
    session.add(other_trip)
    session.flush()
    r = client.get(f"/trips/{other_trip.id}", headers=AUTH)
    assert r.status_code == 404
