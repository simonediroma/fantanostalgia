import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.api.db import init_db
from backend.api.routers import auth, historic, league, lineups, mapping, matchday, players, standings, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FantaNostalgia API", lifespan=lifespan)

_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

_admin_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "admin")
if os.path.isdir(_admin_dir):
    app.mount("/admin/css", StaticFiles(directory=os.path.join(_admin_dir, "css")), name="admin-css")
    app.mount("/admin/js", StaticFiles(directory=os.path.join(_admin_dir, "js")), name="admin-js")

app.include_router(views.router)
app.include_router(auth.router)
app.include_router(league.router)
app.include_router(players.router)
app.include_router(mapping.router)
app.include_router(matchday.router)
app.include_router(lineups.router)
app.include_router(standings.router)
app.include_router(historic.router)


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
def admin_panel():
    index = os.path.join(_admin_dir, "index.html")
    if os.path.isfile(index):
        return FileResponse(index, media_type="text/html")
    return Response("Admin not available", status_code=404)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health():
    return {"status": "ok"}
