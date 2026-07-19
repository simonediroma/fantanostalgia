import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.api.db import init_db
from backend.api.routers import auth, coach, granpremio, historic, inspect, league, lineups, mapping, market, matchday, players, standings, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FantaNostalgia API", lifespan=lifespan)


@app.middleware("http")
async def no_cache_static_assets(request, call_next):
    """Forza la revalidazione per JS/CSS delle SPA (admin/coach) e per /shared.
    Questi file non hanno cache-busting nell'URL (stesso path ad ogni deploy),
    quindi senza Cache-Control esplicito un browser può continuare a servire
    una versione in cache dopo un aggiornamento del codice."""
    response = await call_next(request)
    path = request.url.path
    if path.startswith(("/admin/js/", "/admin/css/", "/coach/js/", "/coach/css/", "/shared/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

_shared_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "shared")
if os.path.isdir(_shared_dir):
    app.mount("/shared", StaticFiles(directory=_shared_dir), name="shared")

_admin_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "admin")
if os.path.isdir(_admin_dir):
    app.mount("/admin/css", StaticFiles(directory=os.path.join(_admin_dir, "css")), name="admin-css")
    app.mount("/admin/js", StaticFiles(directory=os.path.join(_admin_dir, "js")), name="admin-js")

_coach_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "coach")
if os.path.isdir(_coach_dir):
    app.mount("/coach/js", StaticFiles(directory=os.path.join(_coach_dir, "js")), name="coach-js")
    app.mount("/coach/css", StaticFiles(directory=os.path.join(_coach_dir, "css")), name="coach-css")

_webscraper_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "webscraper")
if os.path.isdir(_webscraper_dir):
    app.mount("/webscraper", StaticFiles(directory=_webscraper_dir, html=True), name="webscraper")

app.include_router(views.router)
app.include_router(auth.router)
app.include_router(coach.router)
app.include_router(league.router)
app.include_router(players.router)
app.include_router(mapping.router)
app.include_router(market.router)
app.include_router(matchday.router)
app.include_router(lineups.router)
app.include_router(standings.router)
app.include_router(historic.router)
app.include_router(granpremio.router)
app.include_router(inspect.router)


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
