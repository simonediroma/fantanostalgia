import sqlite3
from collections import defaultdict

from backend.engine.scoring import compute_player_breakdown

CRITERIA = ("best_score", "worst_defense", "best_player", "worst_player")


def free_historic_players(
    conn: sqlite3.Connection, league_id: int, role: str | None = None
) -> list[dict]:
    """Historic players of the league's season_historic not yet in any manager's
    nostalgia pool — the pool of prizes a Gran Premio can draw from."""
    league = conn.execute(
        "SELECT season_historic FROM league WHERE id = ?", (league_id,)
    ).fetchone()
    if league is None:
        raise ValueError("Lega non trovata")

    params: list = [league["season_historic"], league_id]
    role_clause = ""
    if role:
        role_clause = " AND ph.role = ?"
        params.append(role)

    rows = conn.execute(
        f"""
        SELECT ph.id, ph.name, ph.role, ph.team, ph.season
        FROM player_historic ph
        WHERE ph.season = ?
          AND ph.id NOT IN (
              SELECT mnp.player_historic_id
              FROM manager_nostalgia_pool mnp
              WHERE mnp.league_id = ?
          )
          {role_clause}
        ORDER BY ph.role, ph.name
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def _joined_manager_ids(conn: sqlite3.Connection, league_id: int) -> set[int]:
    """Managers whose slot is claimed by a registered coach (user_id set) — only
    these can win a Gran Premio."""
    rows = conn.execute(
        "SELECT id FROM manager WHERE league_id = ? AND user_id IS NOT NULL",
        (league_id,),
    ).fetchall()
    return {r["id"] for r in rows}


def _determine_winner(
    conn: sqlite3.Connection, league_id: int, matchday: int, criterion: str
) -> int | None:
    """Manager who wins the Gran Premio for the given criterion. Tie-break: lowest
    manager_id. Only managers with a joined coach (user_id set) are eligible."""
    if criterion == "best_score":
        row = conn.execute(
            "SELECT manager_id FROM matchday_score"
            " WHERE league_id = ? AND matchday = ?"
            " AND manager_id IN ("
            "   SELECT id FROM manager WHERE league_id = ? AND user_id IS NOT NULL"
            " )"
            " ORDER BY score_nostalgia DESC, manager_id ASC LIMIT 1",
            (league_id, matchday, league_id),
        ).fetchone()
        return row["manager_id"] if row else None

    breakdown = compute_player_breakdown(conn, league_id, matchday)
    joined = _joined_manager_ids(conn, league_id)
    breakdown = [p for p in breakdown if p["manager_id"] in joined]
    if not breakdown:
        return None

    if criterion == "best_player":
        best = max(breakdown, key=lambda x: (x["ns"], -x["manager_id"]))
        return best["manager_id"]

    if criterion == "worst_player":
        worst = min(breakdown, key=lambda x: (x["ns"], x["manager_id"]))
        return worst["manager_id"]

    if criterion == "worst_defense":
        def_score: dict[int, float] = defaultdict(float)
        for p in breakdown:
            if p["role"] in ("P", "D"):
                def_score[p["manager_id"]] += p["ns"]
        if not def_score:
            return None
        return min(def_score, key=lambda m: (def_score[m], m))

    raise ValueError(f"Criterio sconosciuto: {criterion}")


def resolve_gran_premio(conn: sqlite3.Connection, gran_premio_id: int) -> int:
    """Determine the winner, award the prize historic player to their nostalgia
    pool (unassigned), and reopen their association period. Returns winner id."""
    gp = conn.execute(
        "SELECT id, league_id, matchday, criterion, prize_player_historic_id, status"
        " FROM gran_premio WHERE id = ?",
        (gran_premio_id,),
    ).fetchone()
    if gp is None:
        raise ValueError("Gran Premio non trovato")
    if gp["status"] == "resolved":
        raise ValueError("Gran Premio già risolto")

    league_id = gp["league_id"]
    matchday = gp["matchday"]

    scored = conn.execute(
        "SELECT 1 FROM matchday_score WHERE league_id = ? AND matchday = ? LIMIT 1",
        (league_id, matchday),
    ).fetchone()
    if scored is None:
        raise ValueError(f"Punteggi non ancora calcolati per la giornata {matchday}")

    winner_id = _determine_winner(conn, league_id, matchday, gp["criterion"])
    if winner_id is None:
        raise ValueError("Impossibile determinare un vincitore per questo Gran Premio")

    # Award: add the prize to the winner's nostalgia pool (unassigned slot) and
    # reopen their association so they can place/switch it.
    conn.execute(
        "INSERT OR IGNORE INTO manager_nostalgia_pool"
        " (manager_id, league_id, player_historic_id) VALUES (?, ?, ?)",
        (winner_id, league_id, gp["prize_player_historic_id"]),
    )
    conn.execute(
        "UPDATE manager SET assignments_locked = 0 WHERE id = ?", (winner_id,)
    )
    conn.execute(
        "UPDATE gran_premio SET status = 'resolved', winner_manager_id = ?,"
        " resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (winner_id, gran_premio_id),
    )
    return winner_id
