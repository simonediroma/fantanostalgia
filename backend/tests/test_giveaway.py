import itertools
import random
import uuid

import pytest

from backend.api.db import get_db
from backend.engine.giveaway import plan_giveaway, run_giveaway


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


@pytest.fixture
def default_rules(client):
    """Rules are global: restore the defaults after a test that changes them."""
    yield
    client.put("/admin/giveaway/rules", json=[
        {"role": "A", "min_avg": 6.0, "max_avg": 7.1, "min_appearances": 0},
        {"role": "C", "min_avg": 6.0, "max_avg": 6.6, "min_appearances": 0},
        {"role": "D", "min_avg": 6.0, "max_avg": 6.3, "min_appearances": 0},
        {"role": "P", "min_avg": None, "max_avg": None, "min_appearances": 6},
    ])


_years = itertools.count(1100)


def _league(client) -> tuple[int, str]:
    """A league on a season of its own, so free historic players don't leak
    between tests (the DB is shared by the whole session)."""
    year = next(_years)
    season = f"{year}/{(year + 1) % 100:02d}"
    r = client.post("/admin/league", json={
        "name": "GiveawayLega", "season_current": "2024/25",
        "season_historic": season, "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"], season


def _manager(conn, league_id: int, name: str, roles: str, joined: bool = True) -> int:
    """Manager with one current player per letter of `roles` (e.g. "ACDP")."""
    mid = conn.execute(
        "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
        (league_id, name, f"T_{name}"),
    ).lastrowid
    for i, role in enumerate(roles):
        conn.execute(
            "INSERT INTO player_current (league_id, name, role, team, manager_id)"
            " VALUES (?, ?, ?, 'Milan', ?)",
            (league_id, f"{name}_{role}{i}", role, mid),
        )
    if joined:
        uid = conn.execute(
            "INSERT INTO user (email, name, password_hash) VALUES (?, ?, 'x')",
            (f"{name}-{uuid.uuid4().hex[:6]}@test.local", name),
        ).lastrowid
        conn.execute("UPDATE manager SET user_id = ? WHERE id = ?", (uid, mid))
    conn.execute(
        "INSERT INTO matchday_score (league_id, manager_id, matchday) VALUES (?, ?, 1)",
        (league_id, mid),
    )
    return mid


def _historic(conn, season: str, name: str, role: str, ratings: list[float]) -> int:
    hid = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source)"
        " VALUES (?, ?, 'Inter', ?, 'archive')",
        (name, role, season),
    ).lastrowid
    for md, rating in enumerate(ratings, start=1):
        conn.execute(
            "INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
            " VALUES (?, ?, ?, 'archive')",
            (hid, md, rating),
        )
    return hid


def _fill_slot(conn, league_id: int, manager_id: int, role: str, season: str) -> None:
    """Associate every current player of that role, so the manager has no free slot."""
    for pc in conn.execute(
        "SELECT id FROM player_current WHERE manager_id = ? AND role = ?", (manager_id, role)
    ).fetchall():
        hid = _historic(conn, season, f"Filler{pc['id']}", role, [])
        conn.execute(
            "INSERT INTO manager_nostalgia_pool"
            " (manager_id, league_id, player_historic_id, assigned_player_current_id)"
            " VALUES (?, ?, ?, ?)",
            (manager_id, league_id, hid, pc["id"]),
        )


def test_first_giveaway_assigns_forwards_in_band(client):
    league_id, season = _league(client)
    with get_db() as conn:
        m1 = _manager(conn, league_id, "G1", "AC")
        m2 = _manager(conn, league_id, "G2", "AC")
        ok1 = _historic(conn, season, "Ok1", "A", [6.5])
        ok2 = _historic(conn, season, "Ok2", "A", [7.0, 7.2])
        _historic(conn, season, "Top", "A", [8.0])
        _historic(conn, season, "Bad", "A", [5.5])
        _historic(conn, season, "Mid", "C", [6.2])
        conn.execute("UPDATE manager SET assignments_locked = 1 WHERE league_id = ?", (league_id,))

    r = client.post(f"/admin/league/{league_id}/giveaway/1")
    assert r.status_code == 200, r.text
    awards = r.json()["awards"]
    assert {a["manager_id"] for a in awards} == {m1, m2}
    assert {a["player_historic_id"] for a in awards} == {ok1, ok2}
    assert all(a["role"] == "A" and a["in_band"] for a in awards)

    with get_db() as conn:
        locked = conn.execute(
            "SELECT SUM(assignments_locked) AS s FROM manager WHERE league_id = ?", (league_id,)
        ).fetchone()["s"]
        pool = conn.execute(
            "SELECT COUNT(*) AS c FROM manager_nostalgia_pool WHERE league_id = ?", (league_id,)
        ).fetchone()["c"]
    assert locked == 0
    assert pool == 2


def test_sequence_rotates_and_skips_roles_without_free_slots(client):
    league_id, season = _league(client)
    with get_db() as conn:
        _manager(conn, league_id, "S1", "AAP")
        _historic(conn, season, "A1", "A", [6.5])
        _historic(conn, season, "A2", "A", [6.5])
        _historic(conn, season, "C1", "C", [6.2])
        _historic(conn, season, "P1", "P", [6.0] * 6)
        # Second scored matchday for the second run.
        conn.execute(
            "INSERT INTO matchday_score (league_id, manager_id, matchday)"
            " SELECT league_id, id, 2 FROM manager WHERE league_id = ?",
            (league_id,),
        )

        assert run_giveaway(conn, league_id, 1, random.Random(1))[0]["role"] == "A"
        # Next is C, but the manager has no midfielders nor defenders: P.
        assert run_giveaway(conn, league_id, 2, random.Random(1))[0]["role"] == "P"
        # After P the sequence restarts from A (one forward slot still free).
        assert plan_giveaway(conn, league_id)["role"] == "A"


def test_fills_with_out_of_band_players_when_band_is_short(client):
    league_id, season = _league(client)
    with get_db() as conn:
        _manager(conn, league_id, "O1", "A")
        _manager(conn, league_id, "O2", "A")
        _manager(conn, league_id, "O3", "A")
        _historic(conn, season, "InBand", "A", [6.5])
        _historic(conn, season, "Star", "A", [8.0])
        awards = run_giveaway(conn, league_id, 1, random.Random(3))

    assert len(awards) == 2  # only two free forwards: one manager stays out
    by_name = {a["name"]: a["in_band"] for a in awards}
    assert by_name == {"InBand": True, "Star": False}


def test_excludes_unjoined_and_full_managers(client):
    league_id, season = _league(client)
    with get_db() as conn:
        joined = _manager(conn, league_id, "J", "A")
        _manager(conn, league_id, "Ghost", "A", joined=False)
        full = _manager(conn, league_id, "Full", "A")
        _fill_slot(conn, league_id, full, "A", season)
        _historic(conn, season, "X1", "A", [6.5])
        _historic(conn, season, "X2", "A", [6.5])
        awards = run_giveaway(conn, league_id, 1, random.Random(0))

    assert [a["manager_id"] for a in awards] == [joined]


def test_goalkeeper_min_appearances(client):
    league_id, season = _league(client)
    with get_db() as conn:
        _manager(conn, league_id, "K1", "P")
        _historic(conn, season, "FewGames", "P", [9.0] * 5)
        regular = _historic(conn, season, "Regular", "P", [5.0] * 6)
        plan = plan_giveaway(conn, league_id)

    assert plan["role"] == "P"
    assert [p["id"] for p in plan["in_band"]] == [regular]


def test_rules_are_editable_and_validated(client, default_rules):
    r = client.put("/admin/giveaway/rules", json=[
        {"role": "A", "min_avg": 7.0, "max_avg": 6.0, "min_appearances": 0},
    ])
    assert r.status_code == 400

    r = client.put("/admin/giveaway/rules", json=[
        {"role": "A", "min_avg": 6.0, "max_avg": 6.4, "min_appearances": 3},
    ])
    assert r.status_code == 200, r.text
    rule_a = next(x for x in r.json() if x["role"] == "A")
    assert rule_a == {"role": "A", "min_avg": 6.0, "max_avg": 6.4, "min_appearances": 3}

    league_id, season = _league(client)
    with get_db() as conn:
        _manager(conn, league_id, "R1", "A")
        _historic(conn, season, "TwoGames", "A", [6.2, 6.2])
        ok = _historic(conn, season, "ThreeGames", "A", [6.2, 6.2, 6.2])
        plan = plan_giveaway(conn, league_id)
    assert [p["id"] for p in plan["in_band"]] == [ok]


def test_requires_scores_and_resolved_gran_premi(client):
    league_id, season = _league(client)
    with get_db() as conn:
        _manager(conn, league_id, "P1", "A")
        prize = _historic(conn, season, "Prize", "A", [6.5])
        conn.execute(
            "INSERT INTO gran_premio (league_id, matchday, criterion, prize_player_historic_id)"
            " VALUES (?, 1, 'best_score', ?)",
            (league_id, prize),
        )

    r = client.post(f"/admin/league/{league_id}/giveaway/2")
    assert r.status_code == 400
    assert "Punteggi" in r.json()["detail"]

    r = client.post(f"/admin/league/{league_id}/giveaway/1")
    assert r.status_code == 400
    assert "Gran Premi" in r.json()["detail"]

    preview = client.get(f"/admin/league/{league_id}/giveaway/1").json()
    assert preview["done"] is False
    assert "Gran Premi" in preview["blocker"]
    assert preview["role"] == "A"


def test_run_once_per_matchday_enqueues_email_and_blocks_delete(client):
    league_id, season = _league(client)
    with get_db() as conn:
        mid = _manager(conn, league_id, "E1", "AA")
        _historic(conn, season, "Mail1", "A", [6.5])
        _historic(conn, season, "Mail2", "A", [6.5])
        email = conn.execute(
            "SELECT u.email FROM manager m JOIN user u ON u.id = m.user_id WHERE m.id = ?", (mid,)
        ).fetchone()["email"]

    assert client.post(f"/admin/league/{league_id}/giveaway/1").status_code == 200
    r = client.post(f"/admin/league/{league_id}/giveaway/1")
    assert r.status_code == 400
    assert "già eseguita" in r.json()["detail"]

    with get_db() as conn:
        queued = conn.execute(
            "SELECT params FROM email_queue WHERE template = 'giveaway_assigned' AND to_email = ?",
            (email,),
        ).fetchall()
    assert len(queued) == 1

    preview = client.get(f"/admin/league/{league_id}/giveaway/1").json()
    assert preview["done"] is True and len(preview["awards"]) == 1
    assert len(client.get(f"/league/{league_id}/giveaway").json()) == 1

    r = client.delete(f"/admin/league/{league_id}/matchdays/1")
    assert r.status_code == 400


def test_endpoints_require_admin(client):
    client.post("/auth/logout")
    assert client.get("/admin/giveaway/rules").status_code == 401
    assert client.post("/admin/league/1/giveaway/1").status_code == 401
