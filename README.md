# Wyro

Solo-traveler trip-planning app. Monorepo: `apps/api` (FastAPI), `apps/mobile`
(Expo), `packages/api-types` (generated TS types).

## Local dev
1. `docker compose up -d` — start Postgres/PostGIS.
2. Backend: see `apps/api/README` — `uv run uvicorn app.main:app --reload`.
3. Mobile: see `apps/mobile` — `npm run start`.

Built in vertical slices; see `docs/superpowers/specs/`.
