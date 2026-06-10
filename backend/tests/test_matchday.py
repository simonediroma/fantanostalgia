import pytest

from backend.engine.draw import get_season_matchday_count


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_league(client, season_historic: str = "2003/04") -> int:
    r = client.post("/admin/league", json={
        "name": "DrawTestLega",
        "season_current": "2024/25",
        "season_historic": season_historic,
        "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


# ── Unit tests — get_season_matchday_count ────────────────────────────────────

def test_season_matchday_count():
    assert get_season_matchday_count("1980/81") == 30
    assert get_season_matchday_count("1987/88") == 30
    assert get_season_matchday_count("1988/89") == 34
    assert get_season_matchday_count("2003/04") == 34
    assert get_season_matchday_count("2004/05") == 38
    assert get_season_matchday_count("2023/24") == 38


# ── POST /admin/league/{id}/draw/{matchday} ───────────────────────────────────

def test_draw_ok(client):
    league_id = _create_league(client, "2003/04")
    r = client.post(f"/admin/league/{league_id}/draw/1")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["matchday_current"] == 1
    assert 1 <= data["matchday_historic"] <= 34
    assert data["cycle"] == 1
    assert data["drawn_at"] is not None


def test_draw_idempotent(client):
    league_id = _create_league(client, "2003/04")
    r1 = client.post(f"/admin/league/{league_id}/draw/1")
    r2 = client.post(f"/admin/league/{league_id}/draw/1")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["matchday_historic"] == r2.json()["matchday_historic"]
    assert r1.json()["cycle"] == r2.json()["cycle"]
    assert r1.json()["drawn_at"] == r2.json()["drawn_at"]


def test_draw_no_repeats_in_cycle(client):
    league_id = _create_league(client, "2003/04")
    drawn = []
    for matchday in range(1, 35):
        r = client.post(f"/admin/league/{league_id}/draw/{matchday}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cycle"] == 1
        drawn.append(data["matchday_historic"])
    # All 34 historic matchdays used exactly once
    assert sorted(drawn) == list(range(1, 35))


def test_draw_cycle_rollover(client):
    # 1987/88 → 30 matchdays; the 31st draw must start cycle 2
    league_id = _create_league(client, "1987/88")
    for matchday in range(1, 31):
        r = client.post(f"/admin/league/{league_id}/draw/{matchday}")
        assert r.status_code == 200
        assert r.json()["cycle"] == 1

    r = client.post(f"/admin/league/{league_id}/draw/31")
    assert r.status_code == 200
    data = r.json()
    assert data["cycle"] == 2
    assert 1 <= data["matchday_historic"] <= 30


def test_draw_league_not_found(client):
    r = client.post("/admin/league/99999/draw/1")
    assert r.status_code == 404


def test_draw_requires_auth(client):
    league_id = _create_league(client, "2003/04")
    client.post("/auth/logout")
    r = client.post(f"/admin/league/{league_id}/draw/1")
    assert r.status_code == 401


def test_draw_bearer_token_ok(client):
    league_id = _create_league(client, "2003/04")
    client.post("/auth/logout")
    r = client.post(
        f"/admin/league/{league_id}/draw/1",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["matchday_current"] == 1


def test_draw_bearer_token_wrong(client):
    league_id = _create_league(client, "2003/04")
    client.post("/auth/logout")
    r = client.post(
        f"/admin/league/{league_id}/draw/1",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 401


# ── GET /league/{id}/draws ────────────────────────────────────────────────────

def test_list_draws_empty(client):
    league_id = _create_league(client, "2003/04")
    r = client.get(f"/league/{league_id}/draws")
    assert r.status_code == 200
    assert r.json() == []


def test_list_draws_ok(client):
    league_id = _create_league(client, "2003/04")
    for matchday in (3, 1, 2):
        client.post(f"/admin/league/{league_id}/draw/{matchday}")

    r = client.get(f"/league/{league_id}/draws")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert [d["matchday_current"] for d in data] == [1, 2, 3]
    for item in data:
        assert "matchday_current" in item
        assert "matchday_historic" in item
        assert "cycle" in item
        assert "drawn_at" in item


def test_list_draws_league_not_found(client):
    r = client.get("/league/99999/draws")
    assert r.status_code == 404


def test_list_draws_no_auth_required(client):
    league_id = _create_league(client, "2003/04")
    client.post("/auth/logout")
    r = client.get(f"/league/{league_id}/draws")
    assert r.status_code == 200
