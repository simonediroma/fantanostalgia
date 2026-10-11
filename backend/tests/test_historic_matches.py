from backend.api.db import get_db
from backend.engine.historic_matches import reconstruct_matches


def _p(name, team, goals=0, conceded=0, won=0, role="C", **kw):
    row = {"name": name, "role": role, "team": team, "rating": 6.0, "goals": goals,
           "own_goals": 0, "penalties_scored": 0, "yellow_cards": 0, "red_cards": 0,
           "goals_conceded": conceded, "team_won": won, "minutes": 90}
    row.update(kw)
    return row


def test_pairs_teams_with_consistent_scores():
    rows = [
        _p("Del Piero", "Juventus", goals=2, conceded=1, won=1, penalties_scored=1),
        _p("Buffon", "Juventus", conceded=1, won=1, role="P", yellow_cards=1),
        _p("Shevchenko", "Milan", goals=1, conceded=2),
        _p("Totti", "Roma", goals=0, conceded=3),
        _p("Crespo", "Lazio", goals=3, conceded=0, won=1),
    ]
    res = reconstruct_matches(rows)
    assert res["unpaired"] == []
    by_team = {(m["home"]["team"], m["away"]["team"]): m for m in res["matches"]}
    juve = by_team[("Juventus", "Milan")]
    assert (juve["home_goals"], juve["away_goals"]) == (2, 1)
    assert juve["home"]["scorers"] == [{"name": "Del Piero", "goals": 2, "penalties": 1, "own": False}]
    assert juve["home"]["cards"] == [{"name": "Buffon", "card": "yellow"}]
    assert juve["home"]["players"][0]["name"] == "Buffon"  # portiere per primo
    lazio = by_team[("Lazio", "Roma")]
    assert (lazio["home_goals"], lazio["away_goals"]) == (3, 0)


def test_ambiguous_draws_stay_unpaired():
    rows = [_p(f"X{t}", t) for t in ("Bari", "Lecce", "Parma", "Reggina")]
    res = reconstruct_matches(rows)
    assert res["matches"] == []
    assert [t["team"] for t in res["unpaired"]] == ["Bari", "Lecce", "Parma", "Reggina"]


def test_own_goal_counts_for_opponent():
    rows = [
        _p("Vieri", "Inter", goals=1, conceded=0, won=1),
        _p("Zeta", "Inter", conceded=0, won=1),
        _p("Rossi", "Bologna", conceded=2, own_goals=1),
    ]
    res = reconstruct_matches(rows)
    assert len(res["matches"]) == 1
    m = res["matches"][0]
    assert (m["home"]["team"], m["home_goals"], m["away_goals"]) == ("Bologna", 0, 2)
    assert m["home"]["scorers"] == [{"name": "Rossi", "goals": 1, "penalties": 0, "own": True}]


def test_giornata_page_shows_historic_matches(client):
    with get_db() as conn:
        league_id = conn.execute(
            "INSERT INTO league (name, season_current, season_historic) VALUES ('HistMatchLega', '2024/25', '1997/98')"
        ).lastrowid
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic) VALUES (?, 1, 7)",
            (league_id,),
        )
        for name, team, goals, conceded, won, season in [
            ("Ronaldo", "InterHM", 2, 0, 1, "1997/98"),
            ("Baggio", "BolognaHM", 0, 2, 0, "1997/98"),
            ("Altro", "AltraStagioneHM", 1, 0, 1, "1998/99"),
        ]:
            cur = conn.execute(
                "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, 'A', ?, ?, 'archive')",
                (name, team, season),
            )
            conn.execute(
                "INSERT INTO historic_rating (player_historic_id, matchday, rating, goals,"
                " goals_conceded, team_won, minutes, source) VALUES (?, 7, 7.0, ?, ?, ?, 90, 'archive')",
                (cur.lastrowid, goals, conceded, won),
            )
    r = client.get(f"/lega/{league_id}/giornata/1")
    assert r.status_code == 200
    assert "Giornata storica G7" in r.text
    assert "BolognaHM <strong>0 - 2</strong> InterHM" in r.text
    assert "Ronaldo ×2" in r.text
    assert "AltraStagioneHM" not in r.text
