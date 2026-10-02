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


def _nostalgia_score(
    p: dict,
    alter_ego_map: dict[int, int],
    rating_map: dict[int, dict],
    real_map: dict[str, dict],
) -> float:
    """Nostalgia score for a single starter (alter ego historic rating, or real
    rating without bonus if the player has no alter ego)."""
    pcid = p["player_current_id"]
    role = p["role"]
    name_key = p["name"].strip().lower()

    hist_id = alter_ego_map.get(pcid)
    if hist_id is not None:
        hr = rating_map.get(hist_id)
        if hr is None or hr["rating"] is None:
            # Alter ego not available or sv → 6.0
            return 6.0
        # Both archive and synthetic store hr.rating as the final computed score
        # (archive: real fantacalcio vote with bonuses; synthetic: compute_rating()
        # which already adds goal bonus, win bonus, card malus, etc.).
        # Applying _formula() on top would double-count goals for synthetic data.
        return float(hr["rating"])

    rr = real_map.get(name_key)
    if rr is None:
        return 6.0
    # Formazioni Excel import already ships a "voto senza bonus" (malus applied,
    # no goal/assist bonus) computed by the real fantacalcio scoring — use it
    # directly instead of rr["rating"], which for this path is score_bonus
    # (the full bonus-inclusive vote) and would leak bonus back in here.
    if "rating_no_bonus" in rr:
        rating_no_bonus = rr["rating_no_bonus"]
        return float(rating_no_bonus) if rating_no_bonus is not None else 6.0
    return _formula(
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


def _matchday_alter_egos(conn: sqlite3.Connection, league_id: int, lineups) -> dict[int, int]:
    """player_current_id → player_historic_id per le righe di una giornata: l'alter ego
    congelato nella formazione se presente, altrimenti l'associazione corrente."""
    current = {
        r["player_current_id"]: r["player_historic_id"]
        for r in conn.execute(
            "SELECT player_current_id, player_historic_id FROM alter_ego WHERE league_id = ?",
            (league_id,),
        )
    }
    out: dict[int, int] = {}
    for r in lineups:
        hid = r["alter_ego_id"] if r["alter_ego_frozen"] else current.get(r["player_current_id"])
        if hid is not None:
            out[r["player_current_id"]] = hid
    return out


def _historic_ratings(conn: sqlite3.Connection, historic_ids: list[int], matchday_historic: int) -> dict[int, dict]:
    if not historic_ids:
        return {}
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
    return {r["player_historic_id"]: dict(r) for r in rows}


def freeze_scored_alter_egos(conn: sqlite3.Connection, league_id: int) -> None:
    """Fissa nelle formazioni delle giornate già calcolate l'alter ego corrente, così un
    cambio di associazione successivo (es. giocatore uscito dalla rosa) non riscrive lo storico."""
    conn.execute(
        """
        UPDATE lineup SET alter_ego_frozen = 1, alter_ego_id = (
            SELECT ae.player_historic_id FROM alter_ego ae
            WHERE ae.league_id = lineup.league_id AND ae.player_current_id = lineup.player_current_id
            LIMIT 1)
        WHERE league_id = ? AND alter_ego_frozen = 0
          AND matchday IN (SELECT matchday FROM matchday_score WHERE league_id = ?)
        """,
        (league_id, league_id),
    )


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
        SELECT l.manager_id, l.player_current_id, pc.name, pc.role,
               l.score_no_bonus, l.score_bonus, l.alter_ego_id, l.alter_ego_frozen
        FROM lineup l
        JOIN player_current pc ON pc.id = l.player_current_id
        WHERE l.league_id = ? AND l.matchday = ? AND l.is_starter = 1
        """,
        (league_id, matchday_current),
    ).fetchall()

    manager_players: dict[int, list[dict]] = defaultdict(list)
    for row in lineups:
        manager_players[row["manager_id"]].append(dict(row))

    alter_ego_map = _matchday_alter_egos(conn, league_id, lineups)
    rating_map = _historic_ratings(conn, list(alter_ego_map.values()), matchday_historic)

    real_map: dict[str, dict] = {}
    if real_ratings:
        for rr in real_ratings:
            real_map[rr["player_name"].strip().lower()] = rr
    elif real_ratings is None:
        # Fall back to votes stored in lineup (imported from Formazioni Excel)
        stored = conn.execute(
            """
            SELECT pc.name, l.score_no_bonus, l.score_bonus
            FROM lineup l
            JOIN player_current pc ON pc.id = l.player_current_id
            WHERE l.league_id = ? AND l.matchday = ? AND l.score_bonus IS NOT NULL
            """,
            (league_id, matchday_current),
        ).fetchall()
        if stored:
            real_ratings = []  # mark as provided so score_normal is computed
            for s in stored:
                real_map[s["name"].strip().lower()] = {
                    "player_name": s["name"],
                    "rating": s["score_bonus"],
                    "rating_no_bonus": s["score_no_bonus"],
                    "goals": 0, "assists": 0, "yellow_cards": 0,
                    "red_cards": 0, "own_goals": 0,
                    "penalties_missed": 0, "goals_conceded": 0,
                    "penalties_saved": 0, "minutes": 90,
                }

    results: list[ManagerScore] = []
    for mgr in managers:
        mid = mgr["id"]
        players = manager_players.get(mid, [])

        total_normal: Optional[float] = 0.0 if real_ratings is not None else None
        total_nostalgia = 0.0

        for p in players:
            role = p["role"]
            name_key = p["name"].strip().lower()

            # Nostalgia score
            ns = _nostalgia_score(p, alter_ego_map, rating_map, real_map)
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


def compute_player_breakdown(
    conn: sqlite3.Connection, league_id: int, matchday_current: int
) -> list[dict]:
    """Per-starter nostalgia scores for a matchday, recomputed deterministically
    from persisted data (alter_ego + historic_rating). Returns one dict per
    starter: {manager_id, player_current_id, role, name, ns}.

    Players without an alter ego use the stored lineup.score_no_bonus (voto in
    pagella), matching calculate_scores without real_ratings."""
    draw = conn.execute(
        "SELECT matchday_historic FROM matchday_draw"
        " WHERE league_id = ? AND matchday_current = ?",
        (league_id, matchday_current),
    ).fetchone()
    if draw is None:
        raise ValueError(f"Sorteggio non trovato per giornata {matchday_current}")
    matchday_historic = draw["matchday_historic"]

    lineups = conn.execute(
        """
        SELECT l.manager_id, l.player_current_id, pc.name, pc.role,
               l.score_no_bonus, l.score_bonus, l.alter_ego_id, l.alter_ego_frozen
        FROM lineup l
        JOIN player_current pc ON pc.id = l.player_current_id
        WHERE l.league_id = ? AND l.matchday = ? AND l.is_starter = 1
        """,
        (league_id, matchday_current),
    ).fetchall()

    alter_ego_map = _matchday_alter_egos(conn, league_id, lineups)
    rating_map = _historic_ratings(conn, list(alter_ego_map.values()), matchday_historic)

    real_map = {
        r["name"].strip().lower(): {"rating": r["score_bonus"], "rating_no_bonus": r["score_no_bonus"]}
        for r in lineups if r["score_bonus"] is not None
    }

    breakdown: list[dict] = []
    for row in lineups:
        p = dict(row)
        breakdown.append({
            "manager_id": p["manager_id"],
            "player_current_id": p["player_current_id"],
            "role": p["role"],
            "name": p["name"],
            "ns": round(_nostalgia_score(p, alter_ego_map, rating_map, real_map), 1),
        })
    return breakdown


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
