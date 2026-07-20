import math
import sqlite3

from backend.engine.granpremio import free_historic_players
from backend.engine.mapping import POOL_SIZE, ROLES

CUT_BASELINE_RATING = 6.0
CUT_BASE_VALUE = 10
CUT_STEP_CREDITS = 5
CUT_STEP_RATING = 0.5
CUT_FLOOR_VALUE = 1


def _round_half_away_from_zero(x: float) -> int:
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def compute_cut_value(conn: sqlite3.Connection, player_historic_id: int) -> int:
    """Credits earned by cutting a historic player: 10 base, +/-5 per half point of
    average rating away from 6.0, floored at 1. No ratings recorded -> treated as 6.0."""
    row = conn.execute(
        "SELECT AVG(rating) AS avg_rating FROM historic_rating WHERE player_historic_id = ?",
        (player_historic_id,),
    ).fetchone()
    avg_rating = row["avg_rating"] if row and row["avg_rating"] is not None else CUT_BASELINE_RATING
    diff = avg_rating - CUT_BASELINE_RATING
    steps = _round_half_away_from_zero(diff / CUT_STEP_RATING)
    value = CUT_BASE_VALUE + CUT_STEP_CREDITS * steps
    return max(value, CUT_FLOOR_VALUE)


def pool_role_counts(conn: sqlite3.Connection, manager_id: int) -> dict[str, int]:
    counts = {role: 0 for role in ROLES}
    rows = conn.execute(
        """
        SELECT ph.role, COUNT(*) AS n
        FROM manager_nostalgia_pool mnp
        JOIN player_historic ph ON ph.id = mnp.player_historic_id
        WHERE mnp.manager_id = ?
        GROUP BY ph.role
        """,
        (manager_id,),
    ).fetchall()
    for r in rows:
        counts[r["role"]] = r["n"]
    return counts


def free_slots_by_role(conn: sqlite3.Connection, manager_id: int) -> dict[str, int]:
    counts = pool_role_counts(conn, manager_id)
    return {role: max(POOL_SIZE[role] - counts.get(role, 0), 0) for role in ROLES}


def pending_bid_summary(
    conn: sqlite3.Connection,
    market_session_id: int,
    manager_id: int,
    exclude_player_historic_id: int | None = None,
) -> tuple[int, dict[str, int]]:
    """(total amount, count per role) of the manager's pending bids in this session,
    optionally excluding one player (used when updating an existing bid)."""
    rows = conn.execute(
        """
        SELECT mb.amount, ph.role
        FROM market_bid mb
        JOIN player_historic ph ON ph.id = mb.player_historic_id
        WHERE mb.market_session_id = ? AND mb.manager_id = ? AND mb.status = 'pending'
          AND mb.player_historic_id != COALESCE(?, -1)
        """,
        (market_session_id, manager_id, exclude_player_historic_id),
    ).fetchall()
    total = sum(r["amount"] for r in rows)
    by_role: dict[str, int] = {role: 0 for role in ROLES}
    for r in rows:
        by_role[r["role"]] += 1
    return total, by_role


def cut_player(
    conn: sqlite3.Connection, league_id: int, manager_id: int, player_historic_id: int
) -> int:
    """Remove a historic player from the manager's pool in exchange for credits.
    Returns the credited value."""
    session = conn.execute(
        "SELECT id FROM market_session WHERE league_id = ? AND status = 'cuts_open'",
        (league_id,),
    ).fetchone()
    if session is None:
        raise ValueError("Nessun mercato con fase tagli aperta in questa lega")

    pool_entry = conn.execute(
        "SELECT id, assigned_player_current_id FROM manager_nostalgia_pool"
        " WHERE manager_id = ? AND player_historic_id = ?",
        (manager_id, player_historic_id),
    ).fetchone()
    if pool_entry is None:
        raise ValueError("Giocatore non presente nel tuo pool nostalgia")

    value = compute_cut_value(conn, player_historic_id)

    if pool_entry["assigned_player_current_id"] is not None:
        conn.execute(
            "DELETE FROM alter_ego WHERE league_id = ? AND player_current_id = ?",
            (league_id, pool_entry["assigned_player_current_id"]),
        )

    conn.execute("DELETE FROM manager_nostalgia_pool WHERE id = ?", (pool_entry["id"],))
    conn.execute("UPDATE manager SET credits = credits + ? WHERE id = ?", (value, manager_id))
    return value


def create_market_session(
    conn: sqlite3.Connection, league_id: int, player_historic_ids: list[int]
) -> int:
    active = conn.execute(
        "SELECT id FROM market_session WHERE league_id = ? AND status IN ('cuts_open', 'bids_open')",
        (league_id,),
    ).fetchone()
    if active is not None:
        raise ValueError("Esiste già un mercato attivo per questa lega")

    if not player_historic_ids:
        raise ValueError("Seleziona almeno un giocatore per il mercato")

    free_ids = {p["id"] for p in free_historic_players(conn, league_id)}
    invalid = set(player_historic_ids) - free_ids
    if invalid:
        raise ValueError(f"Giocatori non disponibili (non liberi): {sorted(invalid)}")

    cur = conn.execute(
        "INSERT INTO market_session (league_id) VALUES (?)", (league_id,)
    )
    session_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO market_listing (market_session_id, player_historic_id) VALUES (?, ?)",
        [(session_id, pid) for pid in player_historic_ids],
    )
    return session_id


def close_cuts(conn: sqlite3.Connection, market_session_id: int) -> None:
    session = conn.execute(
        "SELECT status FROM market_session WHERE id = ?", (market_session_id,)
    ).fetchone()
    if session is None:
        raise ValueError("Sessione di mercato non trovata")
    if session["status"] != "cuts_open":
        raise ValueError("La fase tagli non è aperta")
    conn.execute(
        "UPDATE market_session SET status = 'bids_open', cuts_closed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (market_session_id,),
    )


def place_bid(
    conn: sqlite3.Connection,
    market_session_id: int,
    manager_id: int,
    player_historic_id: int,
    amount: int,
) -> None:
    if amount <= 0:
        raise ValueError("L'importo deve essere positivo")

    session = conn.execute(
        "SELECT status FROM market_session WHERE id = ?", (market_session_id,)
    ).fetchone()
    if session is None:
        raise ValueError("Sessione di mercato non trovata")
    if session["status"] != "bids_open":
        raise ValueError("La fase offerte non è aperta")

    listing = conn.execute(
        "SELECT ph.role FROM market_listing ml JOIN player_historic ph ON ph.id = ml.player_historic_id"
        " WHERE ml.market_session_id = ? AND ml.player_historic_id = ?",
        (market_session_id, player_historic_id),
    ).fetchone()
    if listing is None:
        raise ValueError("Giocatore non in vendita in questa sessione")
    role = listing["role"]

    manager = conn.execute(
        "SELECT credits FROM manager WHERE id = ?", (manager_id,)
    ).fetchone()
    if manager is None:
        raise ValueError("Manager non trovato")

    pending_total, pending_by_role = pending_bid_summary(
        conn, market_session_id, manager_id, exclude_player_historic_id=player_historic_id
    )
    if pending_total + amount > manager["credits"]:
        raise ValueError(
            f"Crediti insufficienti: disponibili {manager['credits']}, già impegnati {pending_total}"
        )

    free_slots = free_slots_by_role(conn, manager_id)[role]
    if pending_by_role.get(role, 0) + 1 > free_slots:
        raise ValueError(
            f"Nessuno slot libero per il ruolo {role} (anche considerando le offerte in corso)"
        )

    conn.execute(
        """
        INSERT INTO market_bid (market_session_id, manager_id, player_historic_id, amount, status, updated_at)
        VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        ON CONFLICT(market_session_id, manager_id, player_historic_id)
        DO UPDATE SET amount = excluded.amount, status = 'pending', updated_at = CURRENT_TIMESTAMP
        """,
        (market_session_id, manager_id, player_historic_id, amount),
    )


def withdraw_bid(
    conn: sqlite3.Connection, market_session_id: int, manager_id: int, player_historic_id: int
) -> None:
    session = conn.execute(
        "SELECT status FROM market_session WHERE id = ?", (market_session_id,)
    ).fetchone()
    if session is None:
        raise ValueError("Sessione di mercato non trovata")
    if session["status"] != "bids_open":
        raise ValueError("La fase offerte non è aperta")

    cur = conn.execute(
        "UPDATE market_bid SET status = 'withdrawn', updated_at = CURRENT_TIMESTAMP"
        " WHERE market_session_id = ? AND manager_id = ? AND player_historic_id = ? AND status = 'pending'",
        (market_session_id, manager_id, player_historic_id),
    )
    if cur.rowcount == 0:
        raise ValueError("Nessuna offerta attiva su questo giocatore")


def resolve_market_session(conn: sqlite3.Connection, market_session_id: int) -> list[dict]:
    session = conn.execute(
        "SELECT id, league_id, status FROM market_session WHERE id = ?", (market_session_id,)
    ).fetchone()
    if session is None:
        raise ValueError("Sessione di mercato non trovata")
    if session["status"] != "bids_open":
        raise ValueError("La sessione non è in fase offerte")

    league_id = session["league_id"]

    listings = conn.execute(
        """
        SELECT ml.player_historic_id, ph.role, ph.name
        FROM market_listing ml
        JOIN player_historic ph ON ph.id = ml.player_historic_id
        WHERE ml.market_session_id = ?
        ORDER BY ml.id ASC
        """,
        (market_session_id,),
    ).fetchall()

    results: list[dict] = []
    for listing in listings:
        player_historic_id = listing["player_historic_id"]
        role = listing["role"]

        bids = conn.execute(
            "SELECT id, manager_id, amount FROM market_bid"
            " WHERE market_session_id = ? AND player_historic_id = ? AND status = 'pending'"
            " ORDER BY amount DESC, manager_id ASC",
            (market_session_id, player_historic_id),
        ).fetchall()

        winner_bid = None
        for bid in bids:
            free = free_slots_by_role(conn, bid["manager_id"])[role]
            if free >= 1:
                winner_bid = bid
                break

        if winner_bid is not None:
            conn.execute(
                "INSERT OR IGNORE INTO manager_nostalgia_pool"
                " (manager_id, league_id, player_historic_id) VALUES (?, ?, ?)",
                (winner_bid["manager_id"], league_id, player_historic_id),
            )
            conn.execute(
                "UPDATE manager SET credits = credits - ? WHERE id = ?",
                (winner_bid["amount"], winner_bid["manager_id"]),
            )
            conn.execute(
                "UPDATE manager SET assignments_locked = 0 WHERE id = ?",
                (winner_bid["manager_id"],),
            )
            conn.execute("UPDATE market_bid SET status = 'won' WHERE id = ?", (winner_bid["id"],))

        conn.execute(
            "UPDATE market_bid SET status = 'lost'"
            " WHERE market_session_id = ? AND player_historic_id = ? AND status = 'pending'",
            (market_session_id, player_historic_id),
        )

        results.append({
            "player_historic_id": player_historic_id,
            "name": listing["name"],
            "role": role,
            "winner_manager_id": winner_bid["manager_id"] if winner_bid else None,
            "amount": winner_bid["amount"] if winner_bid else None,
        })

    conn.execute(
        "UPDATE market_session SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (market_session_id,),
    )
    return results


def cancel_market_session(conn: sqlite3.Connection, market_session_id: int) -> None:
    session = conn.execute(
        "SELECT status FROM market_session WHERE id = ?", (market_session_id,)
    ).fetchone()
    if session is None:
        raise ValueError("Sessione di mercato non trovata")
    if session["status"] not in ("cuts_open", "bids_open"):
        raise ValueError("La sessione non è annullabile in questo stato")
    conn.execute(
        "UPDATE market_session SET status = 'cancelled' WHERE id = ?", (market_session_id,)
    )
