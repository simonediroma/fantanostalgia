import pytest


@pytest.fixture(autouse=True)
def cleanup(client):
    yield
    client.post("/auth/logout")
    client.post("/auth/user/logout")


def _register_coach(client, email, name="Coach Test"):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    league = client.post("/admin/league", json={
        "name": "Lega Elevation", "season_current": "2024/25",
        "season_historic": "2003/04", "budget": 500,
    }).json()
    manager = client.post(
        f"/admin/league/{league['id']}/managers",
        json={"name": "Mario", "team_name": "Rossi"},
    ).json()
    invite = client.post(
        f"/admin/league/{league['id']}/managers/{manager['id']}/invite"
    ).json()
    client.post("/auth/logout")

    r = client.post("/auth/register", json={
        "name": name, "email": email, "password": "pass1234",
        "invite_token": invite["token"],
    })
    assert r.status_code == 201


def test_elevation_request_requires_coach_auth(client):
    r = client.post("/auth/user/elevation-request")
    assert r.status_code == 401


def test_elevation_request_then_approve_grants_admin_access(client):
    _register_coach(client, "approve@test.com")

    r = client.post("/auth/user/elevation-request")
    assert r.status_code == 201
    req_id = r.json()["id"]
    assert r.json()["status"] == "pending"
    client.post("/auth/user/logout")

    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    listed = client.get("/auth/admin/elevation-requests")
    assert listed.status_code == 200
    assert any(x["id"] == req_id and x["status"] == "pending" for x in listed.json())

    approved = client.post(f"/auth/admin/elevation-requests/{req_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    client.post("/auth/logout")

    login = client.post("/auth/user/login", json={"email": "approve@test.com", "password": "pass1234"})
    assert login.status_code == 200

    me = client.get("/auth/user/me")
    assert me.json()["is_admin"] is True

    admin_check = client.get("/auth/admin/elevation-requests")
    assert admin_check.status_code == 200


def test_elevation_request_then_reject_keeps_permissions_unchanged(client):
    _register_coach(client, "reject@test.com")

    r = client.post("/auth/user/elevation-request")
    req_id = r.json()["id"]
    client.post("/auth/user/logout")

    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    rejected = client.post(f"/auth/admin/elevation-requests/{req_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    client.post("/auth/logout")

    client.post("/auth/user/login", json={"email": "reject@test.com", "password": "pass1234"})
    me = client.get("/auth/user/me")
    assert me.json()["is_admin"] is False

    admin_check = client.get("/auth/admin/elevation-requests")
    assert admin_check.status_code == 403


def test_elevation_request_duplicate_pending_rejected(client):
    _register_coach(client, "dup@test.com")

    r1 = client.post("/auth/user/elevation-request")
    assert r1.status_code == 201
    r2 = client.post("/auth/user/elevation-request")
    assert r2.status_code == 400


def test_cannot_resolve_elevation_request_twice(client):
    _register_coach(client, "twice@test.com")
    r = client.post("/auth/user/elevation-request")
    req_id = r.json()["id"]
    client.post("/auth/user/logout")

    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    first = client.post(f"/auth/admin/elevation-requests/{req_id}/approve")
    assert first.status_code == 200
    second = client.post(f"/auth/admin/elevation-requests/{req_id}/approve")
    assert second.status_code == 400
