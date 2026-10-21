import requests

from backend.api import notifications, wikimedia
from backend.api.db import get_db


def _login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})


def _add_historic(conn, name: str, season: str, role: str = "A") -> int:
    return conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, ?, 'Old FC', ?, 'archive')",
        (name, role, season),
    ).lastrowid


def _entity(qid, footballer=True, image="Foto.jpg", born="+1967-02-18T00:00:00Z"):
    claims = {}
    if footballer:
        claims["P106"] = [{"mainsnak": {"datavalue": {"value": {"id": wikimedia.FOOTBALLER}}}}]
    if image:
        claims["P18"] = [{"mainsnak": {"datavalue": {"value": image}}}]
    if born:
        claims["P569"] = [{"mainsnak": {"datavalue": {"value": {"time": born}}}}]
    return {"id": qid, "claims": claims}


# ── Pure functions ───────────────────────────────────────────────────────────

def test_search_query_strips_initials_and_uppercase():
    assert wikimedia.search_query("BAGGIO R.") == "Baggio"
    assert wikimedia.search_query("Del Piero A.") == "Del Piero"
    assert wikimedia.search_query("Roberto Baggio") == "Roberto Baggio"


def test_pick_candidate_skips_non_footballers_missing_photo_and_wrong_age():
    entities = [
        _entity("Q1", footballer=False),
        _entity("Q2", image=None),
        _entity("Q3", born="+1990-01-01T00:00:00Z"),  # 3 anni nel 1993
        _entity("Q4", image="Baggio.jpg"),
    ]
    assert wikimedia.pick_candidate(entities, "1993/94") == ("Q4", "Baggio.jpg")
    assert wikimedia.pick_candidate(entities[:3], "1993/94") is None


def test_parse_imageinfo_builds_credit_without_html():
    data = {"query": {"pages": {"1": {"imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:X.jpg",
        "extmetadata": {
            "Artist": {"value": '<a href="u">Mario Rossi</a>'},
            "LicenseShortName": {"value": "CC BY-SA 3.0"},
        },
    }]}}}}
    assert wikimedia.parse_imageinfo(data) == {
        "photo_url": "https://upload.wikimedia.org/thumb.jpg",
        "photo_credit": "Mario Rossi, CC BY-SA 3.0",
        "photo_source_url": "https://commons.wikimedia.org/wiki/File:X.jpg",
    }


# ── Batch endpoint ───────────────────────────────────────────────────────────

def test_fetch_photos_only_league_seasons_and_marks_checked(client, monkeypatch):
    _login(client)
    client.post("/admin/league", json={"name": "FotoLega", "season_current": "2024/25", "season_historic": "1961/62"})
    with get_db() as conn:
        with_photo = _add_historic(conn, "FotoSi", "1961/62")
        without = _add_historic(conn, "FotoNo", "1961/62")
        other_season = _add_historic(conn, "AltraStagione", "1955/56")

    def fake_find(name, season):
        if name == "FotoSi":
            return {"wikidata_id": "Q9", "photo_url": "https://img/x.jpg",
                    "photo_credit": "Autore, CC BY-SA", "photo_source_url": "https://src"}
        return None
    monkeypatch.setattr(wikimedia, "find_photo", fake_find)

    r = client.post("/admin/historic/photos/fetch?limit=500")
    assert r.status_code == 200, r.text
    assert r.json()["remaining"] == 0
    assert r.json()["error"] is None

    with get_db() as conn:
        rows = {row["id"]: row for row in conn.execute(
            "SELECT id, photo_url, wikidata_id, photo_checked_at FROM player_historic WHERE id IN (?, ?, ?)",
            (with_photo, without, other_season),
        )}
    assert rows[with_photo]["photo_url"] == "https://img/x.jpg"
    assert rows[with_photo]["wikidata_id"] == "Q9"
    assert rows[without]["photo_url"] is None and rows[without]["photo_checked_at"] is not None
    assert rows[other_season]["photo_checked_at"] is None


def test_fetch_photos_network_error_leaves_player_unchecked(client, monkeypatch):
    _login(client)
    client.post("/admin/league", json={"name": "FotoLega2", "season_current": "2024/25", "season_historic": "1962/63"})
    with get_db() as conn:
        pid = _add_historic(conn, "Irraggiungibile", "1962/63")

    def boom(name, season):
        raise requests.ConnectionError("blocked")
    monkeypatch.setattr(wikimedia, "find_photo", boom)

    r = client.post("/admin/historic/photos/fetch")
    assert r.status_code == 200
    assert "blocked" in r.json()["error"]
    with get_db() as conn:
        row = conn.execute("SELECT photo_checked_at FROM player_historic WHERE id = ?", (pid,)).fetchone()
    assert row["photo_checked_at"] is None


def test_set_photo_override_and_404(client):
    _login(client)
    with get_db() as conn:
        pid = _add_historic(conn, "Manuale", "1970/71")
    r = client.put(f"/admin/historic/players/{pid}/photo",
                   json={"photo_url": "https://img/m.jpg", "photo_credit": "Io, CC0"})
    assert r.status_code == 200
    with get_db() as conn:
        row = conn.execute("SELECT photo_url, photo_credit FROM player_historic WHERE id = ?", (pid,)).fetchone()
    assert (row["photo_url"], row["photo_credit"]) == ("https://img/m.jpg", "Io, CC0")

    assert client.put("/admin/historic/players/999999/photo", json={"photo_url": ""}).status_code == 404


# ── Scheda pubblica ──────────────────────────────────────────────────────────

def test_storico_page_shows_stats_photo_and_credit(client):
    with get_db() as conn:
        pid = _add_historic(conn, "SchedaStar", "1988/89")
        for md, rating, goals in [(1, 7.0, 2), (2, 6.0, 0)]:
            conn.execute(
                "INSERT INTO historic_rating (player_historic_id, matchday, rating, goals, minutes, source)"
                " VALUES (?, ?, ?, ?, 90, 'archive')",
                (pid, md, rating, goals),
            )
        conn.execute(
            "UPDATE player_historic SET photo_url = 'https://img/s.jpg', photo_credit = 'Autore, CC BY-SA'"
            " WHERE id = ?", (pid,),
        )

    r = client.get(f"/storico/{pid}")
    assert r.status_code == 200
    assert "SchedaStar" in r.text
    assert "6.50" in r.text          # media voto
    assert "https://img/s.jpg" in r.text
    assert "Autore, CC BY-SA" in r.text
    assert ">180<" in r.text         # minuti

    assert client.get("/storico/999999").status_code == 404


# ── Email ────────────────────────────────────────────────────────────────────

def test_won_email_contains_player_card_with_photo():
    with get_db() as conn:
        pid = _add_historic(conn, "EmailCard", "1990/91")
        conn.execute(
            "INSERT INTO historic_rating (player_historic_id, matchday, rating, source) VALUES (?, 1, 7.5, 'archive')",
            (pid,),
        )
        conn.execute("UPDATE player_historic SET photo_url = 'https://img/e.jpg' WHERE id = ?", (pid,))
        cards = notifications.player_cards(conn, [pid])

    _, html = notifications.render_email("gran_premio_won", {
        "name": "M", "league_name": "L", "league_id": 1, "prize_player_name": "EmailCard", "players": cards,
    }, "https://fn.it")
    assert 'src="https://img/e.jpg"' in html
    assert "7.50" in html
    assert f"https://fn.it/storico/{pid}" in html

    # Righe accodate prima della modifica (senza "players") restano renderizzabili.
    _, old_html = notifications.render_email("gran_premio_won", {
        "name": "M", "league_name": "L", "league_id": 1, "prize_player_name": "X",
    }, "https://fn.it")
    assert "/storico/" not in old_html
