from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.db import get_db
from backend.api.notifications import enqueue_email
from backend.api.routers.auth import get_current_admin
from backend.engine.granpremio import CRITERIA, free_historic_players, resolve_gran_premio

router = APIRouter(tags=["granpremio"])

MAX_PER_MATCHDAY = 2


def _require_league(conn, league_id: int) -> None:
    row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


@router.get("/admin/league/{league_id}/granpremio/free-players")
def list_free_players(
    league_id: int,
    role: str | None = None,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        try:
            return free_historic_players(conn, league_id, role)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


class CreateGranPremio(BaseModel):
    matchday: int
    criterion: str
    prize_player_historic_id: int


@router.post("/admin/league/{league_id}/granpremio")
def create_gran_premio(
    league_id: int,
    body: CreateGranPremio,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)

        if body.criterion not in CRITERIA:
            raise HTTPException(status_code=400, detail=f"Criterio non valido: {body.criterion}")

        count = conn.execute(
            "SELECT COUNT(*) AS c FROM gran_premio WHERE league_id = ? AND matchday = ?",
            (league_id, body.matchday),
        ).fetchone()["c"]
        if count >= MAX_PER_MATCHDAY:
            raise HTTPException(
                status_code=400,
                detail=f"Massimo {MAX_PER_MATCHDAY} Gran Premi per giornata",
            )

        free_ids = {p["id"] for p in free_historic_players(conn, league_id)}
        if body.prize_player_historic_id not in free_ids:
            raise HTTPException(
                status_code=400,
                detail="Il giocatore in palio non è disponibile (non libero)",
            )

        cur = conn.execute(
            "INSERT INTO gran_premio (league_id, matchday, criterion, prize_player_historic_id)"
            " VALUES (?, ?, ?, ?)",
            (league_id, body.matchday, body.criterion, body.prize_player_historic_id),
        )
        gp_id = cur.lastrowid

    return {"id": gp_id, "matchday": body.matchday, "criterion": body.criterion}


@router.post("/admin/league/{league_id}/granpremio/{gp_id}/resolve")
def resolve(
    league_id: int,
    gp_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        gp = conn.execute(
            "SELECT league_id, prize_player_historic_id FROM gran_premio WHERE id = ?", (gp_id,)
        ).fetchone()
        if gp is None or gp["league_id"] != league_id:
            raise HTTPException(status_code=404, detail="Gran Premio non trovato")
        try:
            winner_id = resolve_gran_premio(conn, gp_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        winner = conn.execute(
            "SELECT name, user_id FROM manager WHERE id = ?", (winner_id,)
        ).fetchone()

        if winner["user_id"] is not None:
            league = conn.execute("SELECT name FROM league WHERE id = ?", (league_id,)).fetchone()
            prize = conn.execute(
                "SELECT name FROM player_historic WHERE id = ?", (gp["prize_player_historic_id"],)
            ).fetchone()
            winner_user = conn.execute(
                "SELECT email FROM user WHERE id = ?", (winner["user_id"],)
            ).fetchone()
            enqueue_email(conn, "gran_premio_won", winner_user["email"], {
                "name": winner["name"], "league_name": league["name"], "league_id": league_id,
                "prize_player_name": prize["name"],
            })

    return {
        "id": gp_id,
        "winner_manager_id": winner_id,
        "winner": winner["name"] if winner else None,
    }


@router.get("/league/{league_id}/granpremio")
def list_gran_premi(league_id: int):
    with get_db() as conn:
        _require_league(conn, league_id)
        rows = conn.execute(
            """
            SELECT gp.id, gp.matchday, gp.criterion, gp.status,
                   gp.prize_player_historic_id,
                   ph.name AS prize_name, ph.role AS prize_role,
                   ph.team AS prize_team, ph.season AS prize_season,
                   gp.winner_manager_id, m.name AS winner_name
            FROM gran_premio gp
            JOIN player_historic ph ON ph.id = gp.prize_player_historic_id
            LEFT JOIN manager m ON m.id = gp.winner_manager_id
            WHERE gp.league_id = ?
            ORDER BY gp.matchday, gp.id
            """,
            (league_id,),
        ).fetchall()
    return [dict(r) for r in rows]
