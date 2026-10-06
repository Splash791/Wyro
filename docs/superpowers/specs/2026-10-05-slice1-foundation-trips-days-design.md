# Slice 1: Foundation + Trips/Days — Design

Date: 2026-10-05
Author: Tyler Quach
Status: Approved

## Context

Wyro is a mobile app for a solo traveler to plan an international trip, keep it
offline, and get good "what should I do next?" answers on the ground. The full
MVP (see `Wyro MVP Spec`) is 8 features, 7 tables, and many external
integrations — too large for a single design/implementation cycle. It is
decomposed into vertical slices, each its own spec → plan → build cycle, each
leaving the app usable:

1. **Foundation + Trips/Days** (this spec)
2. Saved list + Places
3. Day planner + Map
4. Smart import
5. Plan checker
6. Offline trip pack
7. "What's next?" + Now card + alerts

Real Google/Apple OAuth and the SQLite offline mirror are pulled out as their
own focused slices (auth before the trip test; SQLite with the offline slice).

## Goal of this slice

Launch the app on a physical phone via an Expo development build, create a trip
with cities and dates, and see days generated per city shown in local time with
each city's IANA time zone stored behind the scenes. Online-only.

## Scope

### In Slice 1

- Monorepo scaffold: Expo mobile app, FastAPI backend, Postgres + PostGIS for
  local dev via Docker Compose.
- Database tables: `users`, `trips`, `trip_cities`.
- Dev-stub auth: a single seeded dev user; the backend trusts a dev token/header.
- Feature 1 (Trips and days): create a trip with cities and dates; days are
  derived per city; everything shows in local time with the city's IANA time
  zone stored.
- Typed API client: TS types generated from the FastAPI OpenAPI schema.
- Tests: backend (pytest) and mobile (Jest + React Native Testing Library).

### Deferred to later slices

- Tables: `bookings`, `places`, `plan_items`, `pick_log`.
- Features: smart import, saved list, day planner + map, plan checker, offline
  pack, "what's next?", Now card + alerts.
- Real Sign in with Google / Apple (its own slice before the trip test).
- SQLite on-device mirror and last-write-wins sync (with the offline slice).

## Deliberate decisions

- **Auth is stubbed.** Real Google/Apple sign-in needs an Apple Developer
  account and OAuth consent setup that would block all other work. Slice 1 seeds
  one dev user and the backend trusts a dev token. Real OAuth is a focused slice
  later. It is in the MVP "done" criteria, not the "first slice" criteria.
- **No SQLite / offline in Slice 1.** The app talks to the backend online.
  Offline is Slice 6; building the sync layer now would bloat the foundation.
- **Days are derived, not stored.** The data model has no `days` table. Days are
  computed from each city's `arrive_date`/`leave_date`. `plan_items.day` (later
  slice) references these derived days. "Generate days per city" is therefore a
  pure function over `trip_cities`, not persisted state.
- **FastAPI is the single source of truth for the API contract.** It emits an
  OpenAPI schema; the mobile client's TS types are generated from it
  (`openapi-typescript`). No hand-maintained duplicate type definitions.

## Architecture & repo layout

```
wyro/
  apps/
    mobile/        # Expo + TypeScript, expo-router, TanStack Query
    api/           # FastAPI + SQLAlchemy 2.0 + Alembic, managed with uv
  packages/
    api-types/     # TS types generated from the API's OpenAPI schema
  docker-compose.yml   # Postgres + PostGIS for local dev
  docs/
```

- **Backend:** FastAPI, SQLAlchemy 2.0 (typed), Alembic migrations, Pydantic v2
  schemas, dependency-managed with `uv`. PostGIS extension enabled early even
  though Slice 1 stores no geometry yet (places arrive in Slice 2).
- **Mobile:** Expo (development build, not Expo Go), TypeScript, `expo-router`
  for navigation, TanStack Query for server state, a thin typed fetch client
  built on the generated `api-types`.

## Data model (Slice 1 subset)

All times stored as local time plus an IANA time zone, per the full spec.

- `users` — id, email, auth_provider (google/apple), import_address, created_at.
  Seeded with one dev user.
- `trips` — id, user_id (FK users), title, start_date, end_date,
  offline_downloaded_at (nullable, unused in Slice 1).
- `trip_cities` — id, trip_id (FK trips), city, country_code, time_zone (IANA),
  arrive_date, leave_date.

### Day generation (pure function)

Given a trip's `trip_cities`, produce the ordered list of days per city:

- One day per calendar date from `arrive_date` to `leave_date` inclusive.
- Each day carries its city and the city's IANA time zone so the client renders
  it in local time.
- Edge cases to cover in tests: single-day city (arrive == leave); a city
  spanning a month boundary; adjacent cities (one leaves the day the next
  arrives); cities whose date ranges are entered out of order.

## Time zone resolution

Slice 1 city entry is a free-text city name plus an IANA time zone picker,
seeded with a small city→time-zone lookup for convenience. Place-backed city
search with automatic time-zone resolution replaces this in Slice 2 (Places).
Storage format (local time + IANA tz) does not change between slices.

## API surface (Slice 1)

- `GET  /me` — the seeded dev user.
- `GET  /trips` — list the dev user's trips.
- `POST /trips` — create a trip with nested cities; returns the trip with
  derived days.
- `GET  /trips/{id}` — a trip with its cities and derived days.
- (Edit/delete endpoints only if needed by the create/view flow; keep minimal.)

Auth: every request carries a dev token; a FastAPI dependency resolves it to the
seeded user. The same dependency is where real OAuth slots in later.

## Testing

- **Backend (pytest):** day-generation function (all edge cases above); trip
  create/read endpoints; dev-auth dependency.
- **Mobile (Jest + RNTL):** trip-create form submission; day-list rendering in
  the correct local time per city.
- Follow test-driven development: write the failing test before the
  implementation.

## Done when

On a physical phone running the Expo dev build: sign in (stub) → create a trip
with two cities and dates → see days generated per city, each labeled in that
city's local time → data persists across an app restart (server-backed).

## Out of scope / explicitly not done

Group features, money, booking engines, AI itineraries, social, real OAuth,
offline, maps, import, planner, plan checker, live mode. These belong to later
slices or are out of the MVP entirely.
