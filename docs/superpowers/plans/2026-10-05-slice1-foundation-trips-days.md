# Slice 1: Foundation + Trips/Days Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Wyro monorepo and ship Feature 1 — create a trip with cities and dates and see days generated per city in local time — online-only, with a dev-stub user.

**Architecture:** A monorepo with an Expo (React Native + TypeScript) mobile app and a FastAPI backend over Postgres/PostGIS. FastAPI owns the API contract and emits an OpenAPI schema from which the mobile app's TypeScript types are generated. Days are not stored; they are derived from each city's arrive/leave dates by a pure function. Auth is a dev stub (one seeded user resolved from a dev token) so real OAuth can slot into the same dependency later.

**Tech Stack:** Backend — FastAPI, SQLAlchemy 2.0 (typed), Alembic, Pydantic v2, `uv`, Postgres + PostGIS (Docker). Mobile — Expo dev build (not Expo Go), TypeScript, expo-router, TanStack Query, `openapi-typescript` for generated types. Tests — pytest (backend), Jest + React Native Testing Library via `jest-expo` (mobile).

## Global Constraints

- All times stored as **local time + IANA time zone**; never a bare UTC timestamp. (Slice 1 stores dates + the city's IANA tz string.)
- Mobile is **TypeScript**, runs as an **Expo development build, never Expo Go**.
- Backend API is the single source of truth; mobile TS types are **generated** from its OpenAPI schema — never hand-duplicated.
- **Days are derived, not stored** — no `days` table.
- Everything runs on **free/hobby tiers at personal scale**.
- Backend Python managed with **`uv`**; mobile package manager is **npm** (Expo default).
- Dev user id is the constant UUID `00000000-0000-0000-0000-000000000001`; dev auth token is the literal string `dev-token`.
- **DB host port is `5433`** (updated 2026-10-06 — a host-native `postgresql@14` already occupies `5432`). The container's internal port stays `5432`; `docker-compose.yml` publishes `5433:5432` and the backend DB URL is `postgresql+psycopg://wyro:wyro@localhost:5433/wyro`. Task 1/2 code blocks below still show the original `5432`; the committed code uses `5433`.

---

## File Structure

```
wyro/
  docker-compose.yml              # Postgres + PostGIS for local dev
  .gitignore
  README.md
  apps/
    api/
      pyproject.toml              # uv project + deps
      alembic.ini
      alembic/
        env.py
        versions/                 # migrations
      app/
        __init__.py
        config.py                 # pydantic-settings
        db.py                     # engine, session, Base
        models.py                 # users, trips, trip_cities
        schemas.py                # Pydantic request/response models
        days.py                   # derive-days pure function
        auth.py                   # dev-auth dependency + seed helper
        main.py                   # FastAPI app, health, router mount
        routers/
          __init__.py
          trips.py                # /me, /trips endpoints
      tests/
        conftest.py               # test DB + client fixtures
        test_days.py
        test_auth.py
        test_trips_api.py
    mobile/
      (expo app — see Task 9)
      lib/
        api.ts                    # typed fetch client
        queries.ts                # TanStack Query hooks
        days.ts                   # client-side day formatting
      app/
        _layout.tsx
        index.tsx                 # trips list
        trip/
          new.tsx                 # create trip
          [id].tsx                # trip detail w/ days
      __tests__/
  packages/
    api-types/
      openapi.json                # exported schema
      index.ts                    # generated TS types
      package.json
```

---

## Task 1: Monorepo scaffold + Postgres

**Files:**
- Create: `.gitignore`, `README.md`, `docker-compose.yml`

**Interfaces:**
- Produces: a running Postgres+PostGIS on `localhost:5432`, db `wyro`, user `wyro`, password `wyro`; connection URL `postgresql+psycopg://wyro:wyro@localhost:5432/wyro`.

- [ ] **Step 1: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/

# Node / Expo
node_modules/
.expo/
dist/
*.log

# Env
.env
.env.*
!.env.example

# OS
.DS_Store
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: wyro
      POSTGRES_PASSWORD: wyro
      POSTGRES_DB: wyro
    ports:
      - "5432:5432"
    volumes:
      - wyro_pgdata:/var/lib/postgresql/data

volumes:
  wyro_pgdata:
```

- [ ] **Step 3: Write `README.md`**

```markdown
# Wyro

Solo-traveler trip-planning app. Monorepo: `apps/api` (FastAPI), `apps/mobile`
(Expo), `packages/api-types` (generated TS types).

## Local dev
1. `docker compose up -d` — start Postgres/PostGIS.
2. Backend: see `apps/api/README` — `uv run uvicorn app.main:app --reload`.
3. Mobile: see `apps/mobile` — `npm run start`.

Built in vertical slices; see `docs/superpowers/specs/`.
```

- [ ] **Step 4: Remove the placeholder file and start the database**

Run:
```bash
rm -f txt.txt
docker compose up -d
docker compose ps
```
Expected: the `db` service shows state `running` (or `healthy`), port `5432` published.

- [ ] **Step 5: Verify the database accepts connections**

Run:
```bash
docker compose exec db psql -U wyro -d wyro -c "SELECT 1;"
```
Expected: a one-row result with `1`.

- [ ] **Step 6: Commit**

```bash
git add .gitignore README.md docker-compose.yml
git rm --cached txt.txt 2>/dev/null; git add -A
git commit -m "chore: monorepo scaffold and local Postgres"
```

---

## Task 2: FastAPI skeleton

**Files:**
- Create: `apps/api/pyproject.toml`, `apps/api/app/__init__.py`, `apps/api/app/config.py`, `apps/api/app/db.py`, `apps/api/app/main.py`

**Interfaces:**
- Produces: `app.config.settings` (attrs `database_url: str`, `dev_token: str`); `app.db.Base` (declarative base), `app.db.engine`, `app.db.SessionLocal`, `app.db.get_session` (FastAPI dependency yielding a `Session`); `app.main.app` (FastAPI instance) with `GET /health` → `{"status": "ok"}`.

- [ ] **Step 1: Initialize the uv project and add dependencies**

Run from `apps/api`:
```bash
cd apps/api
uv init --name wyro-api --no-readme --python 3.12
uv add fastapi "uvicorn[standard]" "sqlalchemy>=2.0" alembic "psycopg[binary]" pydantic-settings
uv add --dev pytest httpx
```
Then delete the sample `apps/api/hello.py` if `uv init` created one.

- [ ] **Step 2: Write `apps/api/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://wyro:wyro@localhost:5432/wyro"
    dev_token: str = "dev-token"


settings = Settings()
```

- [ ] **Step 3: Write `apps/api/app/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 4: Write `apps/api/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Wyro API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Run the server and verify health**

Run from `apps/api`:
```bash
uv run uvicorn app.main:app --port 8000 &
sleep 2
curl -s localhost:8000/health
kill %1
```
Expected: `{"status":"ok"}`.

- [ ] **Step 6: Commit**

```bash
git add apps/api
git commit -m "feat(api): FastAPI skeleton with health check"
```

---

## Task 3: Database models + test fixtures

**Files:**
- Create: `apps/api/app/models.py`, `apps/api/tests/__init__.py`, `apps/api/tests/conftest.py`

**Interfaces:**
- Consumes: `app.db.Base`.
- Produces:
  - `User(id: UUID, email: str, auth_provider: str, import_address: str | None, created_at: datetime)`
  - `Trip(id: UUID, user_id: UUID, title: str, start_date: date, end_date: date, offline_downloaded_at: datetime | None, cities: list[TripCity])`
  - `TripCity(id: UUID, trip_id: UUID, city: str, country_code: str, time_zone: str, arrive_date: date, leave_date: date)`
  - pytest fixtures: `session` (a `Session` bound to a per-test transaction, rolled back after), `client` (a `fastapi.testclient.TestClient` whose `get_session` dependency uses `session`), `dev_user` (a seeded `User` with id `00000000-0000-0000-0000-000000000001`).

- [ ] **Step 1: Write `apps/api/app/models.py`**

```python
import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)
    auth_provider: Mapped[str] = mapped_column(String)  # "google" | "apple" | "dev"
    import_address: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    start_date: Mapped[datetime.date] = mapped_column(Date)
    end_date: Mapped[datetime.date] = mapped_column(Date)
    offline_downloaded_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cities: Mapped[list["TripCity"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripCity.arrive_date",
    )


class TripCity(Base):
    __tablename__ = "trip_cities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id"))
    city: Mapped[str] = mapped_column(String)
    country_code: Mapped[str] = mapped_column(String)  # ISO 3166-1 alpha-2
    time_zone: Mapped[str] = mapped_column(String)  # IANA, e.g. "Asia/Tokyo"
    arrive_date: Mapped[datetime.date] = mapped_column(Date)
    leave_date: Mapped[datetime.date] = mapped_column(Date)

    trip: Mapped["Trip"] = relationship(back_populates="cities")
```

- [ ] **Step 2: Write `apps/api/tests/__init__.py`**

```python
```
(empty file)

- [ ] **Step 3: Write `apps/api/tests/conftest.py`**

```python
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
```

- [ ] **Step 4: Write a smoke test and run it**

Create `apps/api/tests/test_models.py`:
```python
def test_dev_user_fixture_persists(session, dev_user):
    from app.models import User

    found = session.get(User, dev_user.id)
    assert found is not None
    assert found.email == "dev@wyro.app"
```

Run from `apps/api` (Postgres must be up):
```bash
uv run pytest tests/test_models.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/models.py apps/api/tests
git commit -m "feat(api): data models and pytest DB fixtures"
```

---

## Task 4: Day-generation function

**Files:**
- Create: `apps/api/app/days.py`, `apps/api/tests/test_days.py`

**Interfaces:**
- Consumes: `app.models.TripCity`.
- Produces: `app.days.Day` (dataclass: `date: datetime.date`, `city: str`, `country_code: str`, `time_zone: str`) and `app.days.generate_days(cities: list[TripCity]) -> list[Day]` — one `Day` per calendar date from each city's `arrive_date` to `leave_date` inclusive, ordered by date then by city arrival order.

- [ ] **Step 1: Write the failing tests**

`apps/api/tests/test_days.py`:
```python
import datetime

from app.days import Day, generate_days
from app.models import TripCity


def _city(city, tz, arrive, leave, cc="JP"):
    return TripCity(
        city=city,
        country_code=cc,
        time_zone=tz,
        arrive_date=datetime.date.fromisoformat(arrive),
        leave_date=datetime.date.fromisoformat(leave),
    )


def test_single_day_city():
    cities = [_city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-01")]
    days = generate_days(cities)
    assert days == [
        Day(datetime.date(2026, 4, 1), "Tokyo", "JP", "Asia/Tokyo"),
    ]


def test_multi_day_city_inclusive():
    cities = [_city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-03")]
    days = generate_days(cities)
    assert [d.date for d in days] == [
        datetime.date(2026, 4, 1),
        datetime.date(2026, 4, 2),
        datetime.date(2026, 4, 3),
    ]


def test_month_boundary():
    cities = [_city("Tokyo", "Asia/Tokyo", "2026-01-30", "2026-02-01")]
    days = generate_days(cities)
    assert [d.date for d in days] == [
        datetime.date(2026, 1, 30),
        datetime.date(2026, 1, 31),
        datetime.date(2026, 2, 1),
    ]


def test_adjacent_cities_each_get_their_own_day():
    cities = [
        _city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-02"),
        _city("Kyoto", "Asia/Tokyo", "2026-04-02", "2026-04-03"),
    ]
    days = generate_days(cities)
    assert [(d.date.isoformat(), d.city) for d in days] == [
        ("2026-04-01", "Tokyo"),
        ("2026-04-02", "Tokyo"),
        ("2026-04-02", "Kyoto"),
        ("2026-04-03", "Kyoto"),
    ]


def test_cities_entered_out_of_order_are_sorted_by_arrival():
    cities = [
        _city("Kyoto", "Asia/Tokyo", "2026-04-05", "2026-04-06"),
        _city("Tokyo", "Asia/Tokyo", "2026-04-01", "2026-04-02"),
    ]
    days = generate_days(cities)
    assert [d.city for d in days] == ["Tokyo", "Tokyo", "Kyoto", "Kyoto"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `apps/api`:
```bash
uv run pytest tests/test_days.py -v
```
Expected: FAIL / ImportError — `app.days` does not exist.

- [ ] **Step 3: Write `apps/api/app/days.py`**

```python
import datetime
from dataclasses import dataclass

from app.models import TripCity


@dataclass(frozen=True)
class Day:
    date: datetime.date
    city: str
    country_code: str
    time_zone: str


def generate_days(cities: list[TripCity]) -> list[Day]:
    days: list[Day] = []
    for city in sorted(cities, key=lambda c: c.arrive_date):
        current = city.arrive_date
        while current <= city.leave_date:
            days.append(Day(current, city.city, city.country_code, city.time_zone))
            current += datetime.timedelta(days=1)
    return days
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `apps/api`:
```bash
uv run pytest tests/test_days.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/days.py apps/api/tests/test_days.py
git commit -m "feat(api): derive days from trip cities"
```

---

## Task 5: Pydantic schemas

**Files:**
- Create: `apps/api/app/schemas.py`

**Interfaces:**
- Consumes: none (pure Pydantic models).
- Produces:
  - `TripCityCreate(city: str, country_code: str, time_zone: str, arrive_date: date, leave_date: date)`
  - `TripCreate(title: str, start_date: date, end_date: date, cities: list[TripCityCreate])`
  - `TripCityRead(id: UUID, city, country_code, time_zone, arrive_date, leave_date)`
  - `DayRead(date: date, city: str, country_code: str, time_zone: str)`
  - `TripRead(id: UUID, title, start_date, end_date, cities: list[TripCityRead], days: list[DayRead])`
  - `UserRead(id: UUID, email: str, auth_provider: str, import_address: str | None)`

- [ ] **Step 1: Write `apps/api/app/schemas.py`**

```python
import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class TripCityCreate(BaseModel):
    city: str
    country_code: str
    time_zone: str
    arrive_date: datetime.date
    leave_date: datetime.date


class TripCreate(BaseModel):
    title: str
    start_date: datetime.date
    end_date: datetime.date
    cities: list[TripCityCreate]


class TripCityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    city: str
    country_code: str
    time_zone: str
    arrive_date: datetime.date
    leave_date: datetime.date


class DayRead(BaseModel):
    date: datetime.date
    city: str
    country_code: str
    time_zone: str


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    start_date: datetime.date
    end_date: datetime.date
    cities: list[TripCityRead]
    days: list[DayRead]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    auth_provider: str
    import_address: str | None
```

- [ ] **Step 2: Verify the module imports**

Run from `apps/api`:
```bash
uv run python -c "import app.schemas; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/schemas.py
git commit -m "feat(api): request/response schemas"
```

---

## Task 6: Dev-auth dependency + seed

**Files:**
- Create: `apps/api/app/auth.py`, `apps/api/app/seed.py`, `apps/api/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.config.settings.dev_token`, `app.db.get_session`, `app.models.User`.
- Produces:
  - `app.auth.DEV_USER_ID: uuid.UUID` = `00000000-0000-0000-0000-000000000001`.
  - `app.auth.get_current_user(authorization: str = Header(...), session = Depends(get_session)) -> User` — returns the dev user when the `Authorization` header is `Bearer <dev_token>`; raises `HTTPException(401)` otherwise. Real OAuth replaces this body later.
  - `app.seed.seed_dev_user(session) -> User` — idempotently inserts the dev user.

- [ ] **Step 1: Write the failing tests**

`apps/api/tests/test_auth.py`:
```python
import pytest
from fastapi import HTTPException

from app.auth import DEV_USER_ID, get_current_user
from app.seed import seed_dev_user


def test_seed_is_idempotent(session):
    u1 = seed_dev_user(session)
    u2 = seed_dev_user(session)
    assert u1.id == u2.id == DEV_USER_ID


def test_valid_token_returns_dev_user(session):
    seed_dev_user(session)
    user = get_current_user(authorization="Bearer dev-token", session=session)
    assert user.id == DEV_USER_ID


def test_bad_token_rejected(session):
    seed_dev_user(session)
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Bearer nope", session=session)
    assert exc.value.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `apps/api`:
```bash
uv run pytest tests/test_auth.py -v
```
Expected: FAIL — `app.auth` / `app.seed` do not exist.

- [ ] **Step 3: Write `apps/api/app/seed.py`**

```python
import uuid

from sqlalchemy.orm import Session

from app.models import User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def seed_dev_user(session: Session) -> User:
    user = session.get(User, DEV_USER_ID)
    if user is None:
        user = User(id=DEV_USER_ID, email="dev@wyro.app", auth_provider="dev")
        session.add(user)
        session.flush()
    return user
```

- [ ] **Step 4: Write `apps/api/app/auth.py`**

```python
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User
from app.seed import DEV_USER_ID


def get_current_user(
    authorization: str = Header(default=""),
    session: Session = Depends(get_session),
) -> User:
    expected = f"Bearer {settings.dev_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = session.get(User, DEV_USER_ID)
    if user is None:
        raise HTTPException(status_code=401, detail="Dev user not seeded")
    return user
```

- [ ] **Step 5: Run tests to verify they pass**

Run from `apps/api`:
```bash
uv run pytest tests/test_auth.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/auth.py apps/api/app/seed.py apps/api/tests/test_auth.py
git commit -m "feat(api): dev-stub auth and seed helper"
```

---

## Task 7: Trips router + endpoints

**Files:**
- Create: `apps/api/app/routers/__init__.py`, `apps/api/app/routers/trips.py`, `apps/api/tests/test_trips_api.py`
- Modify: `apps/api/app/main.py`

**Interfaces:**
- Consumes: `app.auth.get_current_user`, `app.db.get_session`, `app.models.*`, `app.schemas.*`, `app.days.generate_days`.
- Produces endpoints (all require `Authorization: Bearer dev-token`):
  - `GET /me` → `UserRead`
  - `GET /trips` → `list[TripRead]` for the current user
  - `POST /trips` (body `TripCreate`) → `TripRead` (201)
  - `GET /trips/{trip_id}` → `TripRead`; 404 if not owned by the user

- [ ] **Step 1: Write the failing tests**

`apps/api/tests/test_trips_api.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `apps/api`:
```bash
uv run pytest tests/test_trips_api.py -v
```
Expected: FAIL — router not mounted / endpoints missing.

- [ ] **Step 3: Write `apps/api/app/routers/__init__.py`**

```python
```
(empty file)

- [ ] **Step 4: Write `apps/api/app/routers/trips.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.days import generate_days
from app.db import get_session
from app.models import Trip, TripCity, User
from app.schemas import DayRead, TripCreate, TripRead, UserRead

router = APIRouter()


def _to_trip_read(trip: Trip) -> TripRead:
    read = TripRead.model_validate(trip)
    read.days = [DayRead(**vars(d)) for d in generate_days(trip.cities)]
    return read


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/trips", response_model=list[TripRead])
def list_trips(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[TripRead]:
    trips = session.scalars(
        select(Trip).where(Trip.user_id == user.id).order_by(Trip.start_date)
    ).all()
    return [_to_trip_read(t) for t in trips]


@router.post("/trips", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(
    body: TripCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TripRead:
    trip = Trip(
        user_id=user.id,
        title=body.title,
        start_date=body.start_date,
        end_date=body.end_date,
        cities=[TripCity(**c.model_dump()) for c in body.cities],
    )
    session.add(trip)
    session.flush()
    session.refresh(trip)
    return _to_trip_read(trip)


@router.get("/trips/{trip_id}", response_model=TripRead)
def get_trip(
    trip_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TripRead:
    trip = session.get(Trip, trip_id)
    if trip is None or trip.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return _to_trip_read(trip)
```

- [ ] **Step 5: Mount the router — rewrite `apps/api/app/main.py`**

```python
from fastapi import FastAPI

from app.routers import trips

app = FastAPI(title="Wyro API", version="0.1.0")
app.include_router(trips.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run tests to verify they pass**

Run from `apps/api`:
```bash
uv run pytest -v
```
Expected: all tests pass (days, auth, trips, models).

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/routers apps/api/app/main.py apps/api/tests/test_trips_api.py
git commit -m "feat(api): trips endpoints with derived days"
```

---

## Task 8: Alembic migration + dev run script

**Files:**
- Create: `apps/api/alembic.ini`, `apps/api/alembic/env.py`, `apps/api/alembic/script.py.mako`, the first migration under `apps/api/alembic/versions/`
- Create: `apps/api/README.md`

**Interfaces:**
- Consumes: `app.db.Base`, `app.models`, `app.config.settings`.
- Produces: a migration that enables the `postgis` extension and creates `users`, `trips`, `trip_cities`; the dev database usable by the running server after `seed`.

- [ ] **Step 1: Initialize Alembic**

Run from `apps/api`:
```bash
uv run alembic init alembic
```

- [ ] **Step 2: Point Alembic at the app metadata — rewrite `apps/api/alembic/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.db import Base
from app import models  # noqa: F401  (register tables on Base.metadata)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Autogenerate the first migration**

Run from `apps/api` (Postgres up):
```bash
uv run alembic revision --autogenerate -m "initial schema"
```
Then open the generated file in `alembic/versions/` and, at the top of `upgrade()`, add:
```python
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
```

- [ ] **Step 4: Apply the migration and seed the dev user**

Run from `apps/api`:
```bash
uv run alembic upgrade head
uv run python -c "from app.db import SessionLocal; from app.seed import seed_dev_user; s=SessionLocal(); seed_dev_user(s); s.commit(); print('seeded')"
```
Expected: `seeded`.

- [ ] **Step 5: Smoke-test the live endpoint end to end**

Run from `apps/api`:
```bash
uv run uvicorn app.main:app --port 8000 &
sleep 2
curl -s -X POST localhost:8000/trips -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"title":"Japan","start_date":"2026-04-01","end_date":"2026-04-02","cities":[{"city":"Tokyo","country_code":"JP","time_zone":"Asia/Tokyo","arrive_date":"2026-04-01","leave_date":"2026-04-02"}]}'
kill %1
```
Expected: JSON with `"days"` containing 2026-04-01 and 2026-04-02 for Tokyo.

- [ ] **Step 6: Write `apps/api/README.md`**

```markdown
# Wyro API

FastAPI + SQLAlchemy + Postgres/PostGIS.

## Run
1. `docker compose up -d` (from repo root).
2. `uv run alembic upgrade head`
3. `uv run python -m app.seed_cli` once, or the inline seed in the plan.
4. `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

Dev auth: send header `Authorization: Bearer dev-token`.

## Test
`uv run pytest` (needs Postgres running; uses a `wyro_test` database).
```

- [ ] **Step 7: Commit**

```bash
git add apps/api/alembic apps/api/alembic.ini apps/api/README.md
git commit -m "feat(api): alembic migrations and dev run docs"
```

---

## Task 9: Generate TypeScript types from OpenAPI

**Files:**
- Create: `packages/api-types/package.json`, `packages/api-types/openapi.json`, `packages/api-types/index.ts`, `packages/api-types/README.md`

**Interfaces:**
- Consumes: the live API's `/openapi.json`.
- Produces: `packages/api-types/index.ts` exporting `paths` and `components` types used by the mobile client; an npm script `generate` that regenerates them.

- [ ] **Step 1: Export the OpenAPI schema from the running app**

Run from `apps/api`:
```bash
uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../../packages/api-types/openapi.json
```

- [ ] **Step 2: Write `packages/api-types/package.json`**

```json
{
  "name": "@wyro/api-types",
  "version": "0.1.0",
  "main": "index.ts",
  "types": "index.ts",
  "scripts": {
    "generate": "openapi-typescript openapi.json -o index.ts"
  },
  "devDependencies": {
    "openapi-typescript": "^7.4.0"
  }
}
```

- [ ] **Step 3: Generate the types**

Run from `packages/api-types`:
```bash
cd packages/api-types
npm install
npm run generate
```
Expected: `index.ts` is created containing `export interface paths` and `export interface components`.

- [ ] **Step 4: Write `packages/api-types/README.md`**

```markdown
# @wyro/api-types

TypeScript types generated from the Wyro API's OpenAPI schema.

Regenerate after API changes:
1. From `apps/api`: export the schema to `../../packages/api-types/openapi.json`
   (see the Slice 1 plan, Task 9 Step 1).
2. From here: `npm run generate`.

Never hand-edit `index.ts`.
```

- [ ] **Step 5: Commit**

```bash
git add packages/api-types
git commit -m "feat(types): generate TS types from OpenAPI schema"
```

---

## Task 10: Expo app scaffold + typed client

**Files:**
- Create the Expo app in `apps/mobile` (generator output), plus:
  - Create: `apps/mobile/.env.example`, `apps/mobile/lib/api.ts`, `apps/mobile/lib/queries.ts`, `apps/mobile/lib/days.ts`, `apps/mobile/app/_layout.tsx`

**Interfaces:**
- Consumes: `@wyro/api-types` (relative import), `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_DEV_TOKEN`.
- Produces:
  - `lib/api.ts`: `apiFetch<T>(path, init?) -> Promise<T>` attaching `Authorization: Bearer <EXPO_PUBLIC_DEV_TOKEN>`; TS aliases `Trip`, `TripCreate`, `Day`, `User` derived from the generated schema.
  - `lib/queries.ts`: `useTrips()`, `useTrip(id)`, `useCreateTrip()` TanStack Query hooks.
  - `lib/days.ts`: `formatDayLabel(day: Day) -> string` rendering the date in the day's IANA tz.
  - `app/_layout.tsx`: a `QueryClientProvider` + expo-router `Stack`.

- [ ] **Step 1: Scaffold the Expo app**

Run from repo root:
```bash
npx create-expo-app@latest apps/mobile
cd apps/mobile
npx expo install expo-dev-client @tanstack/react-query
```
The default template includes TypeScript + expo-router. Remove the demo tabs: delete `apps/mobile/app/(tabs)` and any starter screens so `app/` holds only what this plan creates.

- [ ] **Step 2: Add the generated types as a dependency**

In `apps/mobile/package.json`, add under `dependencies`:
```json
    "@wyro/api-types": "file:../../packages/api-types"
```
Then run from `apps/mobile`:
```bash
npm install
```

- [ ] **Step 3: Write `apps/mobile/.env.example`**

```bash
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_DEV_TOKEN=dev-token
```
Copy it to `.env` for local use:
```bash
cp .env.example .env
```

- [ ] **Step 4: Write `apps/mobile/lib/api.ts`**

```typescript
import type { components } from "@wyro/api-types";

export type Trip = components["schemas"]["TripRead"];
export type TripCreate = components["schemas"]["TripCreate"];
export type Day = components["schemas"]["DayRead"];
export type User = components["schemas"]["UserRead"];

const BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN = process.env.EXPO_PUBLIC_DEV_TOKEN ?? "dev-token";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}
```

- [ ] **Step 5: Write `apps/mobile/lib/queries.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, type Trip, type TripCreate } from "./api";

export function useTrips() {
  return useQuery({
    queryKey: ["trips"],
    queryFn: () => apiFetch<Trip[]>("/trips"),
  });
}

export function useTrip(id: string) {
  return useQuery({
    queryKey: ["trips", id],
    queryFn: () => apiFetch<Trip>(`/trips/${id}`),
  });
}

export function useCreateTrip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TripCreate) =>
      apiFetch<Trip>("/trips", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trips"] }),
  });
}
```

- [ ] **Step 6: Write `apps/mobile/lib/days.ts`**

```typescript
import type { Day } from "./api";

// Render a trip day's date in that city's IANA time zone.
export function formatDayLabel(day: Day): string {
  const date = new Date(`${day.date}T12:00:00Z`);
  const formatted = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: day.time_zone,
  }).format(date);
  return `${formatted} · ${day.city}`;
}
```

- [ ] **Step 7: Write `apps/mobile/app/_layout.tsx`**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerTitle: "Wyro" }} />
    </QueryClientProvider>
  );
}
```

- [ ] **Step 8: Verify the app bundles**

Run from `apps/mobile`:
```bash
npx tsc --noEmit
```
Expected: no type errors.

- [ ] **Step 9: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): expo scaffold, typed API client, query hooks"
```

---

## Task 11: Trips list + create screens

**Files:**
- Create: `apps/mobile/app/index.tsx`, `apps/mobile/app/trip/new.tsx`
- Create: `apps/mobile/jest.config.js`, `apps/mobile/__tests__/new-trip.test.tsx`
- Modify: `apps/mobile/package.json` (jest deps + test script)

**Interfaces:**
- Consumes: `useTrips`, `useCreateTrip` from `lib/queries`.
- Produces: a trips list screen linking to each trip and to `trip/new`; a create-trip form that submits a `TripCreate` with one city and navigates to the new trip on success.

- [ ] **Step 1: Add Jest tooling**

Run from `apps/mobile`:
```bash
npx expo install jest-expo jest react-test-renderer
npm install --save-dev @testing-library/react-native
```
Add to `apps/mobile/package.json` `scripts`:
```json
    "test": "jest"
```

- [ ] **Step 2: Write `apps/mobile/jest.config.js`**

```javascript
module.exports = {
  preset: "jest-expo",
  transformIgnorePatterns: [
    "node_modules/(?!((jest-)?react-native|@react-native(-community)?|expo(nent)?|@expo(nent)?/.*|@tanstack/.*|react-navigation|@react-navigation/.*))",
  ],
};
```

- [ ] **Step 3: Write the failing test**

`apps/mobile/__tests__/new-trip.test.tsx`:
```tsx
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import NewTrip from "../app/trip/new";

jest.mock("expo-router", () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
}));

const mockMutate = jest.fn();
jest.mock("../lib/queries", () => ({
  useCreateTrip: () => ({ mutate: mockMutate, isPending: false }),
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

test("submits a trip with the entered title and city", async () => {
  const { getByTestId, getByText } = wrap(<NewTrip />);
  fireEvent.changeText(getByTestId("title"), "Japan");
  fireEvent.changeText(getByTestId("city"), "Tokyo");
  fireEvent.press(getByText("Create trip"));

  await waitFor(() => expect(mockMutate).toHaveBeenCalled());
  const body = mockMutate.mock.calls[0][0];
  expect(body.title).toBe("Japan");
  expect(body.cities[0].city).toBe("Tokyo");
});
```

- [ ] **Step 4: Run the test to verify it fails**

Run from `apps/mobile`:
```bash
npm test -- new-trip
```
Expected: FAIL — `app/trip/new` does not exist.

- [ ] **Step 5: Write `apps/mobile/app/trip/new.tsx`**

```tsx
import { useRouter } from "expo-router";
import { useState } from "react";
import { Button, StyleSheet, Text, TextInput, View } from "react-native";

import { useCreateTrip } from "../../lib/queries";

export default function NewTrip() {
  const router = useRouter();
  const createTrip = useCreateTrip();
  const [title, setTitle] = useState("");
  const [city, setCity] = useState("");
  const [timeZone, setTimeZone] = useState("Asia/Tokyo");
  const [countryCode, setCountryCode] = useState("JP");
  const [arrive, setArrive] = useState("2026-04-01");
  const [leave, setLeave] = useState("2026-04-03");

  const submit = () => {
    createTrip.mutate(
      {
        title,
        start_date: arrive,
        end_date: leave,
        cities: [
          {
            city,
            country_code: countryCode,
            time_zone: timeZone,
            arrive_date: arrive,
            leave_date: leave,
          },
        ],
      },
      { onSuccess: (trip) => router.replace(`/trip/${trip.id}`) },
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Trip title</Text>
      <TextInput testID="title" style={styles.input} value={title} onChangeText={setTitle} />
      <Text style={styles.label}>City</Text>
      <TextInput testID="city" style={styles.input} value={city} onChangeText={setCity} />
      <Text style={styles.label}>Country code</Text>
      <TextInput testID="country" style={styles.input} value={countryCode} onChangeText={setCountryCode} />
      <Text style={styles.label}>IANA time zone</Text>
      <TextInput testID="tz" style={styles.input} value={timeZone} onChangeText={setTimeZone} />
      <Text style={styles.label}>Arrive (YYYY-MM-DD)</Text>
      <TextInput testID="arrive" style={styles.input} value={arrive} onChangeText={setArrive} />
      <Text style={styles.label}>Leave (YYYY-MM-DD)</Text>
      <TextInput testID="leave" style={styles.input} value={leave} onChangeText={setLeave} />
      <Button title="Create trip" onPress={submit} disabled={createTrip.isPending} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, gap: 4 },
  label: { fontSize: 12, color: "#555", marginTop: 8 },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 6, padding: 8 },
});
```

- [ ] **Step 6: Write `apps/mobile/app/index.tsx`**

```tsx
import { Link } from "expo-router";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import { useTrips } from "../lib/queries";

export default function Trips() {
  const { data: trips, isLoading, error } = useTrips();

  if (isLoading) return <ActivityIndicator style={styles.center} />;
  if (error) return <Text style={styles.center}>Couldn’t load trips.</Text>;

  return (
    <View style={styles.container}>
      <Link href="/trip/new" style={styles.newLink}>
        + New trip
      </Link>
      <FlatList
        data={trips ?? []}
        keyExtractor={(t) => t.id}
        ListEmptyComponent={<Text style={styles.empty}>No trips yet.</Text>}
        renderItem={({ item }) => (
          <Link href={`/trip/${item.id}`} style={styles.row}>
            {item.title} · {item.start_date} → {item.end_date}
          </Link>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  center: { flex: 1, textAlign: "center", marginTop: 40 },
  newLink: { fontSize: 16, color: "#0077B6", marginBottom: 16 },
  row: { fontSize: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#eee" },
  empty: { color: "#888" },
});
```

- [ ] **Step 7: Run the test to verify it passes**

Run from `apps/mobile`:
```bash
npm test -- new-trip
```
Expected: 1 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): trips list and create-trip screens"
```

---

## Task 12: Trip detail with derived days

**Files:**
- Create: `apps/mobile/app/trip/[id].tsx`, `apps/mobile/__tests__/day-label.test.ts`

**Interfaces:**
- Consumes: `useTrip` from `lib/queries`, `formatDayLabel` from `lib/days`, `useLocalSearchParams` from expo-router.
- Produces: a screen that loads a trip by id and renders its derived days, each labeled in the city's local time.

- [ ] **Step 1: Write the failing test**

`apps/mobile/__tests__/day-label.test.ts`:
```typescript
import { formatDayLabel } from "../lib/days";

test("formats a Tokyo day in Tokyo time", () => {
  const label = formatDayLabel({
    date: "2026-04-01",
    city: "Tokyo",
    country_code: "JP",
    time_zone: "Asia/Tokyo",
  });
  expect(label).toContain("Apr 1");
  expect(label).toContain("Tokyo");
});
```

- [ ] **Step 2: Run the test to verify it fails or passes**

Run from `apps/mobile`:
```bash
npm test -- day-label
```
Expected: PASS if Task 10 Step 6 (`lib/days.ts`) is in place; this test locks that behavior. (If `lib/days.ts` is missing, it FAILs on import — create it per Task 10 Step 6.)

- [ ] **Step 3: Write `apps/mobile/app/trip/[id].tsx`**

```tsx
import { useLocalSearchParams } from "expo-router";
import { ActivityIndicator, SectionList, StyleSheet, Text, View } from "react-native";

import { formatDayLabel } from "../../lib/days";
import { useTrip } from "../../lib/queries";

export default function TripDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: trip, isLoading, error } = useTrip(id);

  if (isLoading) return <ActivityIndicator style={styles.center} />;
  if (error || !trip) return <Text style={styles.center}>Couldn’t load this trip.</Text>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{trip.title}</Text>
      <SectionList
        sections={[{ title: "Days", data: trip.days }]}
        keyExtractor={(day, i) => `${day.date}-${day.city}-${i}`}
        renderSectionHeader={({ section }) => <Text style={styles.header}>{section.title}</Text>}
        renderItem={({ item }) => <Text style={styles.day}>{formatDayLabel(item)}</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  center: { flex: 1, textAlign: "center", marginTop: 40 },
  title: { fontSize: 22, fontWeight: "600", marginBottom: 12 },
  header: { fontSize: 13, color: "#555", marginTop: 12, marginBottom: 4 },
  day: { fontSize: 16, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#eee" },
});
```

- [ ] **Step 4: Run all mobile tests**

Run from `apps/mobile`:
```bash
npm test
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): trip detail with derived days in local time"
```

---

## Task 13: End-to-end verification on device

**Files:** none (verification only).

**Interfaces:** exercises the whole slice against a real backend from an Expo dev build.

- [ ] **Step 1: Start backend bound to the LAN**

Run from `apps/api` (Postgres up, migrations applied, dev user seeded):
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Set `apps/mobile/.env` `EXPO_PUBLIC_API_URL` to your machine's LAN IP (e.g. `http://192.168.1.20:8000`), not `localhost`, so the phone can reach it.

- [ ] **Step 2: Build and install the dev client on your phone**

Run from `apps/mobile`:
```bash
npx expo run:ios --device
# or, for Android: npx expo run:android --device
```
(This produces a development build, not Expo Go, per the global constraints.)

- [ ] **Step 3: Drive the flow on the phone**

1. App opens to the trips list (empty).
2. Tap **+ New trip**, enter title + a city (e.g. Tokyo, JP, Asia/Tokyo, 2026-04-01 → 2026-04-03), tap **Create trip**.
3. Land on the trip detail; confirm days 4/1, 4/2, 4/3 appear labeled in Tokyo time.
4. Go back; confirm the trip shows in the list.
5. Kill and reopen the app; confirm the trip persists (server-backed).

- [ ] **Step 4: Record the result**

Confirm the Slice 1 "done when" criterion from the spec is met. If anything fails, debug with the systematic-debugging skill before claiming completion.

- [ ] **Step 5: Final commit / branch wrap-up**

```bash
git add -A
git commit -m "chore: slice 1 end-to-end verified on device" --allow-empty
```

---

## Self-Review

**Spec coverage:**
- Monorepo scaffold (Expo + api + db) → Tasks 1, 2, 10.
- `users`/`trips`/`trip_cities` tables → Task 3 (models), Task 8 (migration).
- Dev-stub auth, one seeded user → Tasks 6, 8.
- Feature 1 (create trip w/ cities+dates, days derived per city, local time, IANA tz stored) → Tasks 4 (derive), 5 (schemas), 7 (endpoints), 11–12 (screens, local-time rendering).
- Generated TS types from OpenAPI (single source of truth) → Task 9.
- Online-only, no SQLite/offline, no real OAuth → honored (none added).
- Tests backend + mobile, TDD → Tasks 4, 6, 7, 11, 12.
- Dev build not Expo Go → Tasks 10 (expo-dev-client), 13 (run:ios/android).
- Done-when (device flow, persistence) → Task 13.

**Placeholder scan:** No TBD/TODO; every code step has complete code; commands have expected output.

**Type consistency:** Pydantic `TripRead.days: list[DayRead]`, `DayRead(date, city, country_code, time_zone)` matches `Day` dataclass fields and the `_to_trip_read` mapping (`DayRead(**vars(d))`). Mobile `Day`/`Trip` aliases pull from the generated `components["schemas"]["DayRead"]`/`["TripRead"]`, which derive from those same Pydantic models. `generate_days` name used consistently in Tasks 4 and 7. Dev token `dev-token` consistent across config, auth test, trips test, and mobile `.env`.
