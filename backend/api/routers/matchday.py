import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin_or_bearer
from backend.engine.draw import perform_draw

router = APIRouter(tags=["matchday"])


def _require_league(conn: sqlite3.Connection, league_id: int) -> None:
    row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


@router.post("/admin/league/{league_id}/draw/{matchday_current}")
def draw_matchday(
    league_id: int,
    matchday_current: int,
    _: str = Depends(get_current_admin_or_bearer),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        try:
            result = perform_draw(conn, league_id, matchday_current)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {
        "matchday_current": result.matchday_current,
        "matchday_historic": result.matchday_historic,
        "cycle": result.cycle,
        "drawn_at": result.drawn_at,
    }


@router.get("/league/{league_id}/draws")
def list_draws(league_id: int):
    with get_db() as conn:
        _require_league(conn, league_id)
        rows = conn.execute(
            "SELECT matchday_current, matchday_historic, cycle, drawn_at"
            " FROM matchday_draw WHERE league_id = ?"
            " ORDER BY matchday_current",
            (league_id,),
        ).fetchall()
    return [dict(r) for r in rows]
