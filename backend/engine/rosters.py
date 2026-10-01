"""Allinea le rose (`player_current.manager_id`) a quelle della piattaforma.

Gli alter ego restano nel pool della squadra: se il giocatore reale a cui erano
associati lascia la rosa, l'associazione si libera e il manager può riassociarli.
"""
import sqlite3


def _release_alter_ego(conn: sqlite3.Connection, league_id: int, player_id: int) -> None:
    """Libera l'alter ego associato a un giocatore uscito dalla rosa."""
    owners = conn.execute(
        "SELECT DISTINCT manager_id FROM manager_nostalgia_pool"
        " WHERE league_id = ? AND assigned_player_current_id = ?",
        (league_id, player_id),
    ).fetchall()
    conn.execute(
        "UPDATE manager_nostalgia_pool SET assigned_player_current_id = NULL"
        " WHERE league_id = ? AND assigned_player_current_id = ?",
        (league_id, player_id),
    )
    conn.execute(
        "DELETE FROM alter_ego WHERE league_id = ? AND player_current_id = ?",
        (league_id, player_id),
    )
    for o in owners:
        conn.execute("UPDATE manager SET assignments_locked = 0 WHERE id = ?", (o["manager_id"],))


def sync_rosters(conn: sqlite3.Connection, league_id: int, rosters: dict[str, list[dict]]) -> dict:
    """`rosters`: nome squadra → [{name, role}]. Aggiunge i nuovi acquisti, sposta chi
    ha cambiato squadra, svincola (manager_id NULL, senza cancellare) chi non è più in
    nessuna rosa. Tocca solo le squadre presenti in `rosters`."""
    managers = conn.execute(
        "SELECT id, name, team_name FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()
    team_map = {(m["team_name"] or m["name"]).strip().lower(): m["id"] for m in managers}
    label = {m["id"]: (m["team_name"] or m["name"]).strip() for m in managers}

    players = conn.execute(
        "SELECT id, name, manager_id FROM player_current WHERE league_id = ?", (league_id,)
    ).fetchall()
    by_name = {p["name"].strip().lower(): dict(p) for p in players}

    added, moved, released, warnings = [], [], [], []
    synced_ids: set[int] = set()
    seen: set[str] = set()

    for team, roster in rosters.items():
        manager_id = team_map.get(team.strip().lower())
        if manager_id is None:
            warnings.append(f"Squadra '{team}' non trovata nella lega — saltata")
            continue
        synced_ids.add(manager_id)
        for p in roster:
            key = p["name"].strip().lower()
            seen.add(key)
            cur = by_name.get(key)
            if cur is None:
                if not p.get("role"):
                    warnings.append(f"Giocatore '{p['name']}' senza ruolo — saltato")
                    continue
                pid = conn.execute(
                    "INSERT INTO player_current (league_id, name, role, team, manager_id)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (league_id, p["name"].strip(), p["role"], p.get("team") or "", manager_id),
                ).lastrowid
                by_name[key] = {"id": pid, "name": p["name"], "manager_id": manager_id}
                added.append(f"{p['name']} → {label[manager_id]}")
            elif cur["manager_id"] != manager_id:
                _release_alter_ego(conn, league_id, cur["id"])
                conn.execute("UPDATE player_current SET manager_id = ? WHERE id = ?",
                             (manager_id, cur["id"]))
                old = label.get(cur["manager_id"], "svincolati")
                moved.append(f"{cur['name']}: {old} → {label[manager_id]}")
                cur["manager_id"] = manager_id

    for key, cur in by_name.items():
        if key not in seen and cur["manager_id"] in synced_ids:
            _release_alter_ego(conn, league_id, cur["id"])
            conn.execute("UPDATE player_current SET manager_id = NULL WHERE id = ?", (cur["id"],))
            released.append(f"{cur['name']} (da {label[cur['manager_id']]})")

    return {"added": added, "moved": moved, "released": released, "warnings": warnings}
