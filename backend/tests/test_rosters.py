import pytest

from backend.api.db import get_db
from backend.engine.rosters import sync_rosters


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


def _setup(client):
    r = client.post("/admin/league", json={"name": "RoseSync", "season_current": "2024/25",
                                           "season_historic": "2003/04", "budget": 500})
    lid = r.json()["id"]
    with get_db() as conn:
        a = conn.execute("INSERT INTO manager (league_id, name, team_name, assignments_locked)"
                         " VALUES (?, 'Simone', 'Stoke', 1)", (lid,)).lastrowid
        b = conn.execute("INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Paolo', 'Stars')",
                         (lid,)).lastrowid
        p = {}
        for name, role, mid in (("Maignan", "P", a), ("Bisseck", "D", a), ("Mandas", "P", b)):
            p[name] = conn.execute("INSERT INTO player_current (league_id, name, role, team, manager_id)"
                                   " VALUES (?, ?, ?, 'X', ?)", (lid, name, role, mid)).lastrowid
        h = conn.execute("INSERT INTO player_historic (name, role, team, season, source)"
                         " VALUES ('Buffon', 'P', 'Juve', '2003/04', 'archive')").lastrowid
        conn.execute("INSERT INTO manager_nostalgia_pool (manager_id, league_id, player_historic_id,"
                     " assigned_player_current_id) VALUES (?, ?, ?, ?)", (a, lid, h, p["Maignan"]))
        conn.execute("INSERT INTO alter_ego (league_id, player_current_id, player_historic_id)"
                     " VALUES (?, ?, ?)", (lid, p["Maignan"], h))
    return lid, a, b, p, h


def test_sync_adds_moves_releases_and_frees_alter_ego(client):
    lid, a, b, p, h = _setup(client)
    with get_db() as conn:
        out = sync_rosters(conn, lid, {
            "STOKE": [{"name": "Bisseck", "role": "D"}, {"name": "Stankovic F.", "role": "P"},
                      {"name": "Mandas", "role": "P"}],
            "Stars": [],
            "Ignota": [{"name": "X", "role": "A"}],
        })
        owners = {r["name"]: r["manager_id"] for r in conn.execute(
            "SELECT name, manager_id FROM player_current WHERE league_id = ?", (lid,))}
        pool = conn.execute("SELECT manager_id, assigned_player_current_id FROM manager_nostalgia_pool"
                            " WHERE league_id = ?", (lid,)).fetchone()
        ae = conn.execute("SELECT COUNT(*) FROM alter_ego WHERE league_id = ?", (lid,)).fetchone()[0]
        locked = conn.execute("SELECT assignments_locked FROM manager WHERE id = ?", (a,)).fetchone()[0]

    assert owners == {"Maignan": None, "Bisseck": a, "Mandas": a, "Stankovic F.": a}
    assert out["added"] == ["Stankovic F. → Stoke"]
    assert out["moved"] == ["Mandas: Stars → Stoke"]
    assert out["released"] == ["Maignan (da Stoke)"]
    assert any("Ignota" in w for w in out["warnings"])
    # L'alter ego resta nel pool di Stoke, libero da riassociare
    assert tuple(pool) == (a, None) and ae == 0 and locked == 0


def test_sync_ignores_teams_not_in_payload(client):
    lid, a, b, p, h = _setup(client)
    with get_db() as conn:
        out = sync_rosters(conn, lid, {"Stars": [{"name": "Mandas", "role": "P"}]})
        owner = conn.execute("SELECT manager_id FROM player_current WHERE id = ?", (p["Maignan"],)).fetchone()[0]
    assert owner == a and out["released"] == [] and out["moved"] == []
