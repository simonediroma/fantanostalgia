import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin_or_bearer
from backend.engine.draw import perform_draw
from backend.engine.scoring import calculate_scores

router = APIRouter(tags=["matchday"])


class RealRatingInput(BaseModel):
    player_name: str
    rating: float
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    own_goals: int = 0
    penalties_missed: int = 0
    goals_conceded: int = 0
    penalties_saved: int = 0
    minutes: int = 90


class ScoreRequest(BaseModel):
    real_ratings: Optional[list[RealRatingInput]] = None


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


@router.post("/admin/league/{league_id}/scores/{matchday}")
def calculate_matchday_scores(
    league_id: int,
    matchday: int,
    body: ScoreRequest = ScoreRequest(),
    _: str = Depends(get_current_admin_or_bearer),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        real_ratings = (
            [rr.model_dump() for rr in body.real_ratings]
            if body.real_ratings is not None
            else None
        )
        try:
            result = calculate_scores(conn, league_id, matchday, real_ratings)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {
        "matchday": result.matchday,
        "matchday_historic": result.matchday_historic,
        "scores": [
            {
                "manager": ms.manager_name,
                "score_normal": ms.score_normal,
                "score_nostalgia": ms.score_nostalgia,
            }
            for ms in result.scores
        ],
    }


@router.post("/admin/process-pending")
def process_pending_matchdays(_: str = Depends(get_current_admin_or_bearer)):
    """Elabora tutte le giornate caricate ma non ancora sortegiate/calcolate, su tutte le leghe."""
    processed = []
    errors = []

    with get_db() as conn:
        pending = conn.execute(
            """
            SELECT DISTINCT l.league_id, l.matchday
            FROM lineup l
            LEFT JOIN matchday_draw md
                ON md.league_id = l.league_id AND md.matchday_current = l.matchday
            WHERE md.matchday_current IS NULL
            ORDER BY l.league_id, l.matchday
            """
        ).fetchall()

    for row in pending:
        league_id, matchday = row["league_id"], row["matchday"]
        try:
            with get_db() as conn:
                draw = perform_draw(conn, league_id, matchday)
                scores = calculate_scores(conn, league_id, matchday)
            processed.append({
                "league_id": league_id,
                "matchday_current": draw.matchday_current,
                "matchday_historic": draw.matchday_historic,
                "scores_count": len(scores.scores),
            })
        except Exception as e:
            errors.append({"league_id": league_id, "matchday": matchday, "error": str(e)})

    return {"processed": processed, "errors": errors}


@router.get("/league/{league_id}/scores/{matchday}")
def get_matchday_scores(league_id: int, matchday: int):
    with get_db() as conn:
        _require_league(conn, league_id)
        rows = conn.execute(
            """
            SELECT m.name AS manager, ms.score_normal, ms.score_nostalgia, ms.calculated_at
            FROM matchday_score ms
            JOIN manager m ON m.id = ms.manager_id
            WHERE ms.league_id = ? AND ms.matchday = ?
            ORDER BY ms.score_nostalgia DESC
            """,
            (league_id, matchday),
        ).fetchall()
    return [dict(r) for r in rows]
