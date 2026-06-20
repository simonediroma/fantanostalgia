import pytest

from backend.api.db import get_db
from backend.engine.granpremio import free_historic_players, resolve_gran_premio
from backend.engine.mapping import _flush_alter_ego_for_manager


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


def _create_league(client, season_historic: str = "2003/04") -> int:
    r = client.post("/admin/league", json={
        "name": "GPTestLega",
        "season_current": "2024/25",
        "season_historic": season_historic,
        "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _add_historic(conn, name: str, role: str, season: str = "2003/04") -> int:
    cur = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source)"
        " VALUES (?, ?, 'Milan', ?, 'archive')",
        (name, role, season),
    )
    return cur.lastrowid


def _add_rating(conn, hist_id: int, matchday: int, rating: float) -> None:
    conn.execute(
        "INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
        " VALUES (?, ?, ?, 'archive')",
        (hist_id, matchday, rating),
    )


def _add_player(conn, league_id: int, manager_id: int, name: str, role: str) -> int:
    cur = conn.execute(
        "INSERT INTO player_current (league_id, name, role, team, manager_id)"
        " VALUES (?, ?, ?, 'Milan', ?)",
        (league_id, name, role, manager_id),
    )
    return cur.lastrowid


def _setup_scored_league(client) -> dict:
    """Two managers, two starters each, archive alter egos with fixed ratings on
    historic matchday 5 (drawn for current matchday 1), scores already computed.

    Ratings (ns == rating for archive):
      M1: A1=8.0, D1=5.0  → total 13.0, defense 5.0
      M2: A2=7.0, D2=6.5  → total 13.5, defense 6.5
    Expected winners: best_score=M2, best_player=M1(A1), worst_player=M1(D1),
    worst_defense=M1.
    """
    league_id = _create_league(client)
    ctx: dict = {"league_id": league_id}

    with get_db() as conn:
        m1 = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M1', 'T1')",
            (league_id,),
        ).lastrowid
        m2 = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M2', 'T2')",
            (league_id,),
        ).lastrowid
        ctx["m1"], ctx["m2"] = m1, m2

        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
            " VALUES (?, 1, 5, 1)",
            (league_id,),
        )

        spec = [
            (m1, "A1", "A", 8.0),
            (m1, "D1", "D", 5.0),
            (m2, "A2", "A", 7.0),
            (m2, "D2", "D", 6.5),
        ]
        for mid, name, role, rating in spec:
            pc = _add_player(conn, league_id, mid, name, role)
            conn.execute(
                "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter)"
                " VALUES (?, ?, 1, ?, 1)",
                (league_id, mid, pc),
            )
            hist = _add_historic(conn, f"H_{name}", role)
            _add_rating(conn, hist, 5, rating)
            conn.execute(
                "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id)"
                " VALUES (?, ?, ?)",
                (league_id, pc, hist),
            )

        # A free historic forward, never assigned to any pool — the prize.
        ctx["prize"] = _add_historic(conn, "PrizeGuy", "A")

    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 200, r.text
    return ctx


# ── free_historic_players ─────────────────────────────────────────────────────

def test_free_historic_players_excludes_assigned(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M', 'T')",
            (league_id,),
        ).lastrowid
        h_free = _add_historic(conn, "Free One", "A")
        h_taken = _add_historic(conn, "Taken One", "A")
        conn.execute(
            "INSERT INTO manager_nostalgia_pool (manager_id, league_id, player_historic_id)"
            " VALUES (?, ?, ?)",
            (mgr, league_id, h_taken),
        )
        free = free_historic_players(conn, league_id)
        free_ids = {p["id"] for p in free}

    assert h_free in free_ids
    assert h_taken not in free_ids


def test_free_historic_players_filter_role(client):
    league_id = _create_league(client)
    with get_db() as conn:
        h_a = _add_historic(conn, "Att", "A")
        h_p = _add_historic(conn, "Por", "P")
        roles = {p["role"] for p in free_historic_players(conn, league_id, role="A")}
        ids_a = {p["id"] for p in free_historic_players(conn, league_id, role="A")}

    assert roles == {"A"}
    assert h_a in ids_a and h_p not in ids_a


# ── criteria → winner ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("criterion,expected_key", [
    ("best_score", "m2"),
    ("best_player", "m1"),
    ("worst_player", "m1"),
    ("worst_defense", "m1"),
])
def test_resolve_picks_expected_winner(client, criterion, expected_key):
    ctx = _setup_scored_league(client)
    league_id = ctx["league_id"]

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1,
        "criterion": criterion,
        "prize_player_historic_id": ctx["prize"],
    })
    assert r.status_code == 200, r.text
    gp_id = r.json()["id"]

    r = client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")
    assert r.status_code == 200, r.text
    assert r.json()["winner_manager_id"] == ctx[expected_key]


def test_resolve_awards_and_reopens(client):
    ctx = _setup_scored_league(client)
    league_id, m2 = ctx["league_id"], ctx["m2"]

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": ctx["prize"],
    })
    gp_id = r.json()["id"]
    client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")

    with get_db() as conn:
        pool = conn.execute(
            "SELECT player_historic_id, assigned_player_current_id"
            " FROM manager_nostalgia_pool WHERE manager_id = ?",
            (m2,),
        ).fetchall()
        locked = conn.execute(
            "SELECT assignments_locked FROM manager WHERE id = ?", (m2,)
        ).fetchone()["assignments_locked"]

    assert len(pool) == 1
    assert pool[0]["player_historic_id"] == ctx["prize"]
    assert pool[0]["assigned_player_current_id"] is None
    assert locked == 0


def test_won_player_flows_into_next_matchday_scoring(client):
    """Winner associates the won historic to one of their players; after flushing
    the association into alter_ego, the next matchday's scoring uses it."""
    ctx = _setup_scored_league(client)
    league_id, m2 = ctx["league_id"], ctx["m2"]

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": ctx["prize"],
    })
    gp_id = r.json()["id"]
    client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")

    with get_db() as conn:
        # M2's A2 player (a forward) gets switched onto the won historic.
        a2 = conn.execute(
            "SELECT id FROM player_current WHERE league_id = ? AND manager_id = ? AND name = 'A2'",
            (league_id, m2),
        ).fetchone()["id"]
        conn.execute(
            "UPDATE manager_nostalgia_pool SET assigned_player_current_id = ?"
            " WHERE manager_id = ? AND player_historic_id = ?",
            (a2, m2, ctx["prize"]),
        )
        # The won historic scores big on historic matchday 7.
        _add_rating(conn, ctx["prize"], 7, 9.0)
        _flush_alter_ego_for_manager(conn, league_id, m2)

        # Matchday 2 draws historic 7; M2 fields A2 as a starter.
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
            " VALUES (?, 2, 7, 1)",
            (league_id,),
        )
        conn.execute(
            "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter)"
            " VALUES (?, ?, 2, ?, 1)",
            (league_id, m2, a2),
        )

    r = client.post(f"/admin/league/{league_id}/scores/2", json={})
    assert r.status_code == 200, r.text
    m2_score = next(s for s in r.json()["scores"] if s["manager"] == "M2")
    # Only A2 fielded for M2 on md2, now mapped to the won historic (archive 9.0).
    assert m2_score["score_nostalgia"] == pytest.approx(9.0)


# ── validation ────────────────────────────────────────────────────────────────

def test_max_two_per_matchday(client):
    ctx = _setup_scored_league(client)
    league_id = ctx["league_id"]
    with get_db() as conn:
        extra1 = _add_historic(conn, "Extra1", "A")
        extra2 = _add_historic(conn, "Extra2", "A")

    for hist in (ctx["prize"], extra1):
        r = client.post(f"/admin/league/{league_id}/granpremio", json={
            "matchday": 1, "criterion": "best_score", "prize_player_historic_id": hist,
        })
        assert r.status_code == 200, r.text

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_player", "prize_player_historic_id": extra2,
    })
    assert r.status_code == 400


def test_prize_must_be_free(client):
    ctx = _setup_scored_league(client)
    league_id, m1 = ctx["league_id"], ctx["m1"]
    with get_db() as conn:
        taken = _add_historic(conn, "AlreadyTaken", "A")
        conn.execute(
            "INSERT INTO manager_nostalgia_pool (manager_id, league_id, player_historic_id)"
            " VALUES (?, ?, ?)",
            (m1, league_id, taken),
        )

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": taken,
    })
    assert r.status_code == 400


def test_invalid_criterion(client):
    ctx = _setup_scored_league(client)
    r = client.post(f"/admin/league/{ctx['league_id']}/granpremio", json={
        "matchday": 1, "criterion": "nonsense", "prize_player_historic_id": ctx["prize"],
    })
    assert r.status_code == 400


def test_resolve_requires_scores(client):
    """A Gran Premio on an unscored matchday cannot be resolved."""
    league_id = _create_league(client)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M', 'T')",
            (league_id,),
        )
        prize = _add_historic(conn, "Prize", "A")

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 9, "criterion": "best_score", "prize_player_historic_id": prize,
    })
    gp_id = r.json()["id"]
    r = client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")
    assert r.status_code == 400


def test_list_gran_premi_public(client):
    ctx = _setup_scored_league(client)
    league_id = ctx["league_id"]
    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": ctx["prize"],
    })
    gp_id = r.json()["id"]
    client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")

    r = client.get(f"/league/{league_id}/granpremio")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["criterion"] == "best_score"
    assert data[0]["status"] == "resolved"
    assert data[0]["winner_name"] == "M2"
    assert data[0]["prize_name"] == "PrizeGuy"


def test_giornata_page_shows_gran_premio(client):
    ctx = _setup_scored_league(client)
    league_id = ctx["league_id"]
    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": ctx["prize"],
    })
    gp_id = r.json()["id"]
    client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")

    r = client.get(f"/lega/{league_id}/giornata/1")
    assert r.status_code == 200, r.text
    body = r.text
    assert "Gran Premi" in body
    assert "PrizeGuy" in body
    assert "Miglior punteggio" in body
    assert "M2" in body  # winner


def test_free_players_endpoint_requires_auth(client):
    ctx = _setup_scored_league(client)
    client.post("/auth/logout")
    r = client.get(f"/admin/league/{ctx['league_id']}/granpremio/free-players")
    assert r.status_code == 401
