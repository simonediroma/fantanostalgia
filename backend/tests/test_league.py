import pytest


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


def test_list_leagues_empty(client):
    r = client.get("/league")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_league(client):
    r = client.post("/admin/league", json={
        "name": "Test Lega",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Lega"
    assert data["season_current"] == "2024/25"


def test_create_league_invalid_season_format(client):
    r = client.post("/admin/league", json={
        "name": "Bad",
        "season_current": "2024-25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    assert r.status_code == 422


def test_create_league_same_seasons(client):
    r = client.post("/admin/league", json={
        "name": "Bad",
        "season_current": "2024/25",
        "season_historic": "2024/25",
        "budget": 500,
    })
    assert r.status_code == 422


def test_create_league_budget_too_low(client):
    r = client.post("/admin/league", json={
        "name": "Bad",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 50,
    })
    assert r.status_code == 422


def test_get_league(client):
    create = client.post("/admin/league", json={
        "name": "Lega Get",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 100,
    })
    league_id = create.json()["id"]
    r = client.get(f"/league/{league_id}")
    assert r.status_code == 200
    assert r.json()["id"] == league_id


def test_get_league_not_found(client):
    r = client.get("/league/99999")
    assert r.status_code == 404


def test_update_league(client):
    create = client.post("/admin/league", json={
        "name": "Lega Update",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = create.json()["id"]
    r = client.put(f"/admin/league/{league_id}", json={"name": "Nuovo Nome"})
    assert r.status_code == 200
    assert r.json()["name"] == "Nuovo Nome"


def test_create_league_with_max_manager_and_platform(client):
    r = client.post("/admin/league", json={
        "name": "Lega Completa",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
        "max_manager": 8,
        "platform": "Fantacalcio.it",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["max_manager"] == 8
    assert data["platform"] == "Fantacalcio.it"


def test_create_league_max_manager_too_low(client):
    r = client.post("/admin/league", json={
        "name": "Bad",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
        "max_manager": 0,
    })
    assert r.status_code == 422


def test_create_league_without_max_manager_or_platform(client):
    r = client.post("/admin/league", json={
        "name": "Lega Minima",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["max_manager"] is None
    assert data["platform"] is None


def test_delete_league(client):
    create = client.post("/admin/league", json={
        "name": "Lega Delete",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = create.json()["id"]
    r = client.delete(f"/admin/league/{league_id}")
    assert r.status_code == 204
    r2 = client.get(f"/league/{league_id}")
    assert r2.status_code == 404


def test_admin_endpoints_require_auth(client):
    client.post("/auth/logout")
    r = client.post("/admin/league", json={
        "name": "X", "season_current": "2024/25", "season_historic": "2003/04", "budget": 500,
    })
    assert r.status_code == 401


# ── Manager endpoints ────────────────────────────────────────────────────────

def _make_league(client):
    r = client.post("/admin/league", json={
        "name": "Lega Manager Test",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    return r.json()["id"]


def test_list_managers_empty(client):
    lid = _make_league(client)
    r = client.get(f"/league/{lid}/managers")
    assert r.status_code == 200
    assert r.json() == []


def test_create_manager(client):
    lid = _make_league(client)
    r = client.post(f"/admin/league/{lid}/managers", json={"name": "Mario", "team_name": "Rossoneri"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Mario"
    assert data["team_name"] == "Rossoneri"
    assert data["league_id"] == lid


def test_list_managers_after_create(client):
    lid = _make_league(client)
    client.post(f"/admin/league/{lid}/managers", json={"name": "Alice", "team_name": "Bianchi"})
    client.post(f"/admin/league/{lid}/managers", json={"name": "Bob", "team_name": "Neri"})
    r = client.get(f"/league/{lid}/managers")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()]
    assert "Alice" in names
    assert "Bob" in names


def test_create_manager_league_not_found(client):
    r = client.post("/admin/league/99999/managers", json={"name": "X", "team_name": "Y"})
    assert r.status_code == 404


def test_list_managers_league_not_found(client):
    r = client.get("/league/99999/managers")
    assert r.status_code == 404


def test_create_manager_requires_auth(client):
    lid = _make_league(client)
    client.post("/auth/logout")
    r = client.post(f"/admin/league/{lid}/managers", json={"name": "X", "team_name": "Y"})
    assert r.status_code == 401


def test_managers_isolated_between_leagues(client):
    lid1 = _make_league(client)
    lid2 = _make_league(client)
    client.post(f"/admin/league/{lid1}/managers", json={"name": "Mario", "team_name": "Rossoneri"})
    client.post(f"/admin/league/{lid2}/managers", json={"name": "Luigi", "team_name": "Verdoni"})
    r1 = client.get(f"/league/{lid1}/managers")
    r2 = client.get(f"/league/{lid2}/managers")
    assert [m["name"] for m in r1.json()] == ["Mario"]
    assert [m["name"] for m in r2.json()] == ["Luigi"]


def test_create_manager_blocked_at_max_manager(client):
    create = client.post("/admin/league", json={
        "name": "Lega Piccola",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
        "max_manager": 1,
    })
    lid = create.json()["id"]
    r1 = client.post(f"/admin/league/{lid}/managers", json={"name": "Primo", "team_name": "Uno"})
    assert r1.status_code == 201
    r2 = client.post(f"/admin/league/{lid}/managers", json={"name": "Secondo", "team_name": "Due"})
    assert r2.status_code == 422
