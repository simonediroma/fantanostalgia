"""Assegnazione giornata: dopo il calcolo della giornata e i Gran Premi, ogni
squadra con un posto libero riceve uno storico casuale dello stesso ruolo.

Ruolo a rotazione A → C → D → P → A…; un ruolo senza squadre con posto libero
(o senza storici liberi) viene saltato. Gli storici "idonei" rispettano le
fasce globali di `giveaway_rule`; se non bastano si completa con storici liberi
dello stesso ruolo fuori fascia.
"""
import random
import sqlite3

from backend.engine.granpremio import _has_free_role_slot, _joined_manager_ids, free_historic_players

SEQUENCE = ("A", "C", "D", "P")


def get_rules(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT role, min_avg, max_avg, min_appearances FROM giveaway_rule"
    ).fetchall()
    return {r["role"]: dict(r) for r in rows}


def in_band(player: dict, rule: dict) -> bool:
    """Whether a historic player (with avg_rating/appearances) matches the rule."""
    if (player["appearances"] or 0) < rule["min_appearances"]:
        return False
    avg = player["avg_rating"]
    if rule["min_avg"] is not None and (avg is None or avg < rule["min_avg"]):
        return False
    if rule["max_avg"] is not None and (avg is None or avg > rule["max_avg"]):
        return False
    return True


def _role_order(conn: sqlite3.Connection, league_id: int) -> list[str]:
    """Roles to try, starting from the one after the last assigned role."""
    last = conn.execute(
        "SELECT role FROM matchday_giveaway WHERE league_id = ? ORDER BY id DESC LIMIT 1",
        (league_id,),
    ).fetchone()
    start = (SEQUENCE.index(last["role"]) + 1) % len(SEQUENCE) if last else 0
    return [SEQUENCE[(start + i) % len(SEQUENCE)] for i in range(len(SEQUENCE))]


def plan_giveaway(conn: sqlite3.Connection, league_id: int) -> dict | None:
    """Next role with at least one receiving manager and one free historic
    player. None when no role can be assigned anymore."""
    rules = get_rules(conn)
    joined = sorted(_joined_manager_ids(conn, league_id))
    for role in _role_order(conn, league_id):
        managers = [m for m in joined if _has_free_role_slot(conn, league_id, m, role)]
        if not managers:
            continue
        free = free_historic_players(conn, league_id, role)
        if not free:
            continue
        band = [p for p in free if in_band(p, rules[role])]
        band_ids = {p["id"] for p in band}
        return {
            "role": role,
            "manager_ids": managers,
            "in_band": band,
            "out_of_band": [p for p in free if p["id"] not in band_ids],
        }
    return None


def check_preconditions(conn: sqlite3.Connection, league_id: int, matchday: int) -> None:
    done = conn.execute(
        "SELECT 1 FROM matchday_giveaway WHERE league_id = ? AND matchday = ? LIMIT 1",
        (league_id, matchday),
    ).fetchone()
    if done:
        raise ValueError("Assegnazione già eseguita per questa giornata")
    scored = conn.execute(
        "SELECT 1 FROM matchday_score WHERE league_id = ? AND matchday = ? LIMIT 1",
        (league_id, matchday),
    ).fetchone()
    if scored is None:
        raise ValueError(f"Punteggi non ancora calcolati per la giornata {matchday}")
    active_gp = conn.execute(
        "SELECT 1 FROM gran_premio WHERE league_id = ? AND matchday = ? AND status = 'active' LIMIT 1",
        (league_id, matchday),
    ).fetchone()
    if active_gp:
        raise ValueError("Risolvi prima i Gran Premi di questa giornata")


def run_giveaway(
    conn: sqlite3.Connection, league_id: int, matchday: int, rng: random.Random | None = None
) -> list[dict]:
    """Assign one random historic player per receiving manager. Returns the
    awards ({manager_id, player_historic_id, name, role, in_band})."""
    rng = rng or random.Random()
    check_preconditions(conn, league_id, matchday)
    plan = plan_giveaway(conn, league_id)
    if plan is None:
        raise ValueError("Nessuna squadra ha posti liberi: le assegnazioni sono concluse")

    managers = list(plan["manager_ids"])
    rng.shuffle(managers)
    band = list(plan["in_band"])
    rng.shuffle(band)
    out = list(plan["out_of_band"])
    rng.shuffle(out)
    candidates = [(p, True) for p in band] + [(p, False) for p in out]

    awards = []
    for manager_id, (player, is_in_band) in zip(managers, candidates):
        conn.execute(
            "INSERT INTO manager_nostalgia_pool (manager_id, league_id, player_historic_id)"
            " VALUES (?, ?, ?)",
            (manager_id, league_id, player["id"]),
        )
        conn.execute("UPDATE manager SET assignments_locked = 0 WHERE id = ?", (manager_id,))
        conn.execute(
            "INSERT INTO matchday_giveaway"
            " (league_id, matchday, role, manager_id, player_historic_id, in_band)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (league_id, matchday, plan["role"], manager_id, player["id"], int(is_in_band)),
        )
        awards.append({
            "manager_id": manager_id,
            "player_historic_id": player["id"],
            "name": player["name"],
            "role": plan["role"],
            "in_band": is_in_band,
        })
    return awards
