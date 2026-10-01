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


# ── Conversione e import formazioni ─────────────────────────────────────────

def _b(**events) -> str:
    counts = [0] * 16
    for idx, n in events.items():
        counts[int(idx[1:])] = n
    return ";".join(map(str, counts))


def test_scores_conversion():
    assert fc._scores({"scr": 56, "cscr": 100, "b": _b()}) == (None, None)
    assert fc._scores({"scr": 55, "cscr": 100, "b": _b()}) == (None, None)
    # voto senza bonus = voto in pagella (scr), senza malus: doppietta + ammonizione
    assert fc._scores({"scr": 7, "cscr": 12.5, "b": _b(i2=2, i0=1)}) == (7.0, 12.5)
    # portiere con 2 gol subiti: resta il voto in pagella
    assert fc._scores({"scr": 6, "cscr": 4, "b": _b(i3=2)}) == (6.0, 4.0)


def _match(home_tid, away_tid, home_players, away_players):
    def side(tid, players):
        return {"tid": tid, "starts": players[:1], "bench": players[1:]}
    return {"home": side(home_tid, home_players), "away": side(away_tid, away_players)}


def test_lineup_rows_maps_teams_players_and_pairings():
    lineups = [_match(
        10, 20,
        [{"pid": 1, "scr": 7, "cscr": 10, "b": _b(i2=1)}, {"pid": 2, "scr": 56, "cscr": 100, "b": _b()}],
        [{"pid": 3, "scr": 6, "cscr": 6, "b": _b()}, {"pid": 999, "scr": 6, "cscr": 6, "b": _b()}],
    )]
    rows, warnings, pairings = fc.lineup_rows(lineups, {10: "Casa FC", 20: "Ospite FC"},
                                              {1: "Rossi A.", 2: "Bianchi B.", 3: "Verdi C."})
    assert pairings == [("Casa FC", "Ospite FC")]
    assert rows[0] == {"manager": "Casa FC", "player": "Rossi A.", "is_starter": 1,
                       "score_no_bonus": 7.0, "score_bonus": 10.0}
    assert rows[1]["is_starter"] == 0 and rows[1]["score_bonus"] is None
    assert [r["player"] for r in rows] == ["Rossi A.", "Bianchi B.", "Verdi C."]
    assert any("999" in w for w in warnings)


def test_lineup_rows_unknown_team_skips_pairing():
    rows, warnings, pairings = fc.lineup_rows(
        [_match(10, 77, [{"pid": 1, "scr": 6, "cscr": 6}], [{"pid": 1, "scr": 6, "cscr": 6}])],
        {10: "Casa FC"}, {1: "Rossi A."})
    assert pairings == [] and len(rows) == 1 and any("77" in w for w in warnings)


@pytest.fixture
def import_setup(client, coach, monkeypatch):
    """Lega FantaNostalgia con 2 manager e rose, admin = coach con token collegato."""
    with get_db() as conn:
        conn.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (coach,))
    client.put("/auth/user/fantacalcio", json={"jwt": _jwt()})
    lid = client.post("/admin/league", json={
        "name": "ImportLega", "season_current": "2024/25", "season_historic": "2003/04", "budget": 500,
    }).json()["id"]
    with get_db() as conn:
        ids = {}
        for name in ("Casa", "Ospite"):
            mid = conn.execute("INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
                               (lid, name, f"{name} FC")).lastrowid
            ids[name] = mid
        for pname, mname in (("Rossi A.", "Casa"), ("Verdi C.", "Ospite")):
            conn.execute("INSERT INTO player_current (league_id, manager_id, name, role, team)"
                         " VALUES (?, ?, ?, 'A', 'X')", (lid, ids[mname], pname))

    calls = []

    def fake_get(path, token, params=None, headers=None):
        calls.append(path)
        if path == "/onboarding/v2/profile":
            return {"leghe": [{"id": 7, "alias": "mia-lega", "nome": "Mia Lega", "jwt": "eyJLEAGUE"}]}
        if path == "/onboarding/v1/league/competition/calendar/5":
            return [
                {"matchDay": 1, "championshipMatchDay": 5, "calculated": True,
                 "matches": [{"tIdH": 10, "tIdA": 20}]},
                {"matchDay": 2, "championshipMatchDay": 6, "calculated": False, "matches": []},
            ]
        if path == "/onboarding/v1/league/competition/teams":
            return {"nextPage": False, "data": [{"id": 10, "n": "Casa FC "}, {"id": 20, "n": "OSPITE FC"}]}
        if path == "/onboarding/v1/league/players":
            return {"players": [{"id": 1, "name": "Rossi A."}, {"id": 3, "name": "Verdi C."}]}
        if path == "/gaming/v1/teamLineup/5/1/5/10/20":
            return _match(10, 20, [{"pid": 1, "scr": 7, "cscr": 10, "b": _b(i2=1)}],
                          [{"pid": 3, "scr": 5.5, "cscr": 5, "b": _b(i0=1)}])
        raise AssertionError(path)

    monkeypatch.setattr(fc, "get", fake_get)
    return lid, ids, calls


def test_import_lineups_saves_like_excel(client, import_setup):
    lid, ids, calls = import_setup
    r = client.post(f"/admin/league/{lid}/lineups/1/fantacalcio",
                    json={"fc_league": "mia-lega", "competition_id": 5, "fc_match_day": 1})
    assert r.status_code == 200, r.text
    assert r.json()["managers_imported"] == 2
    with get_db() as conn:
        rows = conn.execute(
            "SELECT pc.name, l.is_starter, l.score_no_bonus, l.score_bonus FROM lineup l"
            " JOIN player_current pc ON pc.id = l.player_current_id"
            " WHERE l.league_id = ? AND l.matchday = 1 ORDER BY pc.name", (lid,)).fetchall()
        h2h = conn.execute("SELECT manager_home_id, manager_away_id FROM h2h_match"
                           " WHERE league_id = ? AND matchday = 1", (lid,)).fetchall()
    assert [tuple(r) for r in rows] == [("Rossi A.", 1, 7.0, 10.0), ("Verdi C.", 1, 5.5, 5.0)]
    assert [tuple(h) for h in h2h] == [(ids["Casa"], ids["Ospite"])]
    assert "/gaming/v1/teamLineup/5/1/5/10/20" in calls


def test_import_lineups_rejects_uncalculated_or_missing_day(client, import_setup):
    lid, _, _ = import_setup
    body = {"fc_league": "mia-lega", "competition_id": 5}
    assert client.post(f"/admin/league/{lid}/lineups/2/fantacalcio", json={**body, "fc_match_day": 2}).status_code == 400
    assert client.post(f"/admin/league/{lid}/lineups/9/fantacalcio", json={**body, "fc_match_day": 9}).status_code == 404


def test_calendar_endpoint(client, import_setup):
    r = client.get("/admin/fantacalcio/mia-lega/calendar/5")
    assert r.json() == [
        {"match_day": 1, "championship_match_day": 5, "calculated": True},
        {"match_day": 2, "championship_match_day": 6, "calculated": False},
    ]


def test_elevated_user_can_use_matchday_admin_endpoints(client, coach):
    """L'import richiede l'accesso da utente: anche gli endpoint giornate
    (get_current_admin_or_bearer) devono accettare un utente admin."""
    with get_db() as conn:
        lid = conn.execute("SELECT id FROM league ORDER BY id DESC LIMIT 1").fetchone()["id"]
    assert client.get(f"/admin/league/{lid}/matchdays").status_code == 403
    with get_db() as conn:
        conn.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (coach,))
    assert client.get(f"/admin/league/{lid}/matchdays").status_code == 200
