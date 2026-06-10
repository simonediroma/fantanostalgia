import sqlite3

from fastapi import APIRouter, HTTPException

from backend.api.db import get_db

router = APIRouter(tags=["standings"])


def _require_league(conn: sqlite3.Connection, league_id: int) -> dict:
    row = conn.execute("SELECT * FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")
    return dict(row)


@router.get("/league/{league_id}/standings")
def get_standings(league_id: int):
    with get_db() as conn:
        league = _require_league(conn, league_id)

        last_draw = conn.execute(
            "SELECT MAX(matchday_current) AS last FROM matchday_draw WHERE league_id = ?",
            (league_id,),
        ).fetchone()
        last_matchday = last_draw["last"] if last_draw["last"] is not None else 0

        rows = conn.execute(
            """
            SELECT m.name AS manager,
                   s.total_score_normal  AS total_normal,
                   s.total_score_nostalgia AS total_nostalgia,
                   s.rank_normal,
                   s.rank_nostalgia,
                   ms.score_normal       AS last_normal,
                   ms.score_nostalgia    AS last_nostalgia
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
        [
            {
                "rank": r["rank_normal"],
                "manager": r["manager"],
                "total": r["total_normal"],
                "last_matchday": r["last_normal"],
            }
            for r in rows
        ],
        key=lambda x: x["rank"] or 9999,
    )
    nostalgia = sorted(
        [
            {
                "rank": r["rank_nostalgia"],
                "manager": r["manager"],
                "total": r["total_nostalgia"],
                "last_matchday": r["last_nostalgia"],
            }
            for r in rows
        ],
        key=lambda x: x["rank"] or 9999,
    )

    return {
        "league": {
            "name": league["name"],
            "season_current": league["season_current"],
            "season_historic": league["season_historic"],
        },
        "last_matchday": last_matchday,
        "normal": normal,
        "nostalgia": nostalgia,
    }


@router.get("/league/{league_id}/standings/{manager_name}")
def get_manager_standings(league_id: int, manager_name: str):
    with get_db() as conn:
        _require_league(conn, league_id)

        manager = conn.execute(
            "SELECT id FROM manager WHERE league_id = ? AND name = ?",
            (league_id, manager_name),
        ).fetchone()
        if manager is None:
            raise HTTPException(status_code=404, detail="Manager non trovato")

        manager_id = manager["id"]

        matchdays = conn.execute(
            """
            SELECT md.matchday_current, md.matchday_historic,
                   ms.score_normal, ms.score_nostalgia
            FROM matchday_score ms
            JOIN matchday_draw md
                ON md.league_id         = ms.league_id
               AND md.matchday_current  = ms.matchday
            WHERE ms.league_id = ? AND ms.manager_id = ?
            ORDER BY ms.matchday
            """,
            (league_id, manager_id),
        ).fetchall()

        standings = conn.execute(
            """
            SELECT total_score_normal, total_score_nostalgia, rank_normal, rank_nostalgia
            FROM standings WHERE league_id = ? AND manager_id = ?
            """,
            (league_id, manager_id),
        ).fetchone()

    return {
        "manager": manager_name,
        "matchdays": [
            {
                "matchday_current": r["matchday_current"],
                "matchday_historic": r["matchday_historic"],
                "score_normal": r["score_normal"],
                "score_nostalgia": r["score_nostalgia"],
            }
            for r in matchdays
        ],
        "total_normal": standings["total_score_normal"] if standings else 0.0,
        "total_nostalgia": standings["total_score_nostalgia"] if standings else 0.0,
        "rank_normal": standings["rank_normal"] if standings else None,
        "rank_nostalgia": standings["rank_nostalgia"] if standings else None,
    }


@router.get("/league/{league_id}/last-draw")
def get_last_draw(league_id: int):
    with get_db() as conn:
        _require_league(conn, league_id)
        row = conn.execute(
            """
            SELECT matchday_current, matchday_historic, drawn_at
            FROM matchday_draw
            WHERE league_id = ?
            ORDER BY matchday_current DESC
            LIMIT 1
            """,
            (league_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Nessuna giornata sorteggiata")
    return dict(row)
