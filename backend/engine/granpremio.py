import json
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
               ROUND(AVG(hr.rating), 2) AS avg_rating,
               COUNT(hr.rating) AS appearances
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


def _ranking(
    conn: sqlite3.Connection, league_id: int, matchday: int, criterion: str
) -> list[dict]:
    """Joined managers ordered best-to-worst for the given criterion, with the
    value that ranks them and the players it comes from:
    [{manager_id, value, players: [{name, role, ns}]}]. Tie-break: lowest
    manager_id. Only managers with a joined coach (user_id set) are eligible."""
    joined = _joined_manager_ids(conn, league_id)
    if not joined:
        return []

    if criterion == "best_score":
        rows = conn.execute(
            "SELECT manager_id, score_nostalgia FROM matchday_score"
            " WHERE league_id = ? AND matchday = ?"
            " ORDER BY score_nostalgia DESC, manager_id ASC",
            (league_id, matchday),
        ).fetchall()
        return [
            {"manager_id": r["manager_id"], "value": r["score_nostalgia"], "players": []}
            for r in rows if r["manager_id"] in joined
        ]

    breakdown = compute_player_breakdown(conn, league_id, matchday)
    breakdown = [p for p in breakdown if p["manager_id"] in joined]
    if not breakdown:
        return []

    def player(p: dict) -> dict:
        return {"name": p["name"], "role": p["role"], "ns": p["ns"]}

    if criterion in ("best_player", "worst_player"):
        better = (lambda a, b: a > b) if criterion == "best_player" else (lambda a, b: a < b)
        pick: dict[int, dict] = {}
        for p in breakdown:
            mid = p["manager_id"]
            if mid not in pick or better(p["ns"], pick[mid]["ns"]):
                pick[mid] = p
        sign = -1 if criterion == "best_player" else 1
        return [
            {"manager_id": m, "value": pick[m]["ns"], "players": [player(pick[m])]}
            for m in sorted(pick, key=lambda m: (sign * pick[m]["ns"], m))
        ]

    if criterion == "worst_defense":
        defense: dict[int, list[dict]] = defaultdict(list)
        for p in breakdown:
            if p["role"] in ("P", "D"):
                defense[p["manager_id"]].append(p)
        total = {m: sum(p["ns"] for p in ps) for m, ps in defense.items()}
        return [
            {"manager_id": m, "value": round(total[m], 1),
             "players": [player(p) for p in defense[m]]}
            for m in sorted(total, key=lambda m: (total[m], m))
        ]

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

    ranking = _ranking(conn, league_id, matchday, gp["criterion"])
    if not ranking:
        raise ValueError("Impossibile determinare un vincitore per questo Gran Premio")

    already_won = _already_won_manager_ids(conn, league_id, matchday, gran_premio_id)

    winner_id = None
    for entry in ranking:
        if winner_id is not None:
            entry["outcome"] = None
        elif entry["manager_id"] in already_won:
            entry["outcome"] = "already_won"
        elif not _has_free_role_slot(conn, league_id, entry["manager_id"], prize_role):
            entry["outcome"] = "no_slot"
        else:
            entry["outcome"] = "winner"
            winner_id = entry["manager_id"]
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
        " explanation = ?, resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (winner_id, json.dumps(ranking), gran_premio_id),
    )
    return winner_id


CRITERIA_RULES = {
    "best_score": "punteggio nostalgia della squadra, vince il più alto",
    "worst_defense": "somma dei punteggi di portiere e difensori in campo, vince la più bassa",
    "best_player": "miglior giocatore in campo di ogni squadra, vince il più alto",
    "worst_player": "peggior giocatore in campo di ogni squadra, vince il più basso",
}

_OUTCOME_LABELS = {
    "winner": "vince",
    "already_won": "esclusa: ha già vinto un Gran Premio in questa giornata",
    "no_slot": "esclusa: nessun posto libero nel ruolo",
    "excluded": "esclusa",
}


def gran_premio_explanation(conn: sqlite3.Connection, gp) -> dict | None:
    """Il conteggio di un Gran Premio risolto: regola del criterio e classifica delle
    squadre con valore, giocatori che lo compongono ed esito. Usa quello fissato alla
    risoluzione; per i Gran Premi risolti prima che venisse salvato lo ricalcola (senza
    il motivo delle esclusioni)."""
    if gp["status"] != "resolved":
        return None
    if gp["explanation"]:
        ranking = json.loads(gp["explanation"])
    else:
        try:
            ranking = _ranking(conn, gp["league_id"], gp["matchday"], gp["criterion"])
        except ValueError:
            return None
        ids = [r["manager_id"] for r in ranking]
        win_pos = ids.index(gp["winner_manager_id"]) if gp["winner_manager_id"] in ids else -1
        for i, r in enumerate(ranking):
            r["outcome"] = "winner" if i == win_pos else ("excluded" if i < win_pos else None)

    names = {
        r["id"]: r["name"]
        for r in conn.execute("SELECT id, name FROM manager WHERE league_id = ?", (gp["league_id"],))
    }
    rows = []
    for pos, r in enumerate(ranking, start=1):
        detail = " + ".join(f"{p['name']} ({p['role']}) {p['ns']:.1f}" for p in r["players"])
        rows.append({
            "pos": pos,
            "manager": names.get(r["manager_id"], "?"),
            "value": f"{r['value']:.1f}",
            "detail": detail,
            "outcome": r.get("outcome"),
            "outcome_label": _OUTCOME_LABELS.get(r.get("outcome"), ""),
        })
    return {"rule": CRITERIA_RULES.get(gp["criterion"], ""), "ranking": rows}
