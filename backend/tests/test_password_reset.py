import json

import pytest

from backend.api import notifications
from backend.api.db import get_db


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")
    client.post("/auth/user/logout")


def _create_league(client, name="ResetLega") -> int:
    r = client.post("/admin/league", json={
        "name": name, "season_current": "2024/25", "season_historic": "2003/04", "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _create_registered_manager(client, league_id: int, email: str, name="Mario", password="oldpass123") -> int:
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": name, "team_name": f"{name} FC"}
    ).json()
    invite = client.post(f"/admin/league/{league_id}/managers/{manager['id']}/invite").json()
    client.post("/auth/logout")
    r = client.post("/auth/register", json={
        "name": name, "email": email, "password": password, "invite_token": invite["token"],
    })
    assert r.status_code == 201, r.text
    client.post("/auth/user/logout")
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    return manager["id"]


def _queue_rows_for(conn, to_email: str):
    return conn.execute(
        "SELECT * FROM email_queue WHERE to_email = ? ORDER BY id", (to_email,)
    ).fetchall()


def test_admin_reset_changes_password(client):
    league_id = _create_league(client)
    manager_id = _create_registered_manager(client, league_id, "reset1@test.com", password="oldpass123")

    r = client.post(f"/admin/league/{league_id}/managers/{manager_id}/reset-password", json={
        "new_password": "newpass456",
    })
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "reset1@test.com"

    old_login = client.post("/auth/user/login", json={"email": "reset1@test.com", "password": "oldpass123"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/user/login", json={"email": "reset1@test.com", "password": "newpass456"})
    assert new_login.status_code == 200
    client.post("/auth/user/logout")


def test_admin_reset_enqueues_email_with_new_password(client):
    league_id = _create_league(client)
    manager_id = _create_registered_manager(client, league_id, "reset2@test.com", name="Luigi")

    r = client.post(f"/admin/league/{league_id}/managers/{manager_id}/reset-password", json={
        "new_password": "newpass789",
    })
    assert r.status_code == 200, r.text

    with get_db() as conn:
        rows = _queue_rows_for(conn, "reset2@test.com")
    reset_rows = [row for row in rows if row["template"] == "password_reset"]
    assert len(reset_rows) == 1
    params = json.loads(reset_rows[0]["params"])
    assert params == {"name": "Luigi", "new_password": "newpass789"}
    assert reset_rows[0]["status"] == "pending"


def test_process_email_queue_redacts_password_after_send(client, monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, html: calls.append((to, subject, html)))

    league_id = _create_league(client)
    manager_id = _create_registered_manager(client, league_id, "reset3@test.com", name="Anna")
    client.post(f"/admin/league/{league_id}/managers/{manager_id}/reset-password", json={
        "new_password": "supersecret",
    })

    r = client.post("/admin/process-email-queue")
    assert r.status_code == 200, r.text

    assert any(to == "reset3@test.com" and "supersecret" in html for to, _subject, html in calls)

    with get_db() as conn:
        rows = _queue_rows_for(conn, "reset3@test.com")
    reset_rows = [row for row in rows if row["template"] == "password_reset"]
    assert len(reset_rows) == 1
    assert reset_rows[0]["status"] == "sent"
    assert reset_rows[0]["sent_at"] is not None
    assert json.loads(reset_rows[0]["params"]) == {"redacted": True}


def test_reset_password_manager_without_account(client):
    league_id = _create_league(client)
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "NoAccount", "team_name": "NA FC"}
    ).json()

    r = client.post(f"/admin/league/{league_id}/managers/{manager['id']}/reset-password", json={
        "new_password": "whatever123",
    })
    assert r.status_code == 400


def test_reset_password_manager_not_found(client):
    league_id = _create_league(client)
    r = client.post(f"/admin/league/{league_id}/managers/99999/reset-password", json={
        "new_password": "whatever123",
    })
    assert r.status_code == 404


def test_reset_password_requires_admin_auth(client):
    league_id = _create_league(client)
    manager_id = _create_registered_manager(client, league_id, "reset4@test.com")
    client.post("/auth/logout")

    r = client.post(f"/admin/league/{league_id}/managers/{manager_id}/reset-password", json={
        "new_password": "whatever123",
    })
    assert r.status_code == 401
