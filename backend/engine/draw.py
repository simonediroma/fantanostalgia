import random
import sqlite3
from dataclasses import dataclass


def get_season_matchday_count(season: str) -> int:
    start_year = int(season[:4])
    if start_year <= 1987:
        return 30
    elif start_year <= 2003:
        return 34
    else:
        return 38


@dataclass
class DrawResult:
    matchday_current: int
    matchday_historic: int
    cycle: int
    drawn_at: str


def perform_draw(conn: sqlite3.Connection, league_id: int, matchday_current: int) -> DrawResult:
    existing = conn.execute(
        "SELECT matchday_historic, cycle, drawn_at FROM matchday_draw"
        " WHERE league_id = ? AND matchday_current = ?",
        (league_id, matchday_current),
    ).fetchone()
    if existing:
        return DrawResult(
            matchday_current=matchday_current,
            matchday_historic=existing["matchday_historic"],
            cycle=existing["cycle"],
            drawn_at=existing["drawn_at"],
        )

    league = conn.execute(
        "SELECT season_historic FROM league WHERE id = ?", (league_id,)
    ).fetchone()
    if league is None:
        raise ValueError("Lega non trovata")

    n = get_season_matchday_count(league["season_historic"])
    all_matchdays = set(range(1, n + 1))

    rows = conn.execute(
        "SELECT matchday_historic, cycle FROM matchday_draw WHERE league_id = ?",
        (league_id,),
    ).fetchall()

    current_cycle = 1
    drawn_in_cycle: set[int] = set()

    if rows:
        current_cycle = max(r["cycle"] for r in rows)
        drawn_in_cycle = {r["matchday_historic"] for r in rows if r["cycle"] == current_cycle}

    pool = all_matchdays - drawn_in_cycle
    if not pool:
        current_cycle += 1
        pool = all_matchdays

    matchday_historic = random.choice(sorted(pool))

    conn.execute(
        "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
        " VALUES (?, ?, ?, ?)",
        (league_id, matchday_current, matchday_historic, current_cycle),
    )

    row = conn.execute(
        "SELECT drawn_at FROM matchday_draw WHERE league_id = ? AND matchday_current = ?",
        (league_id, matchday_current),
    ).fetchone()

    return DrawResult(
        matchday_current=matchday_current,
        matchday_historic=matchday_historic,
        cycle=current_cycle,
        drawn_at=row["drawn_at"],
    )
