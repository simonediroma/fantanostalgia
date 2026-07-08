from backend.api.db import get_db


def _add_historic(conn, name: str, role: str, team: str, season: str) -> int:
    cur = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source)"
        " VALUES (?, ?, ?, ?, 'archive')",
        (name, role, team, season),
    )
    return cur.lastrowid


def _add_rating(conn, hist_id: int, matchday: int, rating: float) -> None:
    conn.execute(
        "INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
        " VALUES (?, ?, ?, 'archive')",
        (hist_id, matchday, rating),
    )


def test_home_shows_hall_of_fame_for_player_with_enough_matchdays(client):
    with get_db() as conn:
        hist_id = _add_historic(conn, "HOFStarQualifies", "A", "Legend FC", "1999/00")
        for md in range(1, 6):
            _add_rating(conn, hist_id, md, 9.5)

    r = client.get("/")
    assert r.status_code == 200
    assert "Hall of Fame" in r.text
    assert "HOFStarQualifies" in r.text


def test_home_hides_players_below_matchday_threshold(client):
    with get_db() as conn:
        hist_id = _add_historic(conn, "HOFStarTooFewMatchdays", "A", "Legend FC", "1999/00")
        for md in range(100, 104):  # only 4 matchdays, below the n >= 5 threshold
            _add_rating(conn, hist_id, md, 10.0)

    r = client.get("/")
    assert r.status_code == 200
    assert "HOFStarTooFewMatchdays" not in r.text
