import csv
import io
import sqlite3
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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


@router.get("/league/{league_id}/classifica/export.csv")
def export_classifica_csv(league_id: int):
    with get_db() as conn:
        league = _require_league(conn, league_id)
        rows = conn.execute(
            """
            SELECT m.name AS manager,
                   s.rank_nostalgia, s.total_score_nostalgia,
                   s.rank_normal,    s.total_score_normal
            FROM standings s
            JOIN manager m ON m.id = s.manager_id
            WHERE s.league_id = ?
            ORDER BY s.rank_nostalgia, m.name
            """,
            (league_id,),
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Pos FantaNostalgia", "Manager", "Totale FantaNostalgia",
        "Pos Normale", "Totale Normale",
    ])
    for r in rows:
        writer.writerow([
            r["rank_nostalgia"] or "",
            r["manager"],
            f"{r['total_score_nostalgia']:.1f}" if r["total_score_nostalgia"] is not None else "",
            r["rank_normal"] or "",
            f"{r['total_score_normal']:.1f}" if r["total_score_normal"] is not None else "",
        ])

    filename = f"classifica_{league['name'].replace(' ', '_')}_{league['season_current']}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _score_to_goals(score: float) -> int:
    """Convert a nostalgia match score to goals. Base 66 pts = 0 goals, then +1 per 6 pts."""
    if score < 66:
        return 0
    return int((score - 66) // 6)


def _compute_h2h(matches: list) -> list[dict]:
    """Aggregate h2h match results into per-manager standings."""
    stats: dict[str, dict] = defaultdict(lambda: {
        "played": 0, "wins": 0, "draws": 0, "losses": 0, "pf": 0.0, "ps": 0.0,
        "gf": 0, "gs": 0,
    })
    for m in matches:
        hm = m["home_manager"]
        am = m["away_manager"]
        hs = m["home_score"] or 0.0
        as_ = m["away_score"] or 0.0
        stats[hm]["played"] += 1
        stats[am]["played"] += 1
        stats[hm]["pf"] += hs
        stats[hm]["ps"] += as_
        stats[am]["pf"] += as_
        stats[am]["ps"] += hs
        stats[hm]["gf"] += _score_to_goals(hs)
        stats[hm]["gs"] += _score_to_goals(as_)
        stats[am]["gf"] += _score_to_goals(as_)
        stats[am]["gs"] += _score_to_goals(hs)
        if hs > as_:
            stats[hm]["wins"] += 1
            stats[am]["losses"] += 1
        elif hs < as_:
            stats[am]["wins"] += 1
            stats[hm]["losses"] += 1
        else:
            stats[hm]["draws"] += 1
            stats[am]["draws"] += 1

    rows = []
    for manager, s in stats.items():
        pts = s["wins"] * 3 + s["draws"]
        gdr = s["gf"] - s["gs"]
        rows.append({
            "manager": manager,
            "played": s["played"],
            "wins": s["wins"],
            "draws": s["draws"],
            "losses": s["losses"],
            "points": pts,
            "pf": round(s["pf"], 1),
            "ps": round(s["ps"], 1),
            "dr": round(s["pf"] - s["ps"], 1),
            "gf": s["gf"],
            "gs": s["gs"],
            "gdr": gdr,
        })

    rows.sort(key=lambda x: (-x["points"], -x["gdr"], -x["gf"]))
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


@router.get("/league/{league_id}/standings/h2h")
def get_h2h_standings(league_id: int):
    with get_db() as conn:
        league = _require_league(conn, league_id)

        matches = conn.execute(
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

    return {
        "league": {
            "name": league["name"],
            "season_current": league["season_current"],
            "season_historic": league["season_historic"],
        },
        "h2h": _compute_h2h([dict(m) for m in matches]),
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
