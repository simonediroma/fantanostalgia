from backend.api.db import get_db
from backend.engine.mapping import MIN_APPEARANCES, assign_nostalgia_pools


def _historic(conn, name, season, n_rated, n_unrated=0):
    pid = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source)"
        " VALUES (?, 'A', 'Juventus', ?, 'archive')", (name, season),
    ).lastrowid
    for md in range(1, n_rated + 1):
        conn.execute(
            "INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
            " VALUES (?, ?, 6.0, 'archive')", (pid, md))
    for md in range(n_rated + 1, n_rated + n_unrated + 1):
        conn.execute(
            "INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
            " VALUES (?, ?, NULL, 'archive')", (pid, md))
    return pid


def test_pool_only_includes_players_with_min_appearances(client):
    season = "1999/00"
    with get_db() as conn:
        lid = conn.execute(
            "INSERT INTO league (name, season_current, season_historic, budget)"
            " VALUES ('PoolMin', '2024/25', ?, 500)", (season,)).lastrowid
        conn.execute("INSERT INTO manager (league_id, name, team_name) VALUES (?, 'M1', 'T1')", (lid,))
        ok = {_historic(conn, f"Reg{i}", season, MIN_APPEARANCES + i) for i in range(3)}
        _historic(conn, "Pochi", season, MIN_APPEARANCES - 1)
        _historic(conn, "SoloSV", season, MIN_APPEARANCES - 1, n_unrated=5)

        assign_nostalgia_pools(conn, lid)
        ids = {r[0] for r in conn.execute(
            "SELECT player_historic_id FROM manager_nostalgia_pool WHERE league_id = ?", (lid,))}
    assert ids == ok
