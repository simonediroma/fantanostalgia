import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.api.db import get_db

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
templates = Jinja2Templates(directory=_templates_dir)

router = APIRouter(tags=["views"], default_response_class=HTMLResponse)


@router.get("/")
def home(request: Request):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, season_current, season_historic FROM league ORDER BY id"
        ).fetchall()
    leagues = [dict(r) for r in rows]
    return templates.TemplateResponse("home.html", {"request": request, "leagues": leagues})


@router.get("/lega/{league_id}/classifica")
def classifica(request: Request, league_id: int):
    with get_db() as conn:
        league_row = conn.execute(
            "SELECT id, name, season_current, season_historic FROM league WHERE id = ?",
            (league_id,),
        ).fetchone()

        if league_row is None:
            return templates.TemplateResponse(
                "home.html",
                {"request": request, "leagues": [], "error": "Lega non trovata"},
                status_code=404,
            )

        last_draw = conn.execute(
            "SELECT MAX(matchday_current) AS last FROM matchday_draw WHERE league_id = ?",
            (league_id,),
        ).fetchone()
        last_matchday = last_draw["last"] if last_draw["last"] is not None else 0

        rows = conn.execute(
            """
            SELECT m.name AS manager,
                   s.total_score_normal    AS total_normal,
                   s.total_score_nostalgia AS total_nostalgia,
                   s.rank_normal,
                   s.rank_nostalgia,
                   ms.score_normal         AS last_normal,
                   ms.score_nostalgia      AS last_nostalgia
            FROM standings s
            JOIN manager m ON m.id = s.manager_id
            LEFT JOIN matchday_score ms
                ON ms.manager_id = s.manager_id
               AND ms.league_id  = s.league_id
               AND ms.matchday   = ?
            WHERE s.league_id = ?
            """,
            (last_matchday, league_id),
        ).fetchall()

    normal = sorted(
        [{"rank": r["rank_normal"], "manager": r["manager"],
          "total": r["total_normal"], "last_matchday": r["last_normal"]} for r in rows],
        key=lambda x: x["rank"] or 9999,
    )
    nostalgia = sorted(
        [{"rank": r["rank_nostalgia"], "manager": r["manager"],
          "total": r["total_nostalgia"], "last_matchday": r["last_nostalgia"]} for r in rows],
        key=lambda x: x["rank"] or 9999,
    )

    return templates.TemplateResponse("classifica.html", {
        "request": request,
        "league": dict(league_row),
        "last_matchday": last_matchday,
        "normal": normal,
        "nostalgia": nostalgia,
    })


@router.get("/lega/{league_id}/mapping")
def mapping(request: Request, league_id: int):
    with get_db() as conn:
        league_row = conn.execute(
            "SELECT id, name, season_historic, buste_aperte FROM league WHERE id = ?",
            (league_id,),
        ).fetchone()

        if league_row is None:
            return templates.TemplateResponse(
                "home.html",
                {"request": request, "leagues": [], "error": "Lega non trovata"},
                status_code=404,
            )

        buste_aperte = bool(league_row["buste_aperte"])
        managers = []

        if buste_aperte:
            rows = conn.execute(
                """
                SELECT m.name AS manager_name, pc.name AS current_name, pc.role,
                       pc.team AS current_team, ph.name AS historic_name,
                       ph.team AS historic_team, ae.is_duplicate
                FROM alter_ego ae
                JOIN player_current  pc ON pc.id = ae.player_current_id
                JOIN player_historic ph ON ph.id = ae.player_historic_id
                LEFT JOIN manager    m  ON m.id  = pc.manager_id
                WHERE ae.league_id = ?
                ORDER BY m.name, pc.role, pc.name
                """,
                (league_id,),
            ).fetchall()

            mgr_map: dict[str, list] = {}
            for r in rows:
                key = r["manager_name"] or ""
                mgr_map.setdefault(key, []).append({
                    "current": {"name": r["current_name"], "role": r["role"], "team": r["current_team"]},
                    "historic": {"name": r["historic_name"], "team": r["historic_team"]},
                    "is_duplicate": bool(r["is_duplicate"]),
                })
            managers = [{"name": k, "players": v} for k, v in mgr_map.items()]

    return templates.TemplateResponse("mapping.html", {
        "request": request,
        "league_id": league_id,
        "league_name": league_row["name"],
        "season_historic": league_row["season_historic"],
        "buste_aperte": buste_aperte,
        "managers": managers,
    })
