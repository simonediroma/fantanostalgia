from fastapi import APIRouter, Depends, HTTPException

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin
from backend.engine.mapping import generate_mapping

router = APIRouter(tags=["mapping"])


def _require_league(conn, league_id: int):
    row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


@router.post("/admin/league/{league_id}/mapping/generate")
def generate_alter_ego_mapping(
    league_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)

        has_current = conn.execute(
            "SELECT 1 FROM player_current WHERE league_id = ? LIMIT 1", (league_id,)
        ).fetchone()
        if not has_current:
            raise HTTPException(
                status_code=400,
                detail="Listone non caricato: nessun giocatore attuale trovato per questa lega",
            )

        league = conn.execute(
            "SELECT season_historic FROM league WHERE id = ?", (league_id,)
        ).fetchone()
        has_historic = conn.execute(
            "SELECT 1 FROM player_historic WHERE season = ? LIMIT 1",
            (league["season_historic"],),
        ).fetchone()
        if not has_historic:
            raise HTTPException(
                status_code=400,
                detail=f"Nessun giocatore storico trovato per la stagione {league['season_historic']}",
            )

        try:
            result = generate_mapping(conn, league_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {
        "mapped": result.mapped,
        "duplicates": result.duplicates,
        "coverage_by_manager": result.coverage_by_manager,
    }


def _build_public_mapping(conn, league_id: int) -> dict:
    league = conn.execute(
        "SELECT name, season_historic, buste_aperte_at FROM league WHERE id = ?", (league_id,)
    ).fetchone()

    rows = conn.execute(
        """
        SELECT
            m.name   AS manager_name,
            pc.name  AS current_name,
            pc.role,
            pc.team  AS current_team,
            ph.name  AS historic_name,
            ph.team  AS historic_team,
            ph.season AS historic_season,
            ae.is_duplicate
        FROM alter_ego ae
        JOIN player_current  pc ON pc.id = ae.player_current_id
        JOIN player_historic ph ON ph.id = ae.player_historic_id
        LEFT JOIN manager    m  ON m.id  = pc.manager_id
        WHERE ae.league_id = ?
        ORDER BY m.name, pc.role, pc.name
        """,
        (league_id,),
    ).fetchall()

    managers: dict[str, list] = {}
    for r in rows:
        key = r["manager_name"] or ""
        managers.setdefault(key, []).append({
            "current": {"name": r["current_name"], "role": r["role"], "team": r["current_team"]},
            "historic": {
                "name": r["historic_name"],
                "role": r["role"],
                "team": r["historic_team"],
                "season": r["historic_season"],
            },
            "is_duplicate": bool(r["is_duplicate"]),
        })

    return {
        "league": league["name"],
        "season_historic": league["season_historic"],
        "buste_aperte_at": league["buste_aperte_at"],
        "managers": [{"name": name, "players": players} for name, players in managers.items()],
    }


@router.post("/admin/league/{league_id}/mapping/reveal")
def reveal_mapping(
    league_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)

        league = conn.execute(
            "SELECT buste_aperte FROM league WHERE id = ?", (league_id,)
        ).fetchone()
        if league["buste_aperte"] == 1:
            raise HTTPException(status_code=400, detail="Buste già aperte")

        conn.execute(
            "UPDATE league SET buste_aperte = 1, buste_aperte_at = CURRENT_TIMESTAMP WHERE id = ?",
            (league_id,),
        )
        result = _build_public_mapping(conn, league_id)

    return result


@router.get("/league/{league_id}/mapping")
def get_public_mapping(league_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, buste_aperte FROM league WHERE id = ?", (league_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Lega non trovata")
        if row["buste_aperte"] == 0:
            raise HTTPException(status_code=404, detail="Le buste non sono ancora state aperte")

        result = _build_public_mapping(conn, league_id)

    return result


@router.get("/admin/league/{league_id}/mapping")
def get_mapping(
    league_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)

        rows = conn.execute(
            """
            SELECT
                ae.id,
                ae.player_current_id,
                pc.name  AS player_current_name,
                pc.role  AS role,
                pc.team  AS team_current,
                ae.player_historic_id,
                ph.name  AS player_historic_name,
                ph.team  AS team_historic,
                ae.is_duplicate,
                pc.manager_id,
                m.name   AS manager_name
            FROM alter_ego ae
            JOIN player_current  pc ON pc.id = ae.player_current_id
            JOIN player_historic ph ON ph.id = ae.player_historic_id
            LEFT JOIN manager    m  ON m.id  = pc.manager_id
            WHERE ae.league_id = ?
            ORDER BY pc.role, pc.name
            """,
            (league_id,),
        ).fetchall()

    return [dict(r) for r in rows]
