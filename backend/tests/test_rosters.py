import pytest

from backend.api.db import get_db
from backend.api.routers.lineups import save_lineups
from backend.engine.rosters import RosterSyncError, sync_rosters
from backend.engine.scoring import compute_player_breakdown


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


FC_PLAYERS = [
    {"id": 1, "name": "Maignan", "fcrle": 1},
    {"id": 2, "name": "Bisseck", "fcrle": 2},
    {"id": 3, "name": "Mandas", "fcrle": 1},
    {"id": 4, "name": "Stankovic F.", "fcrle": 1},
]


def _team(fc_id, name, ids, roles=None):
    return {"id": fc_id, "n": name, "cal": ";".join(map(str, ids)), "cs": ";".join("5" for _ in ids),
            "r": roles or {"p": 0, "d": 0, "c": 0, "a": len(ids)}}


def _setup(client):
    """Stoke: Maignan (con alter ego Buffon) + Bisseck. Stars: Mandas."""
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


def _owners(conn, lid):
    return {r["name"]: r["manager_id"] for r in conn.execute(
        "SELECT name, manager_id FROM player_current WHERE league_id = ?", (lid,))}


def test_first_sync_with_empty_rosters_is_all_acquisitions(client):
    r = client.post("/admin/league", json={"name": "RoseVuote", "season_current": "2024/25",
                                           "season_historic": "2003/04", "budget": 500})
    lid = r.json()["id"]
    with get_db() as conn:
        a = conn.execute("INSERT INTO manager (league_id, name, team_name) VALUES (?, 'S', 'Stoke')",
                         (lid,)).lastrowid
        out = sync_rosters(conn, lid, [_team(10, "Stoke", [1, 2], {"p": 1, "d": 1, "c": 0, "a": 0})],
                           1, FC_PLAYERS)
        rows = conn.execute("SELECT name, role, manager_id, fc_id, quotation FROM player_current"
                            " WHERE league_id = ? ORDER BY fc_id", (lid,)).fetchall()
    assert len(out["added"]) == 2 and out["moved"] == out["released"] == []
    assert [tuple(r) for r in rows] == [("Maignan", "P", a, 1, 5), ("Bisseck", "D", a, 2, 5)]


def test_acquisition_move_release_and_alter_ego_history(client):
    lid, a, b, p, h = _setup(client)
    with get_db() as conn:
        # Giornata 1 già calcolata con Maignan e il suo alter ego Buffon
        conn.execute("INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter)"
                     " VALUES (?, ?, 1, ?, 1)", (lid, a, p["Maignan"]))
        conn.execute("INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
                     " VALUES (?, 1, 10, 1)", (lid,))
        conn.execute("INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
                     " VALUES (?, 10, 8.0, 'archive')", (h,))
        conn.execute("INSERT INTO matchday_score (league_id, manager_id, matchday, score_nostalgia)"
                     " VALUES (?, ?, 1, 8.0)", (lid, a))

        out = sync_rosters(conn, lid, [
            _team(10, "STOKE", [2, 4, 3]),  # Bisseck resta, Stankovic acquistato, Mandas da Stars
            _team(20, "Stars", [1]),        # Maignan passa a Stars
        ], 2, FC_PLAYERS)

        owners = _owners(conn, lid)
        moves = conn.execute("SELECT kind, COUNT(*) FROM roster_move WHERE league_id = ? GROUP BY kind",
                             (lid,)).fetchall()
        pool = conn.execute("SELECT manager_id, assigned_player_current_id FROM manager_nostalgia_pool"
                            " WHERE league_id = ?", (lid,)).fetchone()
        locked = conn.execute("SELECT assignments_locked FROM manager WHERE id = ?", (a,)).fetchone()[0]
        frozen = conn.execute("SELECT alter_ego_frozen, alter_ego_id FROM lineup WHERE league_id = ?",
                              (lid,)).fetchone()
        breakdown = compute_player_breakdown(conn, lid, 1)

    assert owners == {"Maignan": b, "Bisseck": a, "Mandas": a, "Stankovic F.": a}
    assert out["added"] == ["Stankovic F. → Stoke"]
    assert sorted(out["moved"]) == ["Maignan: Stoke → Stars", "Mandas: Stars → Stoke"]
    assert out["realign"] == ["Stoke"]
    assert dict(moves) == {"acquisto": 1, "spostamento": 2}
    # Alter ego libero nel pool di Stoke, da riassociare; Stars non lo eredita
    assert tuple(pool) == (a, None) and locked == 0
    # Storico della giornata 1 invariato: Maignan conta ancora come Buffon (8.0)
    assert tuple(frozen) == (1, h)
    assert [x["ns"] for x in breakdown] == [8.0]


def test_release_and_idempotent_resync(client):
    lid, a, b, p, h = _setup(client)
    payload = [_team(10, "Stoke", [2]), _team(20, "Stars", [3])]
    with get_db() as conn:
        out = sync_rosters(conn, lid, payload, 2, FC_PLAYERS)
        again = sync_rosters(conn, lid, payload, 2, FC_PLAYERS)
        owners = _owners(conn, lid)
    assert out["released"] == ["Maignan (da Stoke)"] and out["realign"] == ["Stoke"]
    assert owners["Maignan"] is None  # svincolato, non cancellato
    assert again == {"added": [], "moved": [], "released": [], "realign": []}


@pytest.mark.parametrize("teams,total,msg", [
    ([_team(10, "Stoke", [2])], 2, "Lette 1 squadre su 2"),
    ([_team(10, "Stoke", [2]), _team(20, "Stars", [])], 2, "Rosa vuota"),
    ([_team(10, "Stoke", [2]), _team(20, "Stars", [2])], 2, "in due squadre"),
    ([_team(10, "Stoke", [2], {"p": 1, "d": 1, "c": 0, "a": 0}), _team(20, "Stars", [3])], 2, "attesi"),
    ([_team(10, "Stoke", [2]), _team(30, "Ignota", [3])], 2, "non presente"),
])
def test_integrity_errors_write_nothing(client, teams, total, msg):
    lid, a, b, p, h = _setup(client)
    with get_db() as conn:
        before = _owners(conn, lid)
        with pytest.raises(RosterSyncError, match=msg):
            sync_rosters(conn, lid, teams, total, FC_PLAYERS)
        assert _owners(conn, lid) == before
        assert conn.execute("SELECT COUNT(*) FROM roster_sync_run WHERE league_id = ?", (lid,)).fetchone()[0] == 0


def test_too_many_releases_needs_force(client):
    lid, a, b, p, h = _setup(client)
    with get_db() as conn:
        for i in range(11):
            conn.execute("INSERT INTO player_current (league_id, name, role, team, manager_id)"
                         " VALUES (?, ?, 'A', 'X', ?)", (lid, f"Extra {i}", a))
        payload = [_team(10, "Stoke", [1, 2]), _team(20, "Stars", [3])]
        with pytest.raises(RosterSyncError, match="11 giocatori da svincolare"):
            sync_rosters(conn, lid, payload, 2, FC_PLAYERS)
        out = sync_rosters(conn, lid, payload, 2, FC_PLAYERS, force=True)
    assert len(out["released"]) == 11


def test_reimport_past_matchday_keeps_rosters_and_history(client):
    lid, a, b, p, h = _setup(client)
    with get_db() as conn:
        rows = [{"manager": "Stoke", "player": "Maignan", "is_starter": 1}]
        save_lineups(conn, lid, 1, rows, [], [])
        conn.execute("INSERT INTO matchday_score (league_id, manager_id, matchday, score_nostalgia)"
                     " VALUES (?, ?, 1, 6.0)", (lid, a))
        sync_rosters(conn, lid, [_team(10, "Stoke", [2]), _team(20, "Stars", [3, 1])], 2, FC_PLAYERS)
        save_lineups(conn, lid, 2, [{"manager": "Stars", "player": "Mandas", "is_starter": 1}], [], [])
        # Reimport della giornata 1 dopo la cessione di Maignan
        out = save_lineups(conn, lid, 1, rows, [], [])
        owners = _owners(conn, lid)
        lu = conn.execute("SELECT manager_id, alter_ego_frozen, alter_ego_id FROM lineup"
                          " WHERE league_id = ? AND matchday = 1", (lid,)).fetchone()
    assert owners["Maignan"] == b  # la rosa non cambia
    assert tuple(lu) == (a, 1, h)  # formazione e alter ego storici conservati
    assert out["warnings"] == []   # giornata passata: nessun avviso "non in rosa"
