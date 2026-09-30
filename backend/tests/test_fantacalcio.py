import base64
import json
import time

import pytest

from backend.api import fantacalcio as fc
from backend.api.db import get_db


def _jwt(days: int = 300) -> str:
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'RS256'})}.{b64({'exp': int(time.time()) + days * 86400, 'role': 'user'})}.sig"


@pytest.fixture
def coach(client):
    """Utente allenatore registrato via invito, loggato con cookie user_session."""
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    lid = client.post("/admin/league", json={
        "name": "FcLega", "season_current": "2024/25", "season_historic": "2003/04", "budget": 500,
    }).json()["id"]
    mid = client.post(f"/admin/league/{lid}/managers", json={"name": "Fc", "team_name": "Fc FC"}).json()["id"]
    token = client.post(f"/admin/league/{lid}/managers/{mid}/invite").json()["token"]
    client.post("/auth/logout")
    email = f"fc{time.time_ns()}@example.com"
    r = client.post("/auth/register", json={"name": "Fc", "email": email, "password": "pw", "invite_token": token})
    assert r.status_code in (200, 201), r.text
    with get_db() as conn:
        user_id = conn.execute("SELECT id FROM user WHERE email = ?", (email,)).fetchone()["id"]
    yield user_id
    client.post("/auth/user/logout")
    client.post("/auth/logout")


@pytest.fixture
def fake_api(monkeypatch):
    calls = []

    def fake_get(path, token, params=None, headers=None):
        calls.append((path, token))
        if path == "/onboarding/v2/profile":
            return {"leghe": [{"id": 7, "alias": "mia-lega", "nome": "Mia Lega", "jwt": "eyJLEAGUE"}]}
        return {"path": path, "jwt": "eyJsecret", "nested": [{"token": "abc", "n": "Squadra"}]}

    monkeypatch.setattr(fc, "get", fake_get)
    return calls


def test_link_requires_user_session(client):
    assert client.get("/auth/user/fantacalcio").status_code == 401


def test_link_save_encrypted_and_status(client, coach, fake_api):
    jwt = _jwt(300)
    r = client.put("/auth/user/fantacalcio", json={"jwt": jwt})
    assert r.status_code == 200, r.text
    assert 298 <= r.json()["token"]["days_left"] <= 300

    with get_db() as conn:
        stored = conn.execute("SELECT fantacalcio_jwt FROM user WHERE id = ?", (coach,)).fetchone()[0]
        assert stored and jwt not in stored
        assert fc.load_user_jwt(conn, coach) == jwt

    st = client.get("/auth/user/fantacalcio").json()
    assert st["connected"] is True
    assert st["leagues"] == [{"id": 7, "alias": "mia-lega", "name": "Mia Lega"}]
    assert jwt not in json.dumps(st)
    assert fake_api[0] == ("/onboarding/v2/profile", jwt)


def test_link_rejects_invalid_and_expired(client, coach):
    assert client.put("/auth/user/fantacalcio", json={"jwt": "non-un-jwt"}).status_code == 422
    assert client.put("/auth/user/fantacalcio", json={"jwt": _jwt(-1)}).status_code == 422


def test_link_delete(client, coach):
    client.put("/auth/user/fantacalcio", json={"jwt": _jwt()})
    assert client.delete("/auth/user/fantacalcio").status_code == 200
    assert client.get("/auth/user/fantacalcio").json()["connected"] is False


def test_link_status_reports_api_error(client, coach, monkeypatch):
    def failing(*a, **k):
        raise fc.FantacalcioError(401, "ATH003", "token non valido", "u")
    monkeypatch.setattr(fc, "get", failing)
    client.put("/auth/user/fantacalcio", json={"jwt": _jwt()})
    st = client.get("/auth/user/fantacalcio").json()
    assert st["connected"] is True and "ATH003" in st["error"]


def test_explore_uses_league_token_and_redacts(client, coach, fake_api):
    client.put("/auth/user/fantacalcio", json={"jwt": _jwt()})
    with get_db() as conn:
        conn.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (coach,))
    r = client.get("/admin/fantacalcio/explore", params={"league": "mia-lega", "path": "/gaming/v1/x/1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["jwt"] == "***" and body["nested"][0]["token"] == "***" and body["nested"][0]["n"] == "Squadra"
    assert fake_api[-1] == ("/gaming/v1/x/1", "eyJLEAGUE")

    assert client.get("/admin/fantacalcio/explore", params={"league": "altra", "path": "/x"}).status_code == 404
    assert client.get("/admin/fantacalcio/explore", params={"league": "mia-lega", "path": "https://evil"}).status_code == 400


def test_explore_env_admin_without_user_gets_clear_error(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    r = client.get("/admin/fantacalcio/explore", params={"league": "x", "path": "/x"})
    client.post("/auth/logout")
    assert r.status_code == 400
    assert "Fantacalcio" in r.json()["detail"]


def test_explore_requires_admin(client, coach):
    r = client.get("/admin/fantacalcio/explore", params={"league": "x", "path": "/x"})
    assert r.status_code == 403
