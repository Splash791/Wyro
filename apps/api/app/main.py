from fastapi import FastAPI

from app.routers import trips

app = FastAPI(title="Wyro API", version="0.1.0")
app.include_router(trips.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
