import os
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from backend.api.db import get_db
from backend.api.routers.standings import _compute_h2h, _score_to_goals

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
templates = Jinja2Templates(directory=_templates_dir)

_coach_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "coach")

router = APIRouter(tags=["views"], default_response_class=HTMLResponse)

_GP_CRITERIA_LABELS = {
    "best_score": "Miglior punteggio",
    "worst_defense": "Peggior difesa",
    "best_player": "Miglior giocatore",
    "worst_player": "Peggior giocatore",
}


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

        draw_row = conn.execute(
            """SELECT matchday_current, matchday_historic, drawn_at
               FROM matchday_draw
               WHERE league_id = ?
               ORDER BY matchday_current DESC
               LIMIT 1""",
            (league_id,),
        ).fetchone()
        last_matchday = draw_row["matchday_current"] if draw_row else 0

        last_draw = None
        if draw_row:
            drawn_at_fmt = ""
            if draw_row["drawn_at"]:
                try:
                    drawn_at_fmt = datetime.strptime(
                        draw_row["drawn_at"][:10], "%Y-%m-%d"
                    ).strftime("%d/%m/%Y")
                except ValueError:
                    drawn_at_fmt = draw_row["drawn_at"][:10]
            last_draw = {
                "matchday_current": draw_row["matchday_current"],
                "matchday_historic": draw_row["matchday_historic"],
                "drawn_at_fmt": drawn_at_fmt,
            }

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

        all_draw_rows = conn.execute(
            """SELECT matchday_current, matchday_historic, drawn_at
               FROM matchday_draw WHERE league_id = ? ORDER BY matchday_current DESC""",
            (league_id,),
        ).fetchall()

        h2h_matches = conn.execute(
            """
            SELECT h.matchday,
                   mh.name AS home_manager,
                   ma.name AS away_manager,
                   ms_h.score_nostalgia AS home_score,
                   ms_a.score_nostalgia AS away_score
            FROM h2h_match h
            JOIN manager mh ON mh.id = h.manager_home_id
            JOIN manager ma ON ma.id = h.manager_away_id
            LEFT JOIN matchday_score ms_h
                ON ms_h.league_id = h.league_id
               AND ms_h.matchday  = h.matchday
               AND ms_h.manager_id = h.manager_home_id
            LEFT JOIN matchday_score ms_a
                ON ms_a.league_id = h.league_id
               AND ms_a.matchday  = h.matchday
               AND ms_a.manager_id = h.manager_away_id
            WHERE h.league_id = ?
            ORDER BY h.matchday
            """,
            (league_id,),
        ).fetchall()
        h2h = _compute_h2h([dict(m) for m in h2h_matches])

    all_draws = []
    for r in all_draw_rows:
        drawn_at_fmt = ""
        if r["drawn_at"]:
            try:
                drawn_at_fmt = datetime.strptime(r["drawn_at"][:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                drawn_at_fmt = r["drawn_at"][:10]
        all_draws.append({
            "matchday_current": r["matchday_current"],
            "matchday_historic": r["matchday_historic"],
            "drawn_at_fmt": drawn_at_fmt,
        })

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
        "last_draw": last_draw,
        "normal": normal,
        "nostalgia": nostalgia,
        "h2h": h2h,
        "all_draws": all_draws,
    })


@router.get("/coach/login", include_in_schema=False)
@router.get("/coach/join", include_in_schema=False)
def coach_login(request: Request):
    p = os.path.join(_coach_dir, "login.html")
    if os.path.isfile(p):
        return FileResponse(p, media_type="text/html")
    return Response("Coach login not available", status_code=404)


@router.get("/coach/", include_in_schema=False)
@router.get("/coach", include_in_schema=False)
def coach_home(request: Request):
    p = os.path.join(_coach_dir, "index.html")
    if os.path.isfile(p):
        return FileResponse(p, media_type="text/html")
    return Response("Coach home not available", status_code=404)


@router.get("/coach/lega/{league_id}", include_in_schema=False)
def coach_rosa(request: Request, league_id: int):
    p = os.path.join(_coach_dir, "rosa.html")
    if os.path.isfile(p):
        return FileResponse(p, media_type="text/html")
    return Response("Coach rosa not available", status_code=404)


@router.get("/coach/lega/{league_id}/punteggi", include_in_schema=False)
def coach_punteggi(request: Request, league_id: int):
    p = os.path.join(_coach_dir, "punteggi.html")
    if os.path.isfile(p):
        return FileResponse(p, media_type="text/html")
    return Response("Coach punteggi not available", status_code=404)


@router.get("/api/lega/{league_id}/calendario/{matchday}")
def calendario_dati(league_id: int, matchday: int):
    """JSON endpoint: h2h matches for a matchday with per-player score breakdown."""
    with get_db() as conn:
        draw_row = conn.execute(
            "SELECT matchday_current, matchday_historic FROM matchday_draw"
            " WHERE league_id = ? AND matchday_current = ?",
            (league_id, matchday),
        ).fetchone()
        if draw_row is None:
            return JSONResponse({"error": "Giornata non trovata"}, status_code=404)

        matchday_historic = draw_row["matchday_historic"]

        h2h_rows = conn.execute(
            """
            SELECT mh.name AS home_manager, ma.name AS away_manager,
                   ms_h.score_nostalgia AS home_score,
                   ms_a.score_nostalgia AS away_score
            FROM h2h_match h
            JOIN manager mh ON mh.id = h.manager_home_id
            JOIN manager ma ON ma.id = h.manager_away_id
            LEFT JOIN matchday_score ms_h
                ON ms_h.league_id = h.league_id AND ms_h.matchday = h.matchday
               AND ms_h.manager_id = h.manager_home_id
            LEFT JOIN matchday_score ms_a
                ON ms_a.league_id = h.league_id AND ms_a.matchday = h.matchday
               AND ms_a.manager_id = h.manager_away_id
            WHERE h.league_id = ? AND h.matchday = ?
            """,
            (league_id, matchday),
        ).fetchall()

        lineup_rows = conn.execute(
            """
            SELECT m.name AS manager_name, pc.name AS player_name, pc.role,
                   pc.team AS current_team, l.is_starter,
                   l.score_no_bonus, l.score_bonus,
                   ph.name AS alter_ego_name, ph.team AS alter_ego_team,
                   hr.rating, hr.goals, hr.assists, hr.yellow_cards, hr.red_cards,
                   hr.own_goals, hr.penalties_missed, hr.goals_conceded,
                   hr.minutes, hr.source
            FROM lineup l
            JOIN player_current pc ON pc.id = l.player_current_id
            JOIN manager m ON m.id = l.manager_id
            LEFT JOIN alter_ego ae ON ae.player_current_id = pc.id AND ae.league_id = l.league_id
            LEFT JOIN player_historic ph ON ph.id = ae.player_historic_id
            LEFT JOIN historic_rating hr
                ON hr.player_historic_id = ae.player_historic_id AND hr.matchday = ?
            WHERE l.league_id = ? AND l.matchday = ?
            ORDER BY m.name, l.is_starter DESC,
                     CASE pc.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                     pc.name
            """,
            (matchday_historic, league_id, matchday),
        ).fetchall()

    mgr_map: dict[str, dict] = {}
    for r in lineup_rows:
        key = r["manager_name"]
        if key not in mgr_map:
            mgr_map[key] = {"starters": [], "bench": []}
        ns_score = None
        if r["rating"] is not None:
            ns_score = float(r["rating"])
        elif r["alter_ego_name"]:
            ns_score = 6.0
        entry = {
            "role": r["role"],
            "player_name": r["player_name"],
            "current_team": r["current_team"],
            "alter_ego_name": r["alter_ego_name"],
            "alter_ego_team": r["alter_ego_team"],
            "score_no_bonus": r["score_no_bonus"],
            "score_bonus": r["score_bonus"],
            "ns_score": round(ns_score, 1) if ns_score is not None else None,
        }
        if r["is_starter"]:
            mgr_map[key]["starters"].append(entry)
        else:
            mgr_map[key]["bench"].append(entry)

    matches = []
    for h in h2h_rows:
        hm = h["home_manager"]
        am = h["away_manager"]
        hs = h["home_score"] or 0.0
        as_ = h["away_score"] or 0.0
        matches.append({
            "home_manager": hm,
            "away_manager": am,
            "home_score": hs,
            "away_score": as_,
            "home_goals": _score_to_goals(hs),
            "away_goals": _score_to_goals(as_),
            "home_players": mgr_map.get(hm, {"starters": [], "bench": []}),
            "away_players": mgr_map.get(am, {"starters": [], "bench": []}),
        })

    return JSONResponse({
        "matchday": matchday,
        "matchday_historic": matchday_historic,
        "matches": matches,
    })


@router.get("/lega/{league_id}/giornata/{matchday}")
def giornata(request: Request, league_id: int, matchday: int):
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

        draw_row = conn.execute(
            "SELECT matchday_current, matchday_historic, drawn_at FROM matchday_draw"
            " WHERE league_id = ? AND matchday_current = ?",
            (league_id, matchday),
        ).fetchone()
        if draw_row is None:
            return templates.TemplateResponse(
                "home.html",
                {"request": request, "leagues": [], "error": "Giornata non trovata"},
                status_code=404,
            )

        drawn_at_fmt = ""
        if draw_row["drawn_at"]:
            try:
                drawn_at_fmt = datetime.strptime(
                    draw_row["drawn_at"][:10], "%Y-%m-%d"
                ).strftime("%d/%m/%Y")
            except ValueError:
                drawn_at_fmt = draw_row["drawn_at"][:10]

        matchday_historic = draw_row["matchday_historic"]

        score_rows = conn.execute(
            """SELECT m.name AS manager_name, ms.score_normal, ms.score_nostalgia
               FROM matchday_score ms
               JOIN manager m ON m.id = ms.manager_id
               WHERE ms.league_id = ? AND ms.matchday = ?
               ORDER BY ms.score_nostalgia DESC""",
            (league_id, matchday),
        ).fetchall()
        scores = [dict(r) for r in score_rows]

        lineup_rows = conn.execute(
            """
            SELECT m.name AS manager_name, pc.name AS player_name, pc.role,
                   pc.team AS current_team, l.is_starter,
                   ph.name AS alter_ego_name, ph.team AS alter_ego_team,
                   hr.rating, hr.goals, hr.assists, hr.yellow_cards, hr.red_cards,
                   hr.own_goals, hr.penalties_missed, hr.goals_conceded,
                   hr.minutes, hr.source
            FROM lineup l
            JOIN player_current pc ON pc.id = l.player_current_id
            JOIN manager m ON m.id = l.manager_id
            LEFT JOIN alter_ego ae ON ae.player_current_id = pc.id AND ae.league_id = l.league_id
            LEFT JOIN player_historic ph ON ph.id = ae.player_historic_id
            LEFT JOIN historic_rating hr
                ON hr.player_historic_id = ae.player_historic_id AND hr.matchday = ?
            WHERE l.league_id = ? AND l.matchday = ?
            ORDER BY m.name, l.is_starter DESC,
                     CASE pc.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                     pc.name
            """,
            (matchday_historic, league_id, matchday),
        ).fetchall()

        all_draw_rows = conn.execute(
            "SELECT matchday_current FROM matchday_draw WHERE league_id = ? ORDER BY matchday_current",
            (league_id,),
        ).fetchall()

        gp_rows = conn.execute(
            """
            SELECT gp.criterion, gp.status,
                   ph.name AS prize_name, ph.role AS prize_role, ph.team AS prize_team,
                   m.name AS winner_name
            FROM gran_premio gp
            JOIN player_historic ph ON ph.id = gp.prize_player_historic_id
            LEFT JOIN manager m ON m.id = gp.winner_manager_id
            WHERE gp.league_id = ? AND gp.matchday = ?
            ORDER BY gp.id
            """,
            (league_id, matchday),
        ).fetchall()

    gran_premi = [{
        "criterion_label": _GP_CRITERIA_LABELS.get(r["criterion"], r["criterion"]),
        "status": r["status"],
        "prize_name": r["prize_name"],
        "prize_role": r["prize_role"],
        "prize_team": r["prize_team"],
        "winner_name": r["winner_name"],
    } for r in gp_rows]

    mgr_map: dict[str, dict] = {}
    for r in lineup_rows:
        key = r["manager_name"]
        if key not in mgr_map:
            mgr_map[key] = {"starters": [], "bench": []}
        ns_score = None
        if r["rating"] is not None:
            ns_score = float(r["rating"])
        elif r["alter_ego_name"]:
            ns_score = 6.0  # sv o non trovato

        entry = {
            "player_name": r["player_name"],
            "role": r["role"],
            "current_team": r["current_team"],
            "alter_ego_name": r["alter_ego_name"],
            "alter_ego_team": r["alter_ego_team"],
            "rating": r["rating"],
            "ns_score": round(ns_score, 1) if ns_score is not None else None,
        }
        if r["is_starter"]:
            mgr_map[key]["starters"].append(entry)
        else:
            mgr_map[key]["bench"].append(entry)

    managers = [{"name": k, **v} for k, v in mgr_map.items()]
    all_matchdays = [r["matchday_current"] for r in all_draw_rows]

    return templates.TemplateResponse("giornata.html", {
        "request": request,
        "league": dict(league_row),
        "matchday": matchday,
        "matchday_historic": matchday_historic,
        "drawn_at_fmt": drawn_at_fmt,
        "scores": scores,
        "managers": managers,
        "gran_premi": gran_premi,
        "all_matchdays": all_matchdays,
    })


@router.get("/lega/{league_id}/statistiche")
def statistiche(request: Request, league_id: int):
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

        flat_rows = conn.execute(
            """
            SELECT
                pc.id AS pc_id, pc.name AS player_name, pc.role, pc.team AS current_team,
                m.name AS manager_name,
                ph.name AS alter_ego_name, ph.team AS alter_ego_team,
                hr.rating, hr.goals, hr.assists, hr.yellow_cards, hr.red_cards,
                hr.own_goals, hr.penalties_missed, hr.goals_conceded, hr.minutes, hr.source
            FROM player_current pc
            JOIN manager m ON m.id = pc.manager_id
            JOIN alter_ego ae ON ae.player_current_id = pc.id AND ae.league_id = ?
            JOIN player_historic ph ON ph.id = ae.player_historic_id
            JOIN lineup l ON l.player_current_id = pc.id AND l.league_id = ? AND l.is_starter = 1
            JOIN matchday_draw md ON md.league_id = ? AND md.matchday_current = l.matchday
            JOIN historic_rating hr ON hr.player_historic_id = ph.id AND hr.matchday = md.matchday_historic
            WHERE pc.league_id = ?
            ORDER BY pc.id
            """,
            (league_id, league_id, league_id, league_id),
        ).fetchall()

        archivio_rows = conn.execute(
            """
            SELECT ph.name, ph.role, ph.team,
                   COUNT(hr.matchday) AS n,
                   ROUND(AVG(hr.rating), 2) AS avg_rating,
                   SUM(hr.goals) AS goals,
                   SUM(hr.assists) AS assists
            FROM player_historic ph
            JOIN historic_rating hr ON hr.player_historic_id = ph.id
            WHERE ph.season = ?
            GROUP BY ph.id
            HAVING n >= 5
            ORDER BY avg_rating DESC
            LIMIT 50
            """,
            (league_row["season_historic"],),
        ).fetchall()

    player_stats: dict[int, dict] = {}
    for r in flat_rows:
        pid = r["pc_id"]
        if pid not in player_stats:
            player_stats[pid] = {
                "player_name": r["player_name"],
                "role": r["role"],
                "current_team": r["current_team"],
                "manager_name": r["manager_name"],
                "alter_ego_name": r["alter_ego_name"],
                "alter_ego_team": r["alter_ego_team"],
                "n": 0, "sum_rating": 0.0, "total_ns": 0.0,
                "goals": 0, "assists": 0, "yellows": 0, "reds": 0,
            }
        s = player_stats[pid]
        if r["rating"] is not None:
            s["n"] += 1
            s["sum_rating"] += r["rating"]
            # hr.rating is always the final score (archive: real vote with bonuses;
            # synthetic: compute_rating() already includes goal/win/card bonuses).
            ns = float(r["rating"])
            s["total_ns"] += ns
            s["goals"] += r["goals"] or 0
            s["assists"] += r["assists"] or 0
            s["yellows"] += r["yellow_cards"] or 0
            s["reds"] += r["red_cards"] or 0

    players_list = []
    for s in player_stats.values():
        players_list.append({
            **s,
            "avg_rating": round(s["sum_rating"] / s["n"], 2) if s["n"] > 0 else None,
            "total_ns": round(s["total_ns"], 1),
        })

    by_rating = sorted(players_list, key=lambda x: x["avg_rating"] or 0, reverse=True)
    by_goals = sorted(players_list, key=lambda x: (x["goals"], x["assists"]), reverse=True)
    archivio = [dict(r) for r in archivio_rows]

    return templates.TemplateResponse("statistiche.html", {
        "request": request,
        "league": dict(league_row),
        "by_rating": by_rating,
        "by_goals": by_goals,
        "archivio": archivio,
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
