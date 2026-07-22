import pytest

from backend.api.db import get_db


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")
    client.post("/auth/user/logout")


def _create_league(client, season_historic: str = "2003/04") -> int:
    r = client.post("/admin/league", json={
        "name": "StatTestLega", "season_current": "2024/25",
        "season_historic": season_historic, "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _add_historic(conn, name: str, role: str, season: str = "2003/04", team: str = "Milan") -> int:
    cur = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source)"
        " VALUES (?, ?, ?, ?, 'archive')",
        (name, role, team, season),
    )
    return cur.lastrowid


def _add_rating(conn, hist_id: int, matchday: int, **kwargs) -> None:
    fields = {
        "rating": 6.0, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0,
        "own_goals": 0, "penalties_scored": 0, "penalties_missed": 0,
        "goals_conceded": 0, "minutes": 90,
    }
    fields.update(kwargs)
    conn.execute(
        """
        INSERT INTO historic_rating
            (player_historic_id, matchday, rating, goals, assists, yellow_cards, red_cards,
             own_goals, penalties_scored, penalties_missed, goals_conceded, minutes, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'archive')
        """,
        (
            hist_id, matchday, fields["rating"], fields["goals"], fields["assists"],
            fields["yellow_cards"], fields["red_cards"], fields["own_goals"],
            fields["penalties_scored"], fields["penalties_missed"], fields["goals_conceded"],
            fields["minutes"],
        ),
    )


def _add_player_current(conn, league_id: int, manager_id: int, name: str, role: str) -> int:
    cur = conn.execute(
        "INSERT INTO player_current (league_id, name, role, team, manager_id)"
        " VALUES (?, ?, ?, 'Milan', ?)",
        (league_id, name, role, manager_id),
    )
    return cur.lastrowid


def _add_to_pool(conn, manager_id: int, league_id: int, player_historic_id: int, assigned_pc=None) -> int:
    return conn.execute(
        "INSERT INTO manager_nostalgia_pool"
        " (manager_id, league_id, player_historic_id, assigned_player_current_id)"
        " VALUES (?, ?, ?, ?)",
        (manager_id, league_id, player_historic_id, assigned_pc),
    ).lastrowid


def _register_coach(client, league_id: int, email: str, name: str = "Coach") -> int:
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": name, "team_name": f"{name} FC"}
    ).json()
    invite = client.post(f"/admin/league/{league_id}/managers/{manager['id']}/invite").json()
    client.post("/auth/logout")
    r = client.post("/auth/register", json={
        "name": name, "email": email, "password": "pass1234", "invite_token": invite["token"],
    })
    assert r.status_code == 201, r.text
    return manager["id"]


def test_statistiche_storiche_requires_auth(client):
    league_id = _create_league(client)
    r = client.get(f"/coach/league/{league_id}/statistiche-storiche")
    assert r.status_code == 401


def test_statistiche_storiche_ordered_by_avg_rating_desc_with_full_stats(client):
    league_id = _create_league(client)
    with get_db() as conn:
        hi = _add_historic(conn, "HighGuy", "A")
        _add_rating(conn, hi, 1, rating=9.0, goals=2, assists=1, yellow_cards=1, minutes=90)
        _add_rating(conn, hi, 2, rating=7.0, goals=1, minutes=90)

        lo = _add_historic(conn, "LowGuy", "A")
        _add_rating(conn, lo, 1, rating=5.0, red_cards=1, own_goals=1, minutes=90)

        keeper = _add_historic(conn, "Keeper", "P")
        _add_rating(conn, keeper, 1, rating=6.5, penalties_scored=0, goals_conceded=2, minutes=90)

    _register_coach(client, league_id, "coach_stats@test.com")

    r = client.get(f"/coach/league/{league_id}/statistiche-storiche")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["league"]["season_historic"] == "2003/04"

    mine = {hi: None, lo: None, keeper: None}
    for p in data["players"]:
        if p["id"] in mine:
            mine[p["id"]] = p

    ids_in_order = [p["id"] for p in data["players"] if p["id"] in mine]
    assert ids_in_order == [hi, keeper, lo]

    high = mine[hi]
    assert high["matches_played"] == 2
    assert high["avg_rating"] == 8.0
    assert high["goals"] == 3
    assert high["yellow_cards"] == 1
    assert high["minutes"] == 180
    assert "assists" not in high

    low = mine[lo]
    assert low["red_cards"] == 1
    assert low["own_goals"] == 1

    kp = mine[keeper]
    assert kp["goals_conceded"] == 2

    client.post("/auth/user/logout")


def test_statistiche_storiche_scoped_to_league_season(client):
    league_a = _create_league(client, season_historic="2003/04")
    with get_db() as conn:
        other_season = _add_historic(conn, "OtherSeasonGuy", "A", season="1999/00")
        _add_rating(conn, other_season, 1, rating=9.5)

    _register_coach(client, league_a, "coach_scope@test.com")

    r = client.get(f"/coach/league/{league_a}/statistiche-storiche")
    assert r.status_code == 200, r.text
    ids = {p["id"] for p in r.json()["players"]}
    assert other_season not in ids

    client.post("/auth/user/logout")


def test_statistiche_storiche_includes_players_without_ratings(client):
    league_id = _create_league(client)
    with get_db() as conn:
        no_ratings = _add_historic(conn, "NeverPlayed", "D")

    _register_coach(client, league_id, "coach_norating@test.com")

    r = client.get(f"/coach/league/{league_id}/statistiche-storiche")
    assert r.status_code == 200, r.text
    row = next(p for p in r.json()["players"] if p["id"] == no_ratings)
    assert row["matches_played"] == 0
    assert row["avg_rating"] is None
    assert row["goals"] == 0
    assert row["associations"] == []

    client.post("/auth/user/logout")


def test_statistiche_storiche_shows_association_to_current_player(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr_id = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M1', 'T1')",
            (league_id,),
        ).lastrowid
        hist = _add_historic(conn, "AssociatedGuy", "A")
        pc = _add_player_current(conn, league_id, mgr_id, "RealPlayer", "A")
        _add_to_pool(conn, mgr_id, league_id, hist, assigned_pc=pc)

    _register_coach(client, league_id, "coach_assoc@test.com")

    r = client.get(f"/coach/league/{league_id}/statistiche-storiche")
    assert r.status_code == 200, r.text
    row = next(p for p in r.json()["players"] if p["id"] == hist)
    assert row["associations"] == ["RealPlayer (M1)"]

    client.post("/auth/user/logout")


def test_statistiche_storiche_duplicate_pool_does_not_inflate_stats(client):
    """A historic player duplicated across two managers' pools must not have its
    matches/goals doubled by the association lookup (join-multiplication bug the
    two-query design avoids)."""
    league_id = _create_league(client)
    with get_db() as conn:
        m1 = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M1', 'T1')",
            (league_id,),
        ).lastrowid
        m2 = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M2', 'T2')",
            (league_id,),
        ).lastrowid
        hist = _add_historic(conn, "DupeGuy", "A")
        _add_rating(conn, hist, 1, rating=7.0, goals=1)
        _add_rating(conn, hist, 2, rating=9.0, goals=2)

        pc1 = _add_player_current(conn, league_id, m1, "Real1", "A")
        pc2 = _add_player_current(conn, league_id, m2, "Real2", "A")
        _add_to_pool(conn, m1, league_id, hist, assigned_pc=pc1)
        _add_to_pool(conn, m2, league_id, hist, assigned_pc=pc2)

    _register_coach(client, league_id, "coach_dupe@test.com")

    r = client.get(f"/coach/league/{league_id}/statistiche-storiche")
    assert r.status_code == 200, r.text
    row = next(p for p in r.json()["players"] if p["id"] == hist)
    assert row["matches_played"] == 2
    assert row["goals"] == 3
    assert row["avg_rating"] == 8.0
    assert sorted(row["associations"]) == ["Real1 (M1)", "Real2 (M2)"]

    client.post("/auth/user/logout")
