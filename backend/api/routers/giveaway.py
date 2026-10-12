from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.db import get_db
from backend.api.notifications import enqueue_email
from backend.api.routers.auth import get_current_admin
from backend.engine.giveaway import SEQUENCE, check_preconditions, get_rules, plan_giveaway, run_giveaway

router = APIRouter(tags=["giveaway"])


def _require_league(conn, league_id: int) -> None:
    row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


class GiveawayRule(BaseModel):
    role: str
    min_avg: float | None = None
    max_avg: float | None = None
    min_appearances: int = 0


@router.get("/admin/giveaway/rules")
def list_rules(_: str = Depends(get_current_admin)):
    with get_db() as conn:
        rules = get_rules(conn)
    return [rules[r] for r in SEQUENCE]


@router.put("/admin/giveaway/rules")
def update_rules(body: list[GiveawayRule], _: str = Depends(get_current_admin)):
    for rule in body:
        if rule.role not in SEQUENCE:
            raise HTTPException(status_code=400, detail=f"Ruolo non valido: {rule.role}")
        if rule.min_appearances < 0:
            raise HTTPException(status_code=400, detail=f"{rule.role}: le presenze non possono essere negative")
        if rule.min_avg is not None and rule.max_avg is not None and rule.min_avg > rule.max_avg:
            raise HTTPException(status_code=400, detail=f"{rule.role}: la media minima supera la massima")
    with get_db() as conn:
        for rule in body:
            conn.execute(
                "UPDATE giveaway_rule SET min_avg = ?, max_avg = ?, min_appearances = ? WHERE role = ?",
                (rule.min_avg, rule.max_avg, rule.min_appearances, rule.role),
            )
        rules = get_rules(conn)
    return [rules[r] for r in SEQUENCE]


def _awards(conn, league_id: int, matchday: int | None = None) -> list[dict]:
    params: list = [league_id]
    where = ""
    if matchday is not None:
        where = " AND g.matchday = ?"
        params.append(matchday)
    rows = conn.execute(
        f"""
        SELECT g.matchday, g.role, g.in_band, g.manager_id,
               COALESCE(m.team_name, m.name) AS manager_name,
               ph.id AS player_historic_id, ph.name, ph.team, ph.season
        FROM matchday_giveaway g
        JOIN manager m ON m.id = g.manager_id
        JOIN player_historic ph ON ph.id = g.player_historic_id
        WHERE g.league_id = ?{where}
        ORDER BY g.matchday, g.id
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/admin/league/{league_id}/giveaway/{matchday}")
def preview(league_id: int, matchday: int, _: str = Depends(get_current_admin)):
    with get_db() as conn:
        _require_league(conn, league_id)
        awards = _awards(conn, league_id, matchday)
        if awards:
            return {"done": True, "awards": awards}
        blocker = None
        try:
            check_preconditions(conn, league_id, matchday)
        except ValueError as e:
            blocker = str(e)
        plan = plan_giveaway(conn, league_id)
        if plan is None:
            return {"done": False, "blocker": blocker or "Nessuna squadra ha posti liberi: le assegnazioni sono concluse",
                    "role": None}
        names = {
            r["id"]: r["name"] for r in conn.execute(
                "SELECT id, COALESCE(team_name, name) AS name FROM manager WHERE league_id = ?",
                (league_id,),
            ).fetchall()
        }
    return {
        "done": False,
        "blocker": blocker,
        "role": plan["role"],
        "managers": [names[m] for m in plan["manager_ids"]],
        "in_band": len(plan["in_band"]),
        "out_of_band": len(plan["out_of_band"]),
    }


@router.post("/admin/league/{league_id}/giveaway/{matchday}")
def run(league_id: int, matchday: int, _: str = Depends(get_current_admin)):
    with get_db() as conn:
        _require_league(conn, league_id)
        try:
            run_giveaway(conn, league_id, matchday)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        league = conn.execute("SELECT name FROM league WHERE id = ?", (league_id,)).fetchone()
        awards = _awards(conn, league_id, matchday)
        for a in awards:
            mgr = conn.execute(
                "SELECT m.name, u.email FROM manager m JOIN user u ON u.id = m.user_id WHERE m.id = ?",
                (a["manager_id"],),
            ).fetchone()
            if mgr is not None:
                enqueue_email(conn, "giveaway_assigned", mgr["email"], {
                    "name": mgr["name"], "league_name": league["name"], "league_id": league_id,
                    "player_name": a["name"], "matchday": matchday,
                })
    return {"done": True, "awards": awards}


@router.get("/league/{league_id}/giveaway")
def list_giveaways(league_id: int):
    with get_db() as conn:
        _require_league(conn, league_id)
        return _awards(conn, league_id)
