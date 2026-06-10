import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

GOAL_BONUS = {"P": 3.0, "D": 4.0, "C": 3.5, "A": 3.0}


def _formula(
    rating: float,
    role: str,
    goals: int,
    assists: int,
    yellow_cards: int,
    red_cards: int,
    own_goals: int,
    penalties_missed: int,
    goals_conceded: int,
    penalties_saved: int = 0,
    minutes_ge_60: bool = True,
    apply_bonus: bool = True,
) -> float:
    score = rating
    if apply_bonus:
        score += goals * GOAL_BONUS.get(role, 3.0)
        score += assists * 1.0
        if role == "P":
            score += penalties_saved * 1.0
            if goals_conceded == 0 and minutes_ge_60:
                score += 1.0
        elif role == "D" and goals_conceded == 0 and minutes_ge_60:
            score += 0.5
    score -= yellow_cards * 0.5
    score -= red_cards * 1.0
    score -= own_goals * 1.0
    score -= penalties_missed * 3.0
    if role == "P":
        score -= (goals_conceded // 2) * 1.0
    return score


@dataclass
class ManagerScore:
    manager_id: int
    manager_name: str
    score_normal: Optional[float]
    score_nostalgia: float


@dataclass
class ScoringResult:
    matchday: int
    matchday_historic: int
    scores: list[ManagerScore] = field(default_factory=list)


def calculate_scores(
    conn: sqlite3.Connection,
    league_id: int,
    matchday_current: int,
    real_ratings: list[dict] | None = None,
) -> ScoringResult:
    draw = conn.execute(
        "SELECT matchday_historic FROM matchday_draw"
        " WHERE league_id = ? AND matchday_current = ?",
        (league_id, matchday_current),
    ).fetchone()
    if draw is None:
        raise ValueError(f"Sorteggio non trovato per giornata {matchday_current}")
    matchday_historic = draw["matchday_historic"]

    managers = conn.execute(
        "SELECT id, name FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()

    lineups = conn.execute(
        """
        SELECT l.manager_id, l.player_current_id, pc.name, pc.role
        FROM lineup l
        JOIN player_current pc ON pc.id = l.player_current_id
        WHERE l.league_id = ? AND l.matchday = ? AND l.is_starter = 1
        """,
        (league_id, matchday_current),
    ).fetchall()

    manager_players: dict[int, list[dict]] = defaultdict(list)
    for row in lineups:
        manager_players[row["manager_id"]].append(dict(row))

    alter_egos = conn.execute(
        "SELECT player_current_id, player_historic_id FROM alter_ego WHERE league_id = ?",
        (league_id,),
    ).fetchall()
    alter_ego_map = {r["player_current_id"]: r["player_historic_id"] for r in alter_egos}

    historic_ids = list(alter_ego_map.values())
    rating_map: dict[int, dict] = {}
    if historic_ids:
        ph = ",".join("?" * len(historic_ids))
        rows = conn.execute(
            f"""
            SELECT hr.player_historic_id, hr.rating, hr.source,
                   hr.goals, hr.assists, hr.yellow_cards, hr.red_cards,
                   hr.own_goals, hr.penalties_missed, hr.goals_conceded,
                   ph.role
            FROM historic_rating hr
            JOIN player_historic ph ON ph.id = hr.player_historic_id
            WHERE hr.player_historic_id IN ({ph}) AND hr.matchday = ?
            """,
            (*historic_ids, matchday_historic),
        ).fetchall()
        rating_map = {r["player_historic_id"]: dict(r) for r in rows}

    real_map: dict[str, dict] = {}
    if real_ratings:
        for rr in real_ratings:
            real_map[rr["player_name"].strip().lower()] = rr

    results: list[ManagerScore] = []
    for mgr in managers:
        mid = mgr["id"]
        players = manager_players.get(mid, [])

        total_normal: Optional[float] = 0.0 if real_ratings is not None else None
        total_nostalgia = 0.0

        for p in players:
            pcid = p["player_current_id"]
            role = p["role"]
            name_key = p["name"].strip().lower()

            # Nostalgia score
            hist_id = alter_ego_map.get(pcid)
            if hist_id is not None:
                hr = rating_map.get(hist_id)
                if hr is None or hr["rating"] is None:
                    # Alter ego not available or sv → 6.0
                    ns = 6.0
                elif hr["source"] == "archive":
                    # Archive vote already includes bonus/malus
                    ns = float(hr["rating"])
                else:
                    ns = _formula(
                        rating=hr["rating"],
                        role=hr["role"],
                        goals=hr["goals"] or 0,
                        assists=hr["assists"] or 0,
                        yellow_cards=hr["yellow_cards"] or 0,
                        red_cards=hr["red_cards"] or 0,
                        own_goals=hr["own_goals"] or 0,
                        penalties_missed=hr["penalties_missed"] or 0,
                        goals_conceded=hr["goals_conceded"] or 0,
                        minutes_ge_60=hr["rating"] >= 6.0,
                        apply_bonus=True,
                    )
            else:
                rr = real_map.get(name_key)
                if rr is None:
                    ns = 6.0
                else:
                    ns = _formula(
                        rating=rr["rating"],
                        role=role,
                        goals=rr.get("goals", 0),
                        assists=rr.get("assists", 0),
                        yellow_cards=rr.get("yellow_cards", 0),
                        red_cards=rr.get("red_cards", 0),
                        own_goals=rr.get("own_goals", 0),
                        penalties_missed=rr.get("penalties_missed", 0),
                        goals_conceded=rr.get("goals_conceded", 0),
                        apply_bonus=False,
                    )
            total_nostalgia += ns

            # Normal score
            if total_normal is not None:
                rr = real_map.get(name_key)
                if rr is None:
                    total_normal += 6.0
                else:
                    total_normal += _formula(
                        rating=rr["rating"],
                        role=role,
                        goals=rr.get("goals", 0),
                        assists=rr.get("assists", 0),
                        yellow_cards=rr.get("yellow_cards", 0),
                        red_cards=rr.get("red_cards", 0),
                        own_goals=rr.get("own_goals", 0),
                        penalties_missed=rr.get("penalties_missed", 0),
                        goals_conceded=rr.get("goals_conceded", 0),
                        penalties_saved=rr.get("penalties_saved", 0),
                        minutes_ge_60=rr.get("minutes", 90) >= 60,
                        apply_bonus=True,
                    )

        results.append(ManagerScore(
            manager_id=mid,
            manager_name=mgr["name"],
            score_normal=round(total_normal, 1) if total_normal is not None else None,
            score_nostalgia=round(total_nostalgia, 1),
        ))

    _persist_scores(conn, league_id, matchday_current, results)
    _update_standings(conn, league_id)

    return ScoringResult(
        matchday=matchday_current,
        matchday_historic=matchday_historic,
        scores=results,
    )


def _persist_scores(
    conn: sqlite3.Connection,
    league_id: int,
    matchday: int,
    scores: list[ManagerScore],
) -> None:
    for ms in scores:
        conn.execute(
            """
            INSERT INTO matchday_score
                (league_id, manager_id, matchday, score_normal, score_nostalgia, calculated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(league_id, manager_id, matchday)
            DO UPDATE SET score_normal     = excluded.score_normal,
                          score_nostalgia  = excluded.score_nostalgia,
                          calculated_at    = excluded.calculated_at
            """,
            (
                league_id,
                ms.manager_id,
                matchday,
                ms.score_normal if ms.score_normal is not None else 0.0,
                ms.score_nostalgia,
            ),
        )


def _update_standings(conn: sqlite3.Connection, league_id: int) -> None:
    managers = conn.execute(
        "SELECT id FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()

    for mgr in managers:
        mid = mgr["id"]
        totals = conn.execute(
            """
            SELECT COALESCE(SUM(score_normal), 0)    AS total_normal,
                   COALESCE(SUM(score_nostalgia), 0) AS total_nostalgia
            FROM matchday_score WHERE league_id = ? AND manager_id = ?
            """,
            (league_id, mid),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO standings
                (league_id, manager_id, total_score_normal, total_score_nostalgia, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(league_id, manager_id)
            DO UPDATE SET total_score_normal     = excluded.total_score_normal,
                          total_score_nostalgia  = excluded.total_score_nostalgia,
                          updated_at             = excluded.updated_at
            """,
            (league_id, mid, totals["total_normal"], totals["total_nostalgia"]),
        )

    for col, rank_col in (
        ("total_score_normal", "rank_normal"),
        ("total_score_nostalgia", "rank_nostalgia"),
    ):
        rows = conn.execute(
            f"SELECT manager_id FROM standings WHERE league_id = ? ORDER BY {col} DESC",
            (league_id,),
        ).fetchall()
        for rank, row in enumerate(rows, 1):
            conn.execute(
                f"UPDATE standings SET {rank_col} = ? WHERE league_id = ? AND manager_id = ?",
                (rank, league_id, row["manager_id"]),
            )
