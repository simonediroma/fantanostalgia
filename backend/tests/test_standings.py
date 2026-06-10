import pytest

from backend.api.db import get_db


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_league(client) -> dict:
    r = client.post("/admin/league", json={
        "name": "StandingsTestLega",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()


def _setup_full(client):
    """
    League with 2 managers, 2 scored matchdays.
    Simone scores higher nostalgia (alter ego goals).
    Marco scores higher normal (higher real rating).
    Returns (league_id, {"Simone": mid, "Marco": mid}).
    """
    league = _create_league(client)
    league_id = league["id"]

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Simone', 'TeamS')",
            (league_id,),
        )
        simone_id = cur.lastrowid

        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Marco', 'TeamM')",
            (league_id,),
        )
        marco_id = cur.lastrowid

        for mid, pname in ((simone_id, "Leao R."), (marco_id, "Ibra Z.")):
            cur = conn.execute(
                "INSERT INTO player_current (league_id, name, role, team) VALUES (?, ?, 'A', 'Milan')",
                (league_id, pname),
            )
            pid = cur.lastrowid
            for matchday in (1, 2):
                conn.execute(
                    "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter)"
                    " VALUES (?, ?, ?, ?, 1)",
                    (league_id, mid, matchday, pid),
                )

            cur2 = conn.execute(
                "INSERT INTO player_historic (name, role, team, season, source)"
                " VALUES (?, 'A', 'Milan', '2003/04', 'synthetic')",
                (f"Storico_{pname}",),
            )
            hist_id = cur2.lastrowid
            # historic rating per giornata storica 5 e 10
            conn.execute(
                "INSERT INTO historic_rating (player_historic_id, matchday, rating, goals, source)"
                " VALUES (?, 5, 7.0, 1, 'synthetic')",
                (hist_id,),
            )
            conn.execute(
                "INSERT INTO historic_rating (player_historic_id, matchday, rating, goals, source)"
                " VALUES (?, 10, 6.0, 0, 'synthetic')",
                (hist_id,),
            )
            conn.execute(
                "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id)"
                " VALUES (?, ?, ?)",
                (league_id, pid, hist_id),
            )

        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
            " VALUES (?, 1, 5, 1)",
            (league_id,),
        )
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
            " VALUES (?, 2, 10, 1)",
            (league_id,),
        )

    # Calculate scores via API (updates standings)
    r = client.post(f"/admin/league/{league_id}/scores/1", json={
        "real_ratings": [
            {"player_name": "Leao R.", "rating": 7.0, "goals": 1},
            {"player_name": "Ibra Z.", "rating": 8.0, "goals": 2},
        ]
    })
    assert r.status_code == 200, r.text

    r = client.post(f"/admin/league/{league_id}/scores/2", json={
        "real_ratings": [
            {"player_name": "Leao R.", "rating": 6.5},
            {"player_name": "Ibra Z.", "rating": 7.0},
        ]
    })
    assert r.status_code == 200, r.text

    return league_id, {"Simone": simone_id, "Marco": marco_id}


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


# ── GET /league/{id}/standings ────────────────────────────────────────────────

def test_standings_empty(client):
    league = _create_league(client)
    r = client.get(f"/league/{league['id']}/standings")
    assert r.status_code == 200
    data = r.json()
    assert data["league"]["name"] == "StandingsTestLega"
    assert data["league"]["season_current"] == "2024/25"
    assert data["last_matchday"] == 0
    assert data["normal"] == []
    assert data["nostalgia"] == []


def test_standings_league_not_found(client):
    r = client.get("/league/99999/standings")
    assert r.status_code == 404


def test_standings_with_scores(client):
    league_id, _ = _setup_full(client)
    r = client.get(f"/league/{league_id}/standings")
    assert r.status_code == 200
    data = r.json()

    assert data["last_matchday"] == 2
    assert len(data["normal"]) == 2
    assert len(data["nostalgia"]) == 2

    # ranks are 1-based, sorted ascending
    assert data["normal"][0]["rank"] == 1
    assert data["normal"][1]["rank"] == 2
    assert data["nostalgia"][0]["rank"] == 1
    assert data["nostalgia"][1]["rank"] == 2

    # all required fields present
    for item in data["normal"]:
        assert "manager" in item
        assert "total" in item
        assert "last_matchday" in item


def test_standings_no_auth_required(client):
    league_id, _ = _setup_full(client)
    client.post("/auth/logout")
    r = client.get(f"/league/{league_id}/standings")
    assert r.status_code == 200


# ── GET /league/{id}/standings/{manager_name} ──────────────────────────────────

def test_manager_standings_ok(client):
    league_id, _ = _setup_full(client)
    r = client.get(f"/league/{league_id}/standings/Simone")
    assert r.status_code == 200
    data = r.json()

    assert data["manager"] == "Simone"
    assert len(data["matchdays"]) == 2
    assert data["matchdays"][0]["matchday_current"] == 1
    assert data["matchdays"][0]["matchday_historic"] == 5
    assert data["matchdays"][1]["matchday_current"] == 2
    assert data["matchdays"][1]["matchday_historic"] == 10
    assert data["total_nostalgia"] > 0
    assert data["rank_nostalgia"] in (1, 2)
    assert data["rank_normal"] in (1, 2)


def test_manager_standings_matchday_scores(client):
    league_id, _ = _setup_full(client)
    r = client.get(f"/league/{league_id}/standings/Simone")
    data = r.json()
    for md in data["matchdays"]:
        assert md["score_normal"] is not None
        assert md["score_nostalgia"] is not None


def test_manager_standings_not_found(client):
    league = _create_league(client)
    r = client.get(f"/league/{league['id']}/standings/Inesistente")
    assert r.status_code == 404


def test_manager_standings_league_not_found(client):
    r = client.get("/league/99999/standings/Simone")
    assert r.status_code == 404


def test_manager_standings_no_scores(client):
    """Manager exists but no matchday scores yet."""
    league = _create_league(client)
    league_id = league["id"]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Solo', 'T')",
            (league_id,),
        )
    r = client.get(f"/league/{league_id}/standings/Solo")
    assert r.status_code == 200
    data = r.json()
    assert data["matchdays"] == []
    assert data["total_normal"] == 0.0
    assert data["total_nostalgia"] == 0.0
    assert data["rank_normal"] is None
    assert data["rank_nostalgia"] is None


def test_manager_standings_no_auth_required(client):
    league_id, _ = _setup_full(client)
    client.post("/auth/logout")
    r = client.get(f"/league/{league_id}/standings/Simone")
    assert r.status_code == 200


# ── GET /league/{id}/last-draw ────────────────────────────────────────────────

def test_last_draw_no_draws(client):
    league = _create_league(client)
    r = client.get(f"/league/{league['id']}/last-draw")
    assert r.status_code == 404


def test_last_draw_ok(client):
    league_id, _ = _setup_full(client)
    r = client.get(f"/league/{league_id}/last-draw")
    assert r.status_code == 200
    data = r.json()
    assert data["matchday_current"] == 2
    assert data["matchday_historic"] == 10
    assert "drawn_at" in data


def test_last_draw_league_not_found(client):
    r = client.get("/league/99999/last-draw")
    assert r.status_code == 404


def test_last_draw_no_auth_required(client):
    league = _create_league(client)
    client.post("/auth/logout")
    # 404 because no draw exists — but not a 401
    r = client.get(f"/league/{league['id']}/last-draw")
    assert r.status_code == 404
