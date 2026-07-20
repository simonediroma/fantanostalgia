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
        SELECT ph.id, ph.name, ph.role, ph.team, ph.season,
               ROUND(AVG(hr.rating), 2) AS avg_rating
        FROM player_historic ph
        LEFT JOIN historic_rating hr ON hr.player_historic_id = ph.id
        WHERE ph.season = ?
          AND ph.id NOT IN (
              SELECT mnp.player_historic_id
              FROM manager_nostalgia_pool mnp
              WHERE mnp.league_id = ?
          )
          {role_clause}
        GROUP BY ph.id
        ORDER BY CASE ph.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                 ph.team, AVG(hr.rating) DESC
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


def _ranked_managers(
    conn: sqlite3.Connection, league_id: int, matchday: int, criterion: str
) -> list[int]:
    """Joined managers ordered best-to-worst for the given criterion. Tie-break:
    lowest manager_id. Only managers with a joined coach (user_id set) are
    eligible."""
    joined = _joined_manager_ids(conn, league_id)
    if not joined:
        return []

    if criterion == "best_score":
        rows = conn.execute(
            "SELECT manager_id FROM matchday_score"
            " WHERE league_id = ? AND matchday = ?"
            " ORDER BY score_nostalgia DESC, manager_id ASC",
            (league_id, matchday),
        ).fetchall()
        return [r["manager_id"] for r in rows if r["manager_id"] in joined]

    breakdown = compute_player_breakdown(conn, league_id, matchday)
    breakdown = [p for p in breakdown if p["manager_id"] in joined]
    if not breakdown:
        return []

    if criterion == "best_player":
        best_ns: dict[int, float] = {}
        for p in breakdown:
            mid = p["manager_id"]
            if mid not in best_ns or p["ns"] > best_ns[mid]:
                best_ns[mid] = p["ns"]
        return sorted(best_ns, key=lambda m: (-best_ns[m], m))

    if criterion == "worst_player":
        worst_ns: dict[int, float] = {}
        for p in breakdown:
            mid = p["manager_id"]
            if mid not in worst_ns or p["ns"] < worst_ns[mid]:
                worst_ns[mid] = p["ns"]
        return sorted(worst_ns, key=lambda m: (worst_ns[m], m))

    if criterion == "worst_defense":
        def_score: dict[int, float] = defaultdict(float)
        for p in breakdown:
            if p["role"] in ("P", "D"):
                def_score[p["manager_id"]] += p["ns"]
        return sorted(def_score, key=lambda m: (def_score[m], m))

    raise ValueError(f"Criterio sconosciuto: {criterion}")


def _has_free_role_slot(
    conn: sqlite3.Connection, league_id: int, manager_id: int, role: str
) -> bool:
    """Whether the manager has a player_current of this role without an
    assigned nostalgia pool entry yet — the only place a new prize of this
    role could ever be placed."""
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM player_current"
        " WHERE league_id = ? AND manager_id = ? AND role = ?",
        (league_id, manager_id, role),
    ).fetchone()["c"]
    taken = conn.execute(
        "SELECT COUNT(*) AS c FROM manager_nostalgia_pool mnp"
        " JOIN player_current pc ON pc.id = mnp.assigned_player_current_id"
        " WHERE mnp.manager_id = ? AND pc.role = ?",
        (manager_id, role),
    ).fetchone()["c"]
    return taken < total


def _already_won_manager_ids(
    conn: sqlite3.Connection, league_id: int, matchday: int, exclude_gp_id: int
) -> set[int]:
    """Managers who already won another resolved Gran Premio of this same
    matchday — ineligible to win a second one."""
    rows = conn.execute(
        "SELECT winner_manager_id FROM gran_premio"
        " WHERE league_id = ? AND matchday = ? AND status = 'resolved' AND id != ?",
        (league_id, matchday, exclude_gp_id),
    ).fetchall()
    return {r["winner_manager_id"] for r in rows if r["winner_manager_id"] is not None}


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

    earlier_unresolved = conn.execute(
        "SELECT 1 FROM gran_premio"
        " WHERE league_id = ? AND matchday = ? AND status = 'active' AND id < ?"
        " LIMIT 1",
        (league_id, matchday, gran_premio_id),
    ).fetchone()
    if earlier_unresolved is not None:
        raise ValueError(
            "Risolvi prima gli altri Gran Premi di questa giornata, in ordine di creazione"
        )

    scored = conn.execute(
        "SELECT 1 FROM matchday_score WHERE league_id = ? AND matchday = ? LIMIT 1",
        (league_id, matchday),
    ).fetchone()
    if scored is None:
        raise ValueError(f"Punteggi non ancora calcolati per la giornata {matchday}")

    prize_role = conn.execute(
        "SELECT role FROM player_historic WHERE id = ?",
        (gp["prize_player_historic_id"],),
    ).fetchone()["role"]

    ranked = _ranked_managers(conn, league_id, matchday, gp["criterion"])
    if not ranked:
        raise ValueError("Impossibile determinare un vincitore per questo Gran Premio")

    already_won = _already_won_manager_ids(conn, league_id, matchday, gran_premio_id)

    winner_id = next(
        (
            mid for mid in ranked
            if mid not in already_won and _has_free_role_slot(conn, league_id, mid, prize_role)
        ),
        None,
    )
    if winner_id is None:
        raise ValueError(
            "Nessun manager ha uno slot libero per il ruolo in palio "
            "(o ha già vinto un altro Gran Premio in questa giornata): impossibile assegnare il premio"
        )

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
