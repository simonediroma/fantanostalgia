import pytest

from backend.api import fantacalcio as fc
from backend.api.db import get_db


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
                       "score_no_bonus": 7.0, "score_bonus": 10.0, "fc_id": 1}
    assert rows[1]["is_starter"] == 0 and rows[1]["score_bonus"] is None
    assert [r["player"] for r in rows] == ["Rossi A.", "Bianchi B.", "Verdi C."]
    assert any("999" in w for w in warnings)


def test_lineup_rows_unknown_team_skips_pairing():
    rows, warnings, pairings = fc.lineup_rows(
        [_match(10, 77, [{"pid": 1, "scr": 6, "cscr": 6}], [{"pid": 1, "scr": 6, "cscr": 6}])],
        {10: "Casa FC"}, {1: "Rossi A."})
    assert pairings == [] and len(rows) == 1 and any("77" in w for w in warnings)


def test_contains_token():
    assert fc.contains_token({"a": [{"token": "eyJhbGciOi.eyJleHAi.sig"}]})
    assert not fc.contains_token({"a": ["eyJ senza punti", 3, None], "n": "Casa FC"})


def test_pair_day_lineups_uses_calendar_matches():
    day = {"matches": [{"tIdH": 10, "tIdA": 20}, {"tIdH": 30, "tIdA": 40}]}
    teams = [{"tid": 20, "starts": []}, {"tid": 10, "starts": []}, {"tid": 30, "starts": []}]
    matches, warnings = fc.pair_day_lineups(day, teams)
    assert [(m["home"]["tid"], m["away"]["tid"]) for m in matches] == [(10, 20), (30, 40)]
    assert len(warnings) == 1 and "40" in warnings[0]


@pytest.fixture
def admin(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


@pytest.fixture
def ext_key(client, admin):
    return client.post("/admin/fantacalcio/keys", json={"label": "Chrome"}).json()["key"]


def test_keys_require_admin(client):
    assert client.get("/admin/fantacalcio/keys").status_code == 401
    assert client.post("/admin/fantacalcio/keys", json={}).status_code == 401


def test_key_lifecycle(client, admin):
    r = client.post("/admin/fantacalcio/keys", json={"label": "PC casa"})
    assert r.status_code == 201
    key, kid = r.json()["key"], r.json()["id"]
    with get_db() as conn:
        stored = conn.execute("SELECT key_hash FROM ext_api_key WHERE id = ?", (kid,)).fetchone()["key_hash"]
    assert stored != key  # solo l'hash
    listed = client.get("/admin/fantacalcio/keys").json()
    assert any(k["id"] == kid and k["label"] == "PC casa" and "key" not in k for k in listed)

    auth = {"Authorization": f"Bearer {key}"}
    assert client.get("/ext/v1/leagues", headers=auth).status_code == 200
    assert client.get("/admin/fantacalcio/keys").json()[0]["last_used_at"]
    client.delete(f"/admin/fantacalcio/keys/{kid}")
    assert client.get("/ext/v1/leagues", headers=auth).status_code == 401
    assert all(k["id"] != kid for k in client.get("/admin/fantacalcio/keys").json())


def test_ext_requires_key(client):
    assert client.get("/ext/v1/leagues").status_code == 401
    assert client.get("/ext/v1/leagues", headers={"Authorization": "Bearer fn_nope"}).status_code == 401


def test_extension_zip(client, admin):
    r = client.get("/admin/fantacalcio/extension.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    import io, zipfile
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "fantanostalgia-extension/manifest.json" in names


def test_cors_only_for_extension(client):
    origin = "chrome-extension://" + "a" * 32
    r = client.options("/ext/v1/leagues", headers={
        "Origin": origin, "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization"})
    assert r.headers.get("access-control-allow-origin") == origin
    r = client.options("/ext/v1/leagues", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


CALENDAR_DAY = {"matchDay": 1, "championshipMatchDay": 5, "calculated": True,
                "matches": [{"tIdH": 10, "tIdA": 20}]}
PLAYERS = [{"id": 1, "name": "Rossi A.", "fcrle": 4}, {"id": 3, "name": "Verdi C.", "fcrle": 4}]
COMP_TEAMS = [{"id": 10, "n": "Casa FC "}, {"id": 20, "n": "OSPITE FC"}]
LEAGUE_TEAMS = [
    {"id": 10, "n": "Casa FC", "cal": "1", "cs": "12", "r": {"p": 0, "d": 0, "c": 0, "a": 1}},
    {"id": 20, "n": "Ospite FC", "cal": "3", "cs": "8", "r": {"p": 0, "d": 0, "c": 0, "a": 1}}]


def _team(tid, starts, bench=()):
    return {"tid": tid, "starts": list(starts), "bench": list(bench)}


@pytest.fixture
def league(client, admin):
    """Lega FantaNostalgia con 2 manager e rose."""
    lid = client.post("/admin/league", json={
        "name": "ImportLega", "season_current": "2024/25", "season_historic": "2003/04", "budget": 500,
    }).json()["id"]
    ids = {}
    with get_db() as conn:
        for name in ("Casa", "Ospite"):
            ids[name] = conn.execute("INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
                                     (lid, name, f"{name} FC")).lastrowid
        for pname, mname in (("Rossi A.", "Casa"), ("Verdi C.", "Ospite")):
            conn.execute("INSERT INTO player_current (league_id, manager_id, name, role, team)"
                         " VALUES (?, ?, ?, 'A', 'X')", (lid, ids[mname], pname))
    return lid, ids


def _lineups_body(**over):
    body = {
        "day": CALENDAR_DAY,
        "lineups": [_team(20, [{"pid": 3, "scr": 5.5, "cscr": 5, "b": _b(i0=1)}]),
                    _team(10, [{"pid": 1, "scr": 7, "cscr": 10, "b": _b(i2=1)}])],
        "competition_teams": COMP_TEAMS, "players": PLAYERS,
        "league_teams": LEAGUE_TEAMS, "league_total": 2,
    }
    return {**body, **over}


def test_ext_lineups_saves_like_excel(client, league, ext_key):
    lid, ids = league
    r = client.post(f"/ext/v1/league/{lid}/lineups/1", json=_lineups_body(),
                    headers={"Authorization": f"Bearer {ext_key}"})
    assert r.status_code == 200, r.text
    assert r.json()["managers_imported"] == 2
    # La sync rose parte prima dell'import: rose già allineate, nessuna modifica
    assert r.json()["roster_sync"] == {"added": [], "moved": [], "released": [], "realign": []}
    with get_db() as conn:
        rows = conn.execute(
            "SELECT pc.name, l.is_starter, l.score_no_bonus, l.score_bonus FROM lineup l"
            " JOIN player_current pc ON pc.id = l.player_current_id"
            " WHERE l.league_id = ? AND l.matchday = 1 ORDER BY pc.name", (lid,)).fetchall()
        h2h = conn.execute("SELECT manager_home_id, manager_away_id FROM h2h_match"
                           " WHERE league_id = ? AND matchday = 1", (lid,)).fetchall()
    assert [tuple(r) for r in rows] == [("Rossi A.", 1, 7.0, 10.0), ("Verdi C.", 1, 5.5, 5.0)]
    assert [tuple(h) for h in h2h] == [(ids["Casa"], ids["Ospite"])]


def test_ext_lineups_rejects_uncalculated_day_and_tokens(client, league, ext_key):
    lid, _ = league
    auth = {"Authorization": f"Bearer {ext_key}"}
    r = client.post(f"/ext/v1/league/{lid}/lineups/2", headers=auth,
                    json=_lineups_body(day={**CALENDAR_DAY, "calculated": False}))
    assert r.status_code == 400
    r = client.post(f"/ext/v1/league/{lid}/lineups/1", headers=auth,
                    json=_lineups_body(players=PLAYERS + [{"id": 9, "jwt": "eyJa.eyJb.c"}]))
    assert r.status_code == 400 and "token" in r.json()["detail"]
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM lineup WHERE league_id = ?", (lid,)).fetchone()[0] == 0


def test_ext_lineups_unknown_player_never_writes_rosters(client, league, ext_key):
    """Giocatore sconosciuto: creato in anagrafica senza squadra, formazione salvata,
    avviso per rilanciare la sync rose. Sync fallita: l'import va avanti."""
    lid, ids = league
    players = PLAYERS + [{"id": 4, "name": "Nuovo P.", "fcrle": 1}]
    body = _lineups_body(
        players=players,
        lineups=[_team(10, [{"pid": 4, "scr": 6.5, "cscr": 5.5, "b": _b()}]), _team(20, [])],
        league_teams=[LEAGUE_TEAMS[0]], league_total=2)  # squadre lette ≠ item → sync fallita
    r = client.post(f"/ext/v1/league/{lid}/lineups/1", json=body,
                    headers={"Authorization": f"Bearer {ext_key}"})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["roster_sync"]["error"]
    assert any("Nuovo P." in w and "rilancia la sync rose" in w for w in res["warnings"])
    with get_db() as conn:
        p = conn.execute("SELECT role, manager_id, fc_id FROM player_current"
                         " WHERE league_id = ? AND name = 'Nuovo P.'", (lid,)).fetchone()
    assert tuple(p) == ("P", None, 4)


def test_ext_rosters(client, league, ext_key):
    lid, _ = league
    auth = {"Authorization": f"Bearer {ext_key}"}
    url = f"/ext/v1/league/{lid}/rosters"
    teams = [{**LEAGUE_TEAMS[0], "cal": "1;3", "cs": "12;8", "r": {"p": 0, "d": 0, "c": 0, "a": 2}},
             {**LEAGUE_TEAMS[1], "cal": "", "cs": "", "r": {"p": 0, "d": 0, "c": 0, "a": 0}}]
    r = client.post(url, headers=auth, json={"teams": teams, "total": 2, "players": PLAYERS})
    assert r.status_code == 409 and "Rosa vuota" in r.json()["detail"]
    r = client.post(url, headers=auth, json={"teams": teams[:1], "total": 1, "players": PLAYERS})
    assert r.status_code == 200, r.text
    assert r.json()["moved"] == ["Verdi C.: Ospite FC → Casa FC"]
    assert client.post("/ext/v1/league/99999/rosters", headers=auth,
                       json={"teams": [], "players": []}).status_code == 404
