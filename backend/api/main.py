from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.db import init_db
from backend.api.routers import auth, league, players


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FantaNostalgia API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(league.router)
app.include_router(players.router)


@app.get("/health")
def health():
    return {"status": "ok"}
