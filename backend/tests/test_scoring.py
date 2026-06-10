import pytest

from backend.engine.scoring import _formula


# ── Unit tests — _formula ─────────────────────────────────────────────────────

def test_formula_base_only():
    assert _formula(6.5, "C", 0, 0, 0, 0, 0, 0, 0) == pytest.approx(6.5)


def test_formula_goal_attaccante():
    assert _formula(6.0, "A", 1, 0, 0, 0, 0, 0, 0) == pytest.approx(9.0)


def test_formula_goal_centrocampista():
    assert _formula(6.0, "C", 1, 0, 0, 0, 0, 0, 0) == pytest.approx(9.5)


def test_formula_goal_difensore():
    # 6.0 + 4.0 (goal D) + 0.5 (clean sheet, goals_conceded=0) = 10.5
    assert _formula(6.0, "D", 1, 0, 0, 0, 0, 0, 0) == pytest.approx(10.5)


def test_formula_assist():
    assert _formula(6.0, "A", 0, 1, 0, 0, 0, 0, 0) == pytest.approx(7.0)


def test_formula_yellow_card():
    assert _formula(6.0, "C", 0, 0, 1, 0, 0, 0, 0) == pytest.approx(5.5)


def test_formula_red_card():
    assert _formula(6.0, "C", 0, 0, 0, 1, 0, 0, 0) == pytest.approx(5.0)


def test_formula_own_goal():
    # Use A so no clean sheet bonus; own goal → -1.0
    assert _formula(6.0, "A", 0, 0, 0, 0, 1, 0, 0) == pytest.approx(5.0)


def test_formula_penalty_missed():
    assert _formula(6.0, "A", 0, 0, 0, 0, 0, 1, 0) == pytest.approx(3.0)


def test_formula_clean_sheet_portiere():
    assert _formula(6.0, "P", 0, 0, 0, 0, 0, 0, 0, minutes_ge_60=True) == pytest.approx(7.0)


def test_formula_clean_sheet_portiere_short_game():
    # < 60 min: no clean sheet bonus
    assert _formula(6.0, "P", 0, 0, 0, 0, 0, 0, 0, minutes_ge_60=False) == pytest.approx(6.0)


def test_formula_clean_sheet_difensore():
    assert _formula(6.0, "D", 0, 0, 0, 0, 0, 0, 0, minutes_ge_60=True) == pytest.approx(6.5)


def test_formula_goals_conceded_portiere():
    # 2 gol subiti → -1.0
    assert _formula(6.0, "P", 0, 0, 0, 0, 0, 0, 2, minutes_ge_60=True) == pytest.approx(5.0)


def test_formula_goals_conceded_odd():
    # 3 gol subiti → -1.0 (floor division 3//2 = 1)
    assert _formula(6.0, "P", 0, 0, 0, 0, 0, 0, 3, minutes_ge_60=True) == pytest.approx(5.0)


def test_formula_penalty_saved():
    assert _formula(6.0, "P", 0, 0, 0, 0, 0, 0, 0, penalties_saved=1) == pytest.approx(8.0)


def test_formula_no_bonus():
    # With apply_bonus=False: only malus applied, no goals/assist bonus
    result = _formula(6.0, "A", goals=1, assists=1, yellow_cards=1,
                      red_cards=0, own_goals=0, penalties_missed=0,
                      goals_conceded=0, apply_bonus=False)
    assert result == pytest.approx(5.5)  # 6.0 - 0.5 (yellow), no goal/assist bonus


def test_formula_no_bonus_portiere_goals_conceded():
    # Even without bonus, portiere goals_conceded malus applies
    result = _formula(6.0, "P", goals=0, assists=0, yellow_cards=0,
                      red_cards=0, own_goals=0, penalties_missed=0,
                      goals_conceded=2, apply_bonus=False)
    assert result == pytest.approx(5.0)


# ── Integration helpers ───────────────────────────────────────────────────────

def _setup_league(conn) -> tuple[int, int, int]:
    """Create league, one manager, one player_current. Returns (league_id, manager_id, player_id)."""
    cur = conn.execute(
        "INSERT INTO league (name, season_current, season_historic) VALUES ('TestLega', '2024/25', '2003/04')"
    )
    league_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Simone', 'LaSquadra')",
        (league_id,),
    )
    manager_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO player_current (league_id, name, role, team) VALUES (?, 'Leao R.', 'A', 'Milan')",
        (league_id,),
    )
    player_id = cur.lastrowid
    return league_id, manager_id, player_id


def _add_historic_player(conn, name: str, role: str, season: str = "2003/04") -> int:
    cur = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, ?, 'Milan', ?, 'synthetic')",
        (name, role, season),
    )
    return cur.lastrowid


def _add_historic_rating(conn, player_historic_id: int, matchday: int, **kwargs) -> None:
    defaults = dict(rating=6.0, goals=0, assists=0, yellow_cards=0, red_cards=0,
                    own_goals=0, penalties_scored=0, penalties_missed=0,
                    goals_conceded=0, source="synthetic")
    defaults.update(kwargs)
    conn.execute(
        """INSERT INTO historic_rating
           (player_historic_id, matchday, rating, goals, assists, yellow_cards, red_cards,
            own_goals, penalties_scored, penalties_missed, goals_conceded, source)
           VALUES (:player_historic_id, :matchday, :rating, :goals, :assists, :yellow_cards,
                   :red_cards, :own_goals, :penalties_scored, :penalties_missed, :goals_conceded, :source)""",
        {"player_historic_id": player_historic_id, "matchday": matchday, **defaults},
    )


# ── Integration tests — POST /admin/league/{id}/scores/{matchday} ─────────────

@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


def _create_league(client, season_historic: str = "2003/04") -> int:
    r = client.post("/admin/league", json={
        "name": "ScoringTestLega",
        "season_current": "2024/25",
        "season_historic": season_historic,
        "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _full_setup(client, with_alter_ego: bool = True):
    """
    Create league + manager + player + draw + optional alter ego + lineup.
    Returns (league_id, manager_id, player_current_id).
    """
    from backend.api.db import get_db

    league_id = _create_league(client)

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Simone', 'LaSquadra')",
            (league_id,),
        )
        manager_id = cur.lastrowid

        cur = conn.execute(
            "INSERT INTO player_current (league_id, name, role, team) VALUES (?, 'Leao R.', 'A', 'Milan')",
            (league_id,),
        )
        player_id = cur.lastrowid

        # Insert lineup for matchday 1
        conn.execute(
            "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter) VALUES (?, ?, 1, ?, 1)",
            (league_id, manager_id, player_id),
        )

        # Draw matchday 1 → historic 5
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle) VALUES (?, 1, 5, 1)",
            (league_id,),
        )

        if with_alter_ego:
            hist_id = _add_historic_player(conn, "Shevchenko A.", "A")
            _add_historic_rating(conn, hist_id, 5, rating=7.0, goals=1, source="synthetic")
            conn.execute(
                "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id) VALUES (?, ?, ?)",
                (league_id, player_id, hist_id),
            )

    return league_id, manager_id, player_id


def test_scores_with_alter_ego_synthetic(client):
    league_id, manager_id, _ = _full_setup(client, with_alter_ego=True)

    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["matchday"] == 1
    assert data["matchday_historic"] == 5
    scores = data["scores"]
    assert len(scores) == 1
    s = scores[0]
    assert s["manager"] == "Simone"
    assert s["score_normal"] is None  # no real_ratings provided
    # 7.0 base + 3.0 goal (A) = 10.0
    assert s["score_nostalgia"] == pytest.approx(10.0)


def test_scores_with_real_ratings(client):
    league_id, _, _ = _full_setup(client, with_alter_ego=True)

    r = client.post(f"/admin/league/{league_id}/scores/1", json={
        "real_ratings": [
            {"player_name": "Leao R.", "rating": 7.5, "goals": 1}
        ]
    })
    assert r.status_code == 200, r.text
    data = r.json()
    scores = data["scores"]
    assert len(scores) == 1
    s = scores[0]
    # Normal: 7.5 + 3.0 (goal A) = 10.5
    assert s["score_normal"] == pytest.approx(10.5)
    # Nostalgia: alter ego (synthetic 7.0 + 3.0 goal A) = 10.0
    assert s["score_nostalgia"] == pytest.approx(10.0)


def test_scores_no_alter_ego_fallback(client):
    """Player with no alter ego and no real_ratings → nostalgia score = 6.0."""
    league_id, _, _ = _full_setup(client, with_alter_ego=False)

    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 200, r.text
    s = r.json()["scores"][0]
    assert s["score_nostalgia"] == pytest.approx(6.0)


def test_scores_no_alter_ego_with_real_rating(client):
    """Player with no alter ego: nostalgia = real rating with only malus (no bonus)."""
    league_id, _, _ = _full_setup(client, with_alter_ego=False)

    r = client.post(f"/admin/league/{league_id}/scores/1", json={
        "real_ratings": [
            {"player_name": "Leao R.", "rating": 7.0, "goals": 1, "yellow_cards": 1}
        ]
    })
    assert r.status_code == 200, r.text
    s = r.json()["scores"][0]
    # Nostalgia (no bonus): 7.0 - 0.5 (yellow) = 6.5
    assert s["score_nostalgia"] == pytest.approx(6.5)
    # Normal (full bonus): 7.0 + 3.0 (goal A) - 0.5 (yellow) = 9.5
    assert s["score_normal"] == pytest.approx(9.5)


def test_scores_alter_ego_sv(client):
    """Alter ego exists but no historic_rating for that matchday → 6.0 (sv)."""
    from backend.api.db import get_db

    league_id = _create_league(client)

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Alice', 'Squadra')",
            (league_id,),
        )
        manager_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO player_current (league_id, name, role, team) VALUES (?, 'Ronaldo R.', 'A', 'Real')",
            (league_id,),
        )
        player_id = cur.lastrowid
        conn.execute(
            "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter) VALUES (?, ?, 1, ?, 1)",
            (league_id, manager_id, player_id),
        )
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle) VALUES (?, 1, 10, 1)",
            (league_id,),
        )
        hist_id = _add_historic_player(conn, "Del Piero A.", "A")
        # No historic_rating inserted for matchday 10 → sv
        conn.execute(
            "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id) VALUES (?, ?, ?)",
            (league_id, player_id, hist_id),
        )

    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 200, r.text
    s = r.json()["scores"][0]
    assert s["score_nostalgia"] == pytest.approx(6.0)


def test_scores_alter_ego_archive(client):
    """Archive-sourced historic rating: vote used as-is, no formula applied."""
    from backend.api.db import get_db

    league_id = _create_league(client)

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'Bob', 'Team')",
            (league_id,),
        )
        manager_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO player_current (league_id, name, role, team) VALUES (?, 'Dybala P.', 'A', 'Roma')",
            (league_id,),
        )
        player_id = cur.lastrowid
        conn.execute(
            "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter) VALUES (?, ?, 1, ?, 1)",
            (league_id, manager_id, player_id),
        )
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle) VALUES (?, 1, 3, 1)",
            (league_id,),
        )
        hist_id = _add_historic_player(conn, "Totti F.", "A")
        # Archive source: goals are already baked into rating
        _add_historic_rating(conn, hist_id, 3, rating=8.5, goals=2, source="archive")
        conn.execute(
            "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id) VALUES (?, ?, ?)",
            (league_id, player_id, hist_id),
        )

    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 200, r.text
    s = r.json()["scores"][0]
    # Archive: score = 8.5 (no formula applied)
    assert s["score_nostalgia"] == pytest.approx(8.5)


def test_scores_idempotent(client):
    league_id, _, _ = _full_setup(client)

    r1 = client.post(f"/admin/league/{league_id}/scores/1", json={})
    r2 = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["scores"][0]["score_nostalgia"] == r2.json()["scores"][0]["score_nostalgia"]


def test_scores_no_draw(client):
    from backend.api.db import get_db

    league_id = _create_league(client)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M', 'T')", (league_id,)
        )
    r = client.post(f"/admin/league/{league_id}/scores/99", json={})
    assert r.status_code == 400


def test_scores_league_not_found(client):
    r = client.post("/admin/league/99999/scores/1", json={})
    assert r.status_code == 404


def test_scores_requires_auth(client):
    league_id = _create_league(client)
    client.post("/auth/logout")
    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 401


def test_standings_updated_after_scores(client):
    """After calculating scores, standings should reflect the totals."""
    from backend.api.db import get_db

    league_id, manager_id, _ = _full_setup(client)

    client.post(f"/admin/league/{league_id}/scores/1", json={})

    with get_db() as conn:
        row = conn.execute(
            "SELECT total_score_nostalgia, rank_nostalgia FROM standings WHERE league_id = ? AND manager_id = ?",
            (league_id, manager_id),
        ).fetchone()
    assert row is not None
    assert row["total_score_nostalgia"] == pytest.approx(10.0)
    assert row["rank_nostalgia"] == 1


# ── GET /league/{id}/scores/{matchday} ────────────────────────────────────────

def test_get_scores_empty(client):
    league_id = _create_league(client)
    r = client.get(f"/league/{league_id}/scores/1")
    assert r.status_code == 200
    assert r.json() == []


def test_get_scores_ok(client):
    league_id, _, _ = _full_setup(client)
    client.post(f"/admin/league/{league_id}/scores/1", json={})

    r = client.get(f"/league/{league_id}/scores/1")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["manager"] == "Simone"
    assert "score_nostalgia" in data[0]


def test_get_scores_league_not_found(client):
    r = client.get("/league/99999/scores/1")
    assert r.status_code == 404
