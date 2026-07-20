import json

import pytest

from backend.api.db import get_db
from backend.engine import market as market_engine
from backend.engine.mapping import POOL_SIZE


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")
    client.post("/auth/user/logout")


def _create_league(client, season_historic: str = "2003/04") -> int:
    r = client.post("/admin/league", json={
        "name": "MktTestLega", "season_current": "2024/25",
        "season_historic": season_historic, "budget": 500,
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


def _add_manager(conn, league_id: int, name: str = "M", team: str = "T") -> int:
    return conn.execute(
        "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
        (league_id, name, team),
    ).lastrowid


def _set_credits(conn, manager_id: int, credits: int) -> None:
    conn.execute("UPDATE manager SET credits = ? WHERE id = ?", (credits, manager_id))


def _add_to_pool(conn, manager_id, league_id, player_historic_id, assigned_pc=None) -> int:
    return conn.execute(
        "INSERT INTO manager_nostalgia_pool"
        " (manager_id, league_id, player_historic_id, assigned_player_current_id)"
        " VALUES (?, ?, ?, ?)",
        (manager_id, league_id, player_historic_id, assigned_pc),
    ).lastrowid


def _link_user(conn, manager_id: int, email: str, name: str = "Coach") -> int:
    user_id = conn.execute(
        "INSERT INTO user (email, name, password_hash) VALUES (?, ?, 'x')", (email, name)
    ).lastrowid
    conn.execute("UPDATE manager SET user_id = ? WHERE id = ?", (user_id, manager_id))
    return user_id


def _register_coach(client, league_id: int, manager_id: int, email: str, name: str = "Coach") -> None:
    invite = client.post(f"/admin/league/{league_id}/managers/{manager_id}/invite").json()
    client.post("/auth/logout")
    r = client.post("/auth/register", json={
        "name": name, "email": email, "password": "pass1234", "invite_token": invite["token"],
    })
    assert r.status_code == 201, r.text


# ── compute_cut_value ────────────────────────────────────────────────────────

def test_compute_cut_value_no_ratings_treated_as_baseline():
    with get_db() as conn:
        hid = _add_historic(conn, "NoRatings", "A")
        assert market_engine.compute_cut_value(conn, hid) == 10


def test_compute_cut_value_above_baseline():
    with get_db() as conn:
        hid = _add_historic(conn, "Good", "A")
        for md in range(1, 4):
            _add_rating(conn, hid, md, 8.0)
        assert market_engine.compute_cut_value(conn, hid) == 30


def test_compute_cut_value_floors_at_one():
    with get_db() as conn:
        hid = _add_historic(conn, "Bad", "A")
        for md in range(1, 3):
            _add_rating(conn, hid, md, 4.0)
        assert market_engine.compute_cut_value(conn, hid) == 1


def test_compute_cut_value_half_point_rounding():
    with get_db() as conn:
        hid = _add_historic(conn, "HalfPoint", "A")
        _add_rating(conn, hid, 1, 6.25)
        assert market_engine.compute_cut_value(conn, hid) == 15


# ── cut_player ───────────────────────────────────────────────────────────────

def test_cut_player_credits_and_removes_from_pool(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        hid = _add_historic(conn, "CutMe", "A")
        for md in range(1, 3):
            _add_rating(conn, hid, md, 8.0)
        _add_to_pool(conn, mgr, league_id, hid)
        dummy = _add_historic(conn, "Dummy", "A")
        market_engine.create_market_session(conn, league_id, [dummy])

        value = market_engine.cut_player(conn, league_id, mgr, hid)
        assert value == 30

        pool = conn.execute(
            "SELECT id FROM manager_nostalgia_pool WHERE manager_id = ? AND player_historic_id = ?",
            (mgr, hid),
        ).fetchone()
        assert pool is None

        credits = conn.execute("SELECT credits FROM manager WHERE id = ?", (mgr,)).fetchone()["credits"]
        assert credits == 30

        free_ids = {p["id"] for p in market_engine.free_historic_players(conn, league_id)}
        assert hid in free_ids


def test_cut_player_removes_stale_alter_ego(client):
    """A historic already flushed into alter_ego (manager already locked) must have
    that snapshot cleaned up too, not just the pool row."""
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        pc = _add_player(conn, league_id, mgr, "RealGuy", "A")
        hid = _add_historic(conn, "CutMeAssigned", "A")
        _add_to_pool(conn, mgr, league_id, hid, assigned_pc=pc)
        conn.execute(
            "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id) VALUES (?, ?, ?)",
            (league_id, pc, hid),
        )
        dummy = _add_historic(conn, "Dummy2", "A")
        market_engine.create_market_session(conn, league_id, [dummy])

        market_engine.cut_player(conn, league_id, mgr, hid)

        alter = conn.execute(
            "SELECT id FROM alter_ego WHERE league_id = ? AND player_current_id = ?",
            (league_id, pc),
        ).fetchone()
        assert alter is None


def test_cut_player_denied_without_open_session(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        hid = _add_historic(conn, "NoSession", "A")
        _add_to_pool(conn, mgr, league_id, hid)
        with pytest.raises(ValueError):
            market_engine.cut_player(conn, league_id, mgr, hid)


def test_cut_player_denied_after_cuts_closed(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        hid = _add_historic(conn, "TooLate", "A")
        _add_to_pool(conn, mgr, league_id, hid)
        dummy = _add_historic(conn, "Dummy3", "A")
        sid = market_engine.create_market_session(conn, league_id, [dummy])
        market_engine.close_cuts(conn, sid)
        with pytest.raises(ValueError):
            market_engine.cut_player(conn, league_id, mgr, hid)


# ── create_market_session ────────────────────────────────────────────────────

def test_create_market_session_rejects_non_free(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        taken = _add_historic(conn, "Taken", "A")
        _add_to_pool(conn, mgr, league_id, taken)
        with pytest.raises(ValueError):
            market_engine.create_market_session(conn, league_id, [taken])


def test_create_market_session_rejects_empty_list(client):
    league_id = _create_league(client)
    with get_db() as conn:
        with pytest.raises(ValueError):
            market_engine.create_market_session(conn, league_id, [])


def test_only_one_active_market_per_league(client):
    league_id = _create_league(client)
    with get_db() as conn:
        h1 = _add_historic(conn, "H1", "A")
        h2 = _add_historic(conn, "H2", "A")
        market_engine.create_market_session(conn, league_id, [h1])
        with pytest.raises(ValueError):
            market_engine.create_market_session(conn, league_id, [h2])


def test_new_market_allowed_after_resolve(client):
    league_id = _create_league(client)
    with get_db() as conn:
        h1 = _add_historic(conn, "H1b", "A")
        h2 = _add_historic(conn, "H2b", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        market_engine.resolve_market_session(conn, sid)

        new_sid = market_engine.create_market_session(conn, league_id, [h2])
        assert new_sid != sid


# ── place_bid ────────────────────────────────────────────────────────────────

def test_place_bid_rejects_over_credits(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 20)
        h1 = _add_historic(conn, "Expensive", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        with pytest.raises(ValueError):
            market_engine.place_bid(conn, sid, mgr, h1, 21)


def test_place_bid_counts_other_pending_bids_towards_credit_cap(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 20)
        h1 = _add_historic(conn, "A1", "A")
        h2 = _add_historic(conn, "A2", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1, h2])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, mgr, h1, 15)
        with pytest.raises(ValueError):
            market_engine.place_bid(conn, sid, mgr, h2, 10)


def test_place_bid_update_does_not_double_count(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 20)
        h1 = _add_historic(conn, "A1u", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, mgr, h1, 10)
        market_engine.place_bid(conn, sid, mgr, h1, 18)

        amount = conn.execute(
            "SELECT amount FROM market_bid WHERE market_session_id = ? AND manager_id = ? AND player_historic_id = ?",
            (sid, mgr, h1),
        ).fetchone()["amount"]
        assert amount == 18


def test_place_bid_rejects_when_no_free_role_slots(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 100)
        assert POOL_SIZE["P"] == 1
        filler = _add_historic(conn, "FillerP", "P")
        _add_to_pool(conn, mgr, league_id, filler)
        h1 = _add_historic(conn, "NewP", "P")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        with pytest.raises(ValueError):
            market_engine.place_bid(conn, sid, mgr, h1, 10)


def test_place_bid_reserves_role_slot_across_pending_bids(client):
    """1 free D slot; a second pending bid on another D listing must be rejected
    even though the first one hasn't been resolved yet (reservation, not just a
    'do you have >=1 free slot' check)."""
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 100)
        assert POOL_SIZE["D"] == 4
        for i in range(3):
            fid = _add_historic(conn, f"FillerD{i}", "D")
            _add_to_pool(conn, mgr, league_id, fid)
        d1 = _add_historic(conn, "D1", "D")
        d2 = _add_historic(conn, "D2", "D")
        sid = market_engine.create_market_session(conn, league_id, [d1, d2])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, mgr, d1, 10)
        with pytest.raises(ValueError):
            market_engine.place_bid(conn, sid, mgr, d2, 10)


def test_withdraw_bid_frees_reserved_capacity(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 100)
        h1 = _add_historic(conn, "W1", "A")
        h2 = _add_historic(conn, "W2", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1, h2])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, mgr, h1, 90)
        with pytest.raises(ValueError):
            market_engine.place_bid(conn, sid, mgr, h2, 20)

        market_engine.withdraw_bid(conn, sid, mgr, h1)
        market_engine.place_bid(conn, sid, mgr, h2, 20)  # now fits

        status = conn.execute(
            "SELECT status FROM market_bid WHERE market_session_id = ? AND manager_id = ? AND player_historic_id = ?",
            (sid, mgr, h1),
        ).fetchone()["status"]
        assert status == "withdrawn"


# ── resolve_market_session ───────────────────────────────────────────────────

def test_resolve_assigns_best_bidder_and_deducts_credits(client):
    league_id = _create_league(client)
    with get_db() as conn:
        m1 = _add_manager(conn, league_id, "M1", "T1")
        m2 = _add_manager(conn, league_id, "M2", "T2")
        _set_credits(conn, m1, 50)
        _set_credits(conn, m2, 50)
        h1 = _add_historic(conn, "Prize1", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, m1, h1, 20)
        market_engine.place_bid(conn, sid, m2, h1, 30)

        results = market_engine.resolve_market_session(conn, sid)

        assert results[0]["winner_manager_id"] == m2
        assert results[0]["amount"] == 30

        m2_credits = conn.execute("SELECT credits FROM manager WHERE id = ?", (m2,)).fetchone()["credits"]
        m1_credits = conn.execute("SELECT credits FROM manager WHERE id = ?", (m1,)).fetchone()["credits"]
        assert m2_credits == 20
        assert m1_credits == 50  # losing bid never charged

        pool = conn.execute(
            "SELECT assigned_player_current_id FROM manager_nostalgia_pool"
            " WHERE manager_id = ? AND player_historic_id = ?",
            (m2, h1),
        ).fetchone()
        assert pool is not None
        assert pool["assigned_player_current_id"] is None

        locked = conn.execute(
            "SELECT assignments_locked FROM manager WHERE id = ?", (m2,)
        ).fetchone()["assignments_locked"]
        assert locked == 0

        status = conn.execute(
            "SELECT status FROM market_session WHERE id = ?", (sid,)
        ).fetchone()["status"]
        assert status == "resolved"

        bid_statuses = {
            r["manager_id"]: r["status"]
            for r in conn.execute(
                "SELECT manager_id, status FROM market_bid WHERE market_session_id = ?", (sid,)
            ).fetchall()
        }
        assert bid_statuses[m2] == "won"
        assert bid_statuses[m1] == "lost"


def test_resolve_tie_break_lowest_manager_id(client):
    league_id = _create_league(client)
    with get_db() as conn:
        m1 = _add_manager(conn, league_id, "M1", "T1")
        m2 = _add_manager(conn, league_id, "M2", "T2")
        _set_credits(conn, m1, 50)
        _set_credits(conn, m2, 50)
        h1 = _add_historic(conn, "TieGuy", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, m2, h1, 25)
        market_engine.place_bid(conn, sid, m1, h1, 25)

        results = market_engine.resolve_market_session(conn, sid)
        assert results[0]["winner_manager_id"] == min(m1, m2)


def test_resolve_cascades_when_winner_has_no_slot_left(client):
    """Bids inserted directly (bypassing place_bid's reservation check) to simulate
    a manager who ends up with two pending bids on the same role but only one free
    slot: the higher-priority listing (creation order) wins for them, the other
    cascades to the next best offerer."""
    league_id = _create_league(client)
    with get_db() as conn:
        m1 = _add_manager(conn, league_id, "M1", "T1")
        m2 = _add_manager(conn, league_id, "M2", "T2")
        _set_credits(conn, m1, 100)
        _set_credits(conn, m2, 100)
        assert POOL_SIZE["P"] == 1
        p1 = _add_historic(conn, "P1", "P")
        p2 = _add_historic(conn, "P2", "P")
        sid = market_engine.create_market_session(conn, league_id, [p1, p2])
        market_engine.close_cuts(conn, sid)

        conn.execute(
            "INSERT INTO market_bid (market_session_id, manager_id, player_historic_id, amount, status)"
            " VALUES (?, ?, ?, 30, 'pending')",
            (sid, m1, p1),
        )
        conn.execute(
            "INSERT INTO market_bid (market_session_id, manager_id, player_historic_id, amount, status)"
            " VALUES (?, ?, ?, 25, 'pending')",
            (sid, m1, p2),
        )
        conn.execute(
            "INSERT INTO market_bid (market_session_id, manager_id, player_historic_id, amount, status)"
            " VALUES (?, ?, ?, 10, 'pending')",
            (sid, m2, p2),
        )

        results = market_engine.resolve_market_session(conn, sid)

    by_player = {r["player_historic_id"]: r for r in results}
    assert by_player[p1]["winner_manager_id"] == m1
    assert by_player[p2]["winner_manager_id"] == m2


def test_resolve_leaves_player_unsold_if_no_valid_bidder(client):
    league_id = _create_league(client)
    with get_db() as conn:
        h1 = _add_historic(conn, "Unsold", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)

        results = market_engine.resolve_market_session(conn, sid)
        assert results[0]["winner_manager_id"] is None
        assert results[0]["amount"] is None

        pool = conn.execute(
            "SELECT id FROM manager_nostalgia_pool WHERE player_historic_id = ?", (h1,)
        ).fetchone()
        assert pool is None


# ── admin router (HTTP) ───────────────────────────────────────────────────────

def test_admin_current_market_hides_amounts_during_bids_open(client):
    league_id = _create_league(client)
    with get_db() as conn:
        mgr = _add_manager(conn, league_id)
        _set_credits(conn, mgr, 50)
        h1 = _add_historic(conn, "Hidden", "A")

    r = client.post(f"/admin/league/{league_id}/market", json={"player_historic_ids": [h1]})
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    r = client.post(f"/admin/league/{league_id}/market/{sid}/close-cuts")
    assert r.status_code == 200, r.text

    with get_db() as conn:
        market_engine.place_bid(conn, sid, mgr, h1, 42)

    r = client.get(f"/admin/league/{league_id}/market/current")
    assert r.status_code == 200
    row = r.json()["listing"][0]
    assert row["bid_count"] == 1
    assert "amount" not in row


def test_market_listing_ordered_by_role_team_then_avg_rating_desc(client):
    league_id = _create_league(client)
    with get_db() as conn:
        gk = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('Keeper', 'P', 'Inter', '2003/04', 'archive')"
        ).lastrowid
        juve = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('AttJuve', 'A', 'Juve', '2003/04', 'archive')"
        ).lastrowid
        milan_hi = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('AttMilanHi', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid
        milan_lo = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('AttMilanLo', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid
        _add_rating(conn, juve, 1, 9.0)
        _add_rating(conn, milan_hi, 1, 8.0)
        _add_rating(conn, milan_lo, 1, 6.0)

    r = client.post(f"/admin/league/{league_id}/market", json={
        "player_historic_ids": [milan_lo, gk, juve, milan_hi],
    })
    assert r.status_code == 200, r.text
    listing = r.json()["listing"]
    assert [p["player_historic_id"] for p in listing] == [gk, juve, milan_hi, milan_lo]


def test_admin_resolve_enqueues_market_won_email(client):
    league_id = _create_league(client)
    with get_db() as conn:
        m1 = _add_manager(conn, league_id, "M1", "T1")
        _link_user(conn, m1, "winner_market@test.com", name="M1")
        _set_credits(conn, m1, 50)
        h1 = _add_historic(conn, "EmailPrize", "A")

    r = client.post(f"/admin/league/{league_id}/market", json={"player_historic_ids": [h1]})
    sid = r.json()["id"]
    client.post(f"/admin/league/{league_id}/market/{sid}/close-cuts")

    with get_db() as conn:
        market_engine.place_bid(conn, sid, m1, h1, 20)

    r = client.post(f"/admin/league/{league_id}/market/{sid}/resolve")
    assert r.status_code == 200, r.text

    with get_db() as conn:
        rows = conn.execute(
            "SELECT template, params FROM email_queue WHERE to_email = ?",
            ("winner_market@test.com",),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["template"] == "market_won"
    params = json.loads(rows[0]["params"])
    assert params["won_players_names"] == ["EmailPrize"]


def test_market_free_players_requires_auth(client):
    league_id = _create_league(client)
    client.post("/auth/logout")
    r = client.get(f"/admin/league/{league_id}/market/free-players")
    assert r.status_code == 401


def test_public_market_listing_shows_results_after_resolve(client):
    league_id = _create_league(client)
    with get_db() as conn:
        m1 = _add_manager(conn, league_id, "M1", "T1")
        _set_credits(conn, m1, 50)
        h1 = _add_historic(conn, "PublicPrize", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)
        market_engine.place_bid(conn, sid, m1, h1, 20)
        market_engine.resolve_market_session(conn, sid)

    r = client.get(f"/league/{league_id}/market")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["status"] == "resolved"
    assert data[0]["results"][0]["name"] == "PublicPrize"
    assert data[0]["results"][0]["manager_name"] == "M1"


# ── coach router (HTTP, thin integration) ────────────────────────────────────

def test_coach_market_requires_auth(client):
    league_id = _create_league(client)
    r = client.get(f"/coach/league/{league_id}/market")
    assert r.status_code == 401


def test_coach_cut_endpoint_via_http(client):
    league_id = _create_league(client)
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "M1", "team_name": "T1"}
    ).json()
    mgr = manager["id"]
    with get_db() as conn:
        h1 = _add_historic(conn, "HttpCut", "A")
        for md in range(1, 3):
            _add_rating(conn, h1, md, 8.0)
        _add_to_pool(conn, mgr, league_id, h1)
        dummy = _add_historic(conn, "HttpDummy", "A")
        market_engine.create_market_session(conn, league_id, [dummy])

    _register_coach(client, league_id, mgr, "cutter@test.com")
    r = client.post(f"/coach/league/{league_id}/market/cut", json={"player_historic_id": h1})
    assert r.status_code == 200, r.text
    assert r.json()["credited"] == 30
    assert r.json()["credits"] == 30
    client.post("/auth/user/logout")


def test_coach_bid_endpoint_via_http_and_validation_error(client):
    league_id = _create_league(client)
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "M1", "team_name": "T1"}
    ).json()
    mgr = manager["id"]
    with get_db() as conn:
        _set_credits(conn, mgr, 15)
        h1 = _add_historic(conn, "HttpBid", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)

    _register_coach(client, league_id, mgr, "bidder@test.com")

    r = client.post(
        f"/coach/league/{league_id}/market/bid", json={"player_historic_id": h1, "amount": 10}
    )
    assert r.status_code == 200, r.text

    r = client.post(
        f"/coach/league/{league_id}/market/bid", json={"player_historic_id": h1, "amount": 999}
    )
    assert r.status_code == 400

    r = client.delete(f"/coach/league/{league_id}/market/bid/{h1}")
    assert r.status_code == 200, r.text

    client.post("/auth/user/logout")


def test_coach_get_market_reflects_state(client):
    league_id = _create_league(client)
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "M1", "team_name": "T1"}
    ).json()
    mgr = manager["id"]
    with get_db() as conn:
        _set_credits(conn, mgr, 42)
        h1 = _add_historic(conn, "StateCheck", "A")
        sid = market_engine.create_market_session(conn, league_id, [h1])
        market_engine.close_cuts(conn, sid)

    _register_coach(client, league_id, mgr, "stater@test.com")

    r = client.get(f"/coach/league/{league_id}/market")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["credits"] == 42
    assert data["session"]["status"] == "bids_open"
    assert data["free_slots"]["A"] == POOL_SIZE["A"]
    assert len(data["listing"]) == 1

    client.post("/auth/user/logout")


def test_coach_cut_candidates_ordered_by_role_team_then_avg_rating_desc(client):
    league_id = _create_league(client)
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "M1", "team_name": "T1"}
    ).json()
    mgr = manager["id"]
    with get_db() as conn:
        gk = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('Keeper', 'P', 'Inter', '2003/04', 'archive')"
        ).lastrowid
        juve = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('AttJuve', 'A', 'Juve', '2003/04', 'archive')"
        ).lastrowid
        milan_hi = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('AttMilanHi', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid
        milan_lo = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('AttMilanLo', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid
        _add_rating(conn, juve, 1, 9.0)
        _add_rating(conn, milan_hi, 1, 8.0)
        _add_rating(conn, milan_lo, 1, 6.0)
        for hid in (gk, juve, milan_hi, milan_lo):
            _add_to_pool(conn, mgr, league_id, hid)
        dummy = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('Dummy', 'A', 'Empoli', '2003/04', 'archive')"
        ).lastrowid
        market_engine.create_market_session(conn, league_id, [dummy])

    _register_coach(client, league_id, mgr, "cutorder@test.com")

    r = client.get(f"/coach/league/{league_id}/market")
    assert r.status_code == 200, r.text
    cut_candidates = r.json()["cut_candidates"]
    assert [p["player_historic_id"] for p in cut_candidates] == [gk, juve, milan_hi, milan_lo]

    client.post("/auth/user/logout")
