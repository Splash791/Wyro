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
