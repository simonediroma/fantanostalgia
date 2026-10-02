"""Sincronizza le rose (`player_current.manager_id`) con quelle di Leghe Fantacalcio.

Prima si verifica tutto, poi si scrive: una risposta parziale o anomala non modifica nulla.
Le associazioni alter ego non vengono toccate: un alter ego vale solo quando la squadra che
lo possiede schiera il giocatore (vedi scoring). Se il giocatore esce dalla rosa, la squadra
viene sbloccata per poterlo riassociare; l'associazione resta finché non lo fa.
"""
import json
import sqlite3

from backend.api.fantacalcio import FC_ROLES, parse_roster

MAX_RELEASES = 10


class RosterSyncError(ValueError):
    pass


def _unlock_previous_owners(conn: sqlite3.Connection, league_id: int, player_id: int,
                            new_manager_id: int | None) -> list[int]:
    """Sblocca le associazioni delle squadre che hanno un alter ego su un giocatore che non
    è più loro, così possono riassociarlo. L'associazione non viene cancellata."""
    owners = [r["manager_id"] for r in conn.execute(
        "SELECT DISTINCT manager_id FROM manager_nostalgia_pool"
        " WHERE league_id = ? AND assigned_player_current_id = ?",
        (league_id, player_id),
    ) if r["manager_id"] != new_manager_id]
    for mid in owners:
        conn.execute("UPDATE manager SET assignments_locked = 0 WHERE id = ?", (mid,))
    return owners


def _key(name: str) -> str:
    return (name or "").strip().lower()


def sync_rosters(conn: sqlite3.Connection, league_id: int, teams: list[dict], total: int | None,
                 fc_players: list[dict], force: bool = False) -> dict:
    """`teams`/`total` da fantacalcio.league_teams, `fc_players` da fantacalcio.players.
    Solleva RosterSyncError (senza scrivere nulla) se un controllo di integrità fallisce."""
    managers = conn.execute(
        "SELECT id, name, team_name, fc_team_id FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()
    label = {m["id"]: (m["team_name"] or m["name"]).strip() for m in managers}
    by_fc_team = {m["fc_team_id"]: m["id"] for m in managers if m["fc_team_id"]}
    by_team_name = {_key(m["team_name"] or m["name"]): m["id"] for m in managers}
    anagrafica = {p.get("id"): p for p in fc_players}

    # ── 1. Controlli di integrità ─────────────────────────────────────────────
    errors: list[str] = []
    if total is not None and len(teams) != total:
        errors.append(f"Lette {len(teams)} squadre su {total}")
    team_manager: dict[int, int] = {}
    new_owner: dict[int, tuple[int, int | None]] = {}  # fc player id → (manager_id, prezzo)
    for t in teams:
        name = (t.get("n") or "").strip()
        mid = by_fc_team.get(t.get("id")) or by_team_name.get(_key(name))
        if mid is None:
            errors.append(f"Squadra '{name}' non presente in FantaNostalgia: creala o rinominala")
            continue
        if mid in team_manager.values():
            errors.append(f"Squadra '{name}' collegata a una squadra già usata ({label[mid]})")
        team_manager[t.get("id")] = mid
        roster = parse_roster(t)
        if not roster:
            errors.append(f"Rosa vuota per '{name}'")
        expected = sum((t.get("r") or {}).values()) if t.get("r") else None
        if expected is not None and len(roster) != expected:
            errors.append(f"'{name}': {len(roster)} giocatori in rosa ma {expected} attesi per ruolo")
        for p in roster:
            pid = p["player_id"]
            if pid in new_owner:
                errors.append(f"Giocatore {pid} in due squadre")
            if pid not in anagrafica:
                errors.append(f"Giocatore {pid} di '{name}' assente dall'anagrafica")
            elif FC_ROLES.get(anagrafica[pid].get("fcrle")) is None:
                errors.append(f"Ruolo sconosciuto per {anagrafica[pid].get('name')}")
            new_owner[pid] = (mid, p["purchase_price"])
    if errors:
        raise RosterSyncError("Sincronizzazione interrotta, nessuna modifica: " + "; ".join(errors))

    # ── 2. Diff (nessuna scrittura) ───────────────────────────────────────────
    current = [dict(r) for r in conn.execute(
        "SELECT id, name, manager_id, fc_id FROM player_current WHERE league_id = ?", (league_id,))]
    by_fc_id = {p["fc_id"]: p for p in current if p["fc_id"] is not None}
    by_name = {_key(p["name"]): p for p in current if p["fc_id"] is None}

    matched: dict[int, dict | None] = {}
    for pid in new_owner:
        pc = by_fc_id.get(pid) or by_name.pop(_key(anagrafica[pid].get("name")), None)
        matched[pid] = pc
    matched_ids = {pc["id"] for pc in matched.values() if pc}

    moves: list[tuple[str, dict | None, int, int | None]] = []  # (kind, pc, to_mid, fc pid)
    for pid, (mid, _) in new_owner.items():
        pc = matched[pid]
        if pc is None or pc["manager_id"] is None:
            moves.append(("acquisto", pc, mid, pid))
        elif pc["manager_id"] != mid:
            moves.append(("spostamento", pc, mid, pid))
    released = [p for p in current if p["manager_id"] is not None and p["id"] not in matched_ids]
    if len(released) > MAX_RELEASES and not force:
        raise RosterSyncError(
            f"Sincronizzazione interrotta, nessuna modifica: {len(released)} giocatori da svincolare "
            f"(soglia {MAX_RELEASES}). Se è corretto, conferma per procedere comunque."
        )

    # ── 3. Scrittura ──────────────────────────────────────────────────────────
    run_id = conn.execute(
        "INSERT INTO roster_sync_run (league_id, teams_raw) VALUES (?, ?)",
        (league_id, json.dumps([{k: t.get(k) for k in ("id", "n", "cri", "crs", "cr", "bm")} for t in teams])),
    ).lastrowid
    for fc_team, mid in team_manager.items():
        conn.execute("UPDATE manager SET fc_team_id = ? WHERE id = ?", (fc_team, mid))
    for pid, pc in matched.items():
        if pc is not None and pc["fc_id"] is None:
            conn.execute("UPDATE player_current SET fc_id = ? WHERE id = ?", (pid, pc["id"]))

    summary = {"added": [], "moved": [], "released": [], "realign": []}
    realign: set[int] = set()

    def log(kind, pc_id, from_mid, to_mid):
        conn.execute(
            "INSERT INTO roster_move (sync_run_id, league_id, player_current_id, from_manager_id,"
            " to_manager_id, kind) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, league_id, pc_id, from_mid, to_mid, kind),
        )

    for kind, pc, mid, pid in moves:
        info = anagrafica[pid]
        if pc is None:
            # Prezzo d'acquisto (`cs`, da confermare) salvato come quotation, come il Costo del listone
            pc_id = conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, quotation, manager_id, fc_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (league_id, info.get("name"), FC_ROLES[info.get("fcrle")], info.get("team") or "",
                 new_owner[pid][1] or 1, mid, pid),
            ).lastrowid
            from_mid = None
        else:
            pc_id, from_mid = pc["id"], pc["manager_id"]
            realign.update(_unlock_previous_owners(conn, league_id, pc_id, mid))
            conn.execute("UPDATE player_current SET manager_id = ? WHERE id = ?", (mid, pc_id))
        log(kind, pc_id, from_mid, mid)
        if kind == "acquisto":
            summary["added"].append(f"{info.get('name')} → {label[mid]}")
        else:
            summary["moved"].append(f"{info.get('name')}: {label[from_mid]} → {label[mid]}")

    for p in released:
        realign.update(_unlock_previous_owners(conn, league_id, p["id"], None))
        conn.execute("UPDATE player_current SET manager_id = NULL WHERE id = ?", (p["id"],))
        log("svincolo", p["id"], p["manager_id"], None)
        summary["released"].append(f"{p['name']} (da {label[p['manager_id']]})")

    summary["realign"] = sorted(label[m] for m in realign if m in label)
    conn.execute("UPDATE roster_sync_run SET summary = ? WHERE id = ?", (json.dumps(summary), run_id))
    return summary


def _is_referenced(conn: sqlite3.Connection, player_id: int) -> bool:
    return any(
        conn.execute(sql, (player_id,)).fetchone()
        for sql in (
            "SELECT 1 FROM lineup WHERE player_current_id = ? LIMIT 1",
            "SELECT 1 FROM manager_nostalgia_pool WHERE assigned_player_current_id = ? LIMIT 1",
            "SELECT 1 FROM alter_ego WHERE player_current_id = ? LIMIT 1",
            "SELECT 1 FROM roster_move WHERE player_current_id = ? LIMIT 1",
        )
    )


def apply_listone(conn: sqlite3.Connection, league_id: int, rows: list[dict], force: bool = False) -> dict:
    """Reimport del listone senza cancellare: aggiorna i giocatori esistenti (per nome),
    aggiunge i nuovi e, se il file indica la fantasquadra, sposta chi ha cambiato squadra.
    Chi non è più nel file viene cancellato se mai usato, altrimenti tolto dalla rosa.
    Le associazioni alter ego restano (vedi sync_rosters). Solleva RosterSyncError, senza
    scrivere nulla, se gli svincoli superano MAX_RELEASES e non c'è `force`."""
    managers = conn.execute(
        "SELECT id, name, team_name FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()
    team_map = {_key(m["team_name"]): m["id"] for m in managers if m["team_name"]}
    label = {m["id"]: (m["team_name"] or m["name"]).strip() for m in managers}

    current = {_key(p["name"]): dict(p) for p in conn.execute(
        "SELECT id, name, manager_id FROM player_current WHERE league_id = ?", (league_id,))}
    in_file = {_key(r["name"]) for r in rows}
    gone = [p for k, p in current.items() if k not in in_file]
    to_release = [p for p in gone if _is_referenced(conn, p["id"])]
    released_owned = [p for p in to_release if p["manager_id"] is not None]
    if len(released_owned) > MAX_RELEASES and not force:
        raise RosterSyncError(
            f"Import interrotto, nessuna modifica: {len(released_owned)} giocatori da svincolare "
            f"(soglia {MAX_RELEASES}). Se è corretto, conferma per procedere comunque."
        )

    teams_created: list[str] = []
    summary = {"added": [], "moved": [], "released": [], "realign": []}
    realign: set[int] = set()
    run_id = conn.execute("INSERT INTO roster_sync_run (league_id) VALUES (?)", (league_id,)).lastrowid

    def log(kind, pc_id, from_mid, to_mid):
        conn.execute(
            "INSERT INTO roster_move (sync_run_id, league_id, player_current_id, from_manager_id,"
            " to_manager_id, kind) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, league_id, pc_id, from_mid, to_mid, kind),
        )

    for r in rows:
        has_team = "fanta_team" in r and r["fanta_team"]
        mid = None
        if has_team:
            key = _key(r["fanta_team"])
            mid = team_map.get(key)
            if mid is None:
                # Auto-create team from Excel; president can rename the manager later
                mid = conn.execute(
                    "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
                    (league_id, r["fanta_team"].strip(), r["fanta_team"].strip()),
                ).lastrowid
                team_map[key] = mid
                label[mid] = r["fanta_team"].strip()
                teams_created.append(r["fanta_team"].strip())
        pc = current.get(_key(r["name"]))
        if pc is None:
            pc_id = conn.execute(
                "INSERT INTO player_current"
                " (league_id, name, role, team, quotation, starts_current_season, manager_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (league_id, r["name"], r["role"], r["team"], r["quota"], r["starts"], mid),
            ).lastrowid
            current[_key(r["name"])] = {"id": pc_id, "name": r["name"], "manager_id": mid}
            if mid is not None:
                log("acquisto", pc_id, None, mid)
                summary["added"].append(f"{r['name']} → {label[mid]}")
            continue
        conn.execute(
            "UPDATE player_current SET role = ?, team = ?, quotation = ?, starts_current_season = ?"
            " WHERE id = ?",
            (r["role"], r["team"], r["quota"], r["starts"], pc["id"]),
        )
        if has_team and pc["manager_id"] != mid:
            realign.update(_unlock_previous_owners(conn, league_id, pc["id"], mid))
            conn.execute("UPDATE player_current SET manager_id = ? WHERE id = ?", (mid, pc["id"]))
            kind = "acquisto" if pc["manager_id"] is None else "spostamento"
            log(kind, pc["id"], pc["manager_id"], mid)
            if kind == "acquisto":
                summary["added"].append(f"{r['name']} → {label[mid]}")
            else:
                summary["moved"].append(f"{r['name']}: {label[pc['manager_id']]} → {label[mid]}")

    for p in gone:
        if p in to_release:
            if p["manager_id"] is None:
                continue
            realign.update(_unlock_previous_owners(conn, league_id, p["id"], None))
            conn.execute("UPDATE player_current SET manager_id = NULL WHERE id = ?", (p["id"],))
            log("svincolo", p["id"], p["manager_id"], None)
            summary["released"].append(f"{p['name']} (da {label[p['manager_id']]})")
        else:
            conn.execute("DELETE FROM player_current WHERE id = ?", (p["id"],))

    summary["realign"] = sorted(label[m] for m in realign if m in label)
    conn.execute("UPDATE roster_sync_run SET summary = ? WHERE id = ?", (json.dumps(summary), run_id))
    return {**summary, "teams_created": sorted(teams_created)}
