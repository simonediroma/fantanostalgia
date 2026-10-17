from backend.api.db import get_db


def _setup(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    lid = client.post("/admin/league", json={
        "name": "CompletaLega", "season_current": "2024/25",
        "season_historic": "1990/91", "budget": 500,
    }).json()["id"]
    with get_db() as conn:
        conn.execute("UPDATE league SET associations_closed = 1 WHERE id = ?", (lid,))
        mid = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M', 'TeamM')", (lid,)
        ).lastrowid
        pcs = {}
        for name, role, starts in [("A_low", "A", 3), ("A_high", "A", 20), ("D1", "D", 10)]:
            pcs[name] = conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, manager_id, starts_current_season)"
                " VALUES (?, ?, ?, 'Milan', ?, ?)",
                (lid, name, role, mid, starts),
            ).lastrowid
        hist = {}
        for name, role in [("HA1", "A"), ("HA2", "A"), ("HD1", "D"), ("HD2", "D")]:
            hist[name] = conn.execute(
                "INSERT INTO player_historic (name, role, team, season, source)"
                " VALUES (?, ?, 'Inter', '1990/91', 'archive')",
                (name, role),
            ).lastrowid
        # HA1 already on A_high; HD1 already on D1 (the only defender)
        pool = {}
        for h, pc in [("HA1", "A_high"), ("HA2", None), ("HD1", "D1"), ("HD2", None)]:
            pool[h] = conn.execute(
                "INSERT INTO manager_nostalgia_pool (manager_id, player_historic_id, assigned_player_current_id)"
                " VALUES (?, ?, ?)",
                (mid, hist[h], pcs[pc] if pc else None),
            ).lastrowid
    return lid, mid, pcs, pool


def test_complete_missing_uses_only_free_players(client):
    lid, mid, pcs, pool = _setup(client)
    r = client.post(f"/admin/league/{lid}/mapping/complete-missing")
    assert r.status_code == 200, r.text
    assert r.json()["teams"] == [{"team": "TeamM", "assigned": 1, "missing": 1}]
    with get_db() as conn:
        rows = {
            r["id"]: r["assigned_player_current_id"]
            for r in conn.execute(
                "SELECT id, assigned_player_current_id FROM manager_nostalgia_pool WHERE manager_id = ?",
                (mid,),
            )
        }
        locked = conn.execute("SELECT assignments_locked FROM manager WHERE id = ?", (mid,)).fetchone()[0]
    assert rows[pool["HA2"]] == pcs["A_low"]  # the only free attacker
    assert rows[pool["HD2"]] is None          # no free defender: no duplicate
    assert not locked                          # still incomplete


def test_complete_missing_locks_completed_team(client):
    lid, mid, pcs, pool = _setup(client)
    with get_db() as conn:
        conn.execute("DELETE FROM manager_nostalgia_pool WHERE id = ?", (pool["HD2"],))
    r = client.post(f"/admin/league/{lid}/mapping/complete-missing")
    assert r.json()["teams"] == [{"team": "TeamM", "assigned": 1, "missing": 0}]
    with get_db() as conn:
        locked = conn.execute("SELECT assignments_locked FROM manager WHERE id = ?", (mid,)).fetchone()[0]
        egos = conn.execute(
            "SELECT COUNT(*) FROM alter_ego WHERE league_id = ? AND manager_id = ?", (lid, mid)
        ).fetchone()[0]
    assert locked == 1
    assert egos == 3
    # nothing left to do
    assert client.post(f"/admin/league/{lid}/mapping/complete-missing").json()["teams"] == []
