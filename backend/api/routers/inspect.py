"""
Endpoint di sola lettura per ispezionare i dati storici importati nel DB.

Utili per verificare la qualità dei dati dopo l'import e confrontarli con la fonte.

Tutte le route sono pubbliche (no auth) perché sono strumenti diagnostici.
Le stagioni nei path usano il formato YYYY-YY (es. 2016-17) che internamente
viene convertito nel formato DB YYYY/YY (es. 2016/17).
"""

from fastapi import APIRouter, HTTPException, Query
from backend.api.db import get_db

router = APIRouter(prefix="/inspect", tags=["inspect"])


def _season_to_db(season_slug: str) -> str:
    """Normalizza il formato stagione per le query al DB.
    Il DB può contenere sia YYYY-YY (scraper) che YYYY/YY (formato canonico).
    Accetta entrambi e li passa attraverso; converte solo YYYY-YYYY → YYYY-YY."""
    if "-" in season_slug and "/" not in season_slug:
        parts = season_slug.split("-")
        # YYYY-YYYY → YYYY-YY  (es. 2000-2001 → 2000-01)
        if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 4:
            return f"{parts[0]}-{parts[1][2:]}"
    # YYYY/YY → YYYY-YY  (es. 2000/01 → 2000-01)
    if "/" in season_slug:
        return season_slug.replace("/", "-")
    return season_slug


# ---------------------------------------------------------------------------
# /inspect/seasons
# ---------------------------------------------------------------------------

@router.get("/seasons")
def list_seasons():
    """Elenca tutte le stagioni presenti nel DB con statistiche di copertura."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                ph.season,
                ph.source,
                COUNT(DISTINCT ph.id)          AS players,
                COUNT(DISTINCT ph.team)        AS teams,
                COUNT(hr.id)                   AS total_ratings,
                COUNT(DISTINCT hr.matchday)    AS matchdays_covered,
                MIN(hr.matchday)               AS first_matchday,
                MAX(hr.matchday)               AS last_matchday
            FROM player_historic ph
            LEFT JOIN historic_rating hr ON hr.player_historic_id = ph.id
            GROUP BY ph.season, ph.source
            ORDER BY ph.season DESC, ph.source
            """
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# /inspect/seasons/{season}
# ---------------------------------------------------------------------------

@router.get("/seasons/{season}")
def season_summary(season: str):
    """
    Riepilogo di una stagione: distribuzione per ruolo e squadra, copertura giornate.
    Formato season nel path: YYYY-YY (es. 2016-17).
    """
    db_season = _season_to_db(season)
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM player_historic WHERE season = ? LIMIT 1", (db_season,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, f"Stagione '{db_season}' non trovata nel DB")

        by_role = conn.execute(
            """
            SELECT role, COUNT(*) AS players
            FROM player_historic WHERE season = ?
            GROUP BY role ORDER BY role
            """,
            (db_season,),
        ).fetchall()

        by_team = conn.execute(
            """
            SELECT team, COUNT(*) AS players
            FROM player_historic WHERE season = ?
            GROUP BY team ORDER BY players DESC
            """,
            (db_season,),
        ).fetchall()

        matchday_coverage = conn.execute(
            """
            SELECT hr.matchday,
                   COUNT(DISTINCT hr.player_historic_id) AS players_with_rating,
                   ROUND(AVG(hr.rating), 2)              AS avg_rating,
                   SUM(hr.goals)                         AS total_goals,
                   SUM(hr.minutes)                       AS total_minutes
            FROM historic_rating hr
            JOIN player_historic ph ON ph.id = hr.player_historic_id
            WHERE ph.season = ?
            GROUP BY hr.matchday
            ORDER BY hr.matchday
            """,
            (db_season,),
        ).fetchall()

        source_info = conn.execute(
            """
            SELECT source, COUNT(*) AS players
            FROM player_historic WHERE season = ?
            GROUP BY source
            """,
            (db_season,),
        ).fetchall()

    return {
        "season": db_season,
        "by_role": [dict(r) for r in by_role],
        "by_team": [dict(r) for r in by_team],
        "matchday_coverage": [dict(r) for r in matchday_coverage],
        "sources": [dict(r) for r in source_info],
    }


# ---------------------------------------------------------------------------
# /inspect/seasons/{season}/players
# ---------------------------------------------------------------------------

@router.get("/seasons/{season}/players")
def list_players(
    season: str,
    role: str | None = Query(None, description="Filtra per ruolo: P, D, C, A"),
    team: str | None = Query(None, description="Filtra per squadra reale (case-insensitive, match parziale)"),
    name: str | None = Query(None, description="Cerca per nome (case-insensitive, match parziale)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista giocatori storici di una stagione con statistiche aggregate.
    Supporta filtri per ruolo, squadra e nome.
    """
    db_season = _season_to_db(season)

    conditions = ["ph.season = ?"]
    params: list = [db_season]

    if role:
        role_upper = role.strip().upper()
        if role_upper not in {"P", "D", "C", "A"}:
            raise HTTPException(400, "Ruolo non valido: usa P, D, C o A")
        conditions.append("ph.role = ?")
        params.append(role_upper)

    if team:
        conditions.append("ph.team LIKE ?")
        params.append(f"%{team}%")

    if name:
        conditions.append("ph.name LIKE ?")
        params.append(f"%{name}%")

    where = " AND ".join(conditions)

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM player_historic ph WHERE {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT
                ph.id,
                ph.name,
                ph.role,
                ph.team,
                ph.season,
                ph.source,
                COUNT(hr.id)              AS matchdays_played,
                ROUND(AVG(hr.rating), 2)  AS avg_rating,
                SUM(hr.goals)             AS total_goals,
                SUM(hr.assists)           AS total_assists,
                SUM(hr.yellow_cards)      AS total_yellow,
                SUM(hr.red_cards)         AS total_red,
                SUM(hr.minutes)           AS total_minutes
            FROM player_historic ph
            LEFT JOIN historic_rating hr ON hr.player_historic_id = ph.id
            WHERE {where}
            GROUP BY ph.id
            ORDER BY ph.name
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    return {
        "season": db_season,
        "total": total,
        "limit": limit,
        "offset": offset,
        "players": [dict(r) for r in rows],
    }


# ---------------------------------------------------------------------------
# /inspect/players/{player_id}
# ---------------------------------------------------------------------------

@router.get("/players/{player_id}")
def player_detail(player_id: int):
    """
    Dettaglio completo di un giocatore storico: anagrafica + voti giornata per giornata.
    Utile per confrontare i dati importati con la fonte originale.
    """
    with get_db() as conn:
        player = conn.execute(
            "SELECT * FROM player_historic WHERE id = ?", (player_id,)
        ).fetchone()
        if not player:
            raise HTTPException(404, f"Giocatore id={player_id} non trovato")

        ratings = conn.execute(
            """
            SELECT matchday, rating, goals, assists,
                   yellow_cards, red_cards, own_goals,
                   penalties_scored, penalties_missed,
                   goals_conceded, team_won, minutes, source
            FROM historic_rating
            WHERE player_historic_id = ?
            ORDER BY matchday
            """,
            (player_id,),
        ).fetchall()

    return {
        "player": dict(player),
        "ratings": [dict(r) for r in ratings],
        "stats": {
            "matchdays_played": len(ratings),
            "avg_rating": round(sum(r["rating"] for r in ratings) / len(ratings), 2) if ratings else None,
            "total_goals": sum(r["goals"] for r in ratings),
            "total_assists": sum(r["assists"] for r in ratings),
            "total_yellow": sum(r["yellow_cards"] for r in ratings),
            "total_red": sum(r["red_cards"] for r in ratings),
            "total_minutes": sum(r["minutes"] for r in ratings),
        },
    }


# ---------------------------------------------------------------------------
# /inspect/seasons/{season}/matchday/{matchday}
# ---------------------------------------------------------------------------

@router.get("/seasons/{season}/matchday/{matchday}")
def matchday_detail(
    season: str,
    matchday: int,
    role: str | None = Query(None, description="Filtra per ruolo: P, D, C, A"),
    team: str | None = Query(None),
    min_rating: float | None = Query(None, description="Mostra solo voti >= soglia"),
):
    """
    Tutti i voti di una giornata specifica, con possibilità di filtrare per ruolo e squadra.
    Utile per verificare i dati di una singola giornata contro la fonte.
    """
    db_season = _season_to_db(season)

    conditions = ["ph.season = ?", "hr.matchday = ?"]
    params: list = [db_season, matchday]

    if role:
        role_upper = role.strip().upper()
        if role_upper not in {"P", "D", "C", "A"}:
            raise HTTPException(400, "Ruolo non valido: usa P, D, C o A")
        conditions.append("ph.role = ?")
        params.append(role_upper)

    if team:
        conditions.append("ph.team LIKE ?")
        params.append(f"%{team}%")

    if min_rating is not None:
        conditions.append("hr.rating >= ?")
        params.append(min_rating)

    where = " AND ".join(conditions)

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                ph.id              AS player_id,
                ph.name,
                ph.role,
                ph.team,
                hr.rating,
                hr.goals,
                hr.assists,
                hr.yellow_cards,
                hr.red_cards,
                hr.own_goals,
                hr.penalties_scored,
                hr.penalties_missed,
                hr.goals_conceded,
                hr.team_won,
                hr.minutes,
                hr.source
            FROM historic_rating hr
            JOIN player_historic ph ON ph.id = hr.player_historic_id
            WHERE {where}
            ORDER BY ph.role, hr.rating DESC
            """,
            params,
        ).fetchall()

    if not rows:
        raise HTTPException(404, f"Nessun dato per stagione '{db_season}' giornata {matchday}")

    return {
        "season": db_season,
        "matchday": matchday,
        "players": len(rows),
        "avg_rating": round(sum(r["rating"] for r in rows) / len(rows), 2),
        "ratings": [dict(r) for r in rows],
    }


# ---------------------------------------------------------------------------
# /inspect/seasons/{season}/teams
# ---------------------------------------------------------------------------

@router.get("/seasons/{season}/teams")
def season_teams(season: str):
    """
    Lista squadre reali presenti nella stagione con conteggio giocatori per ruolo.
    """
    db_season = _season_to_db(season)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                team,
                COUNT(*)                                          AS total,
                SUM(CASE WHEN role='P' THEN 1 ELSE 0 END)        AS portieri,
                SUM(CASE WHEN role='D' THEN 1 ELSE 0 END)        AS difensori,
                SUM(CASE WHEN role='C' THEN 1 ELSE 0 END)        AS centrocampisti,
                SUM(CASE WHEN role='A' THEN 1 ELSE 0 END)        AS attaccanti
            FROM player_historic
            WHERE season = ?
            GROUP BY team
            ORDER BY total DESC
            """,
            (db_season,),
        ).fetchall()

    if not rows:
        raise HTTPException(404, f"Stagione '{db_season}' non trovata nel DB")

    return {"season": db_season, "teams": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Logica condivisa trend
# ---------------------------------------------------------------------------

def _compute_trend(player_id: int, window: int) -> dict:
    with get_db() as conn:
        player = conn.execute(
            "SELECT * FROM player_historic WHERE id = ?", (player_id,)
        ).fetchone()
        if not player:
            raise HTTPException(404, f"Giocatore id={player_id} non trovato")

        raw = conn.execute(
            """
            SELECT matchday, rating, goals, assists,
                   yellow_cards, red_cards, goals_conceded, team_won, minutes
            FROM historic_rating
            WHERE player_historic_id = ?
            ORDER BY matchday
            """,
            (player_id,),
        ).fetchall()

    if not raw:
        return {"player": dict(player), "window": window, "season_avg": None, "trend": []}

    ratings = [r["rating"] for r in raw]
    season_avg = round(sum(ratings) / len(ratings), 2)

    trend = []
    for i, r in enumerate(raw):
        window_ratings = ratings[max(0, i - window + 1): i + 1]
        moving_avg = round(sum(window_ratings) / len(window_ratings), 2)
        delta = round(r["rating"] - raw[i - 1]["rating"], 2) if i > 0 else None
        trend.append({
            "matchday": r["matchday"],
            "rating": r["rating"],
            "moving_avg": moving_avg,
            "delta": delta,
            "forma": round(moving_avg - season_avg, 2),
            "goals": r["goals"],
            "assists": r["assists"],
            "yellow_cards": r["yellow_cards"],
            "red_cards": r["red_cards"],
            "goals_conceded": r["goals_conceded"],
            "team_won": r["team_won"],
            "minutes": r["minutes"],
        })

    played = [t for t in trend if t["minutes"] > 0]
    best = max(trend, key=lambda t: t["rating"])
    worst = min(played, key=lambda t: t["rating"]) if played else min(trend, key=lambda t: t["rating"])
    last_n = trend[-window:]
    recent_avg = round(sum(t["rating"] for t in last_n) / len(last_n), 2)

    return {
        "player": dict(player),
        "window": window,
        "season_avg": season_avg,
        "recent_avg": recent_avg,
        "forma_recente": round(recent_avg - season_avg, 2),
        "best_matchday": {"matchday": best["matchday"], "rating": best["rating"]},
        "worst_matchday": {"matchday": worst["matchday"], "rating": worst["rating"]},
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# /inspect/players/{player_id}/trend
# /inspect/trend?name=...&season=...
# ---------------------------------------------------------------------------

@router.get("/trend")
def player_trend_by_name(
    name: str = Query(..., min_length=2, description="Nome (parziale) del giocatore"),
    season: str = Query(..., description="Stagione in formato YYYY-YY (es. 2016-17)"),
    window: int = Query(5, ge=2, le=10, description="Ampiezza della media mobile (default 5)"),
):
    """
    Andamento di un giocatore cercato per nome e stagione.
    Se il nome matcha più giocatori restituisce la lista di candidati invece del trend.
    """
    db_season = _season_to_db(season)
    with get_db() as conn:
        matches = conn.execute(
            "SELECT id, name, role, team FROM player_historic WHERE name LIKE ? AND season = ? ORDER BY name",
            (f"%{name}%", db_season),
        ).fetchall()

    if not matches:
        raise HTTPException(404, f"Nessun giocatore trovato per nome '{name}' nella stagione {db_season}")

    if len(matches) > 1:
        return {
            "ambiguous": True,
            "query": name,
            "season": db_season,
            "candidates": [dict(m) for m in matches],
            "hint": "Usa un nome più preciso oppure /inspect/players/{player_id}/trend con l'id esatto",
        }

    return _compute_trend(matches[0]["id"], window)


@router.get("/players/{player_id}/trend")
def player_trend(
    player_id: int,
    window: int = Query(5, ge=2, le=10, description="Ampiezza della media mobile (default 5)"),
):
    """Andamento di un giocatore per id. Vedi anche GET /inspect/trend?name=&season=."""
    return _compute_trend(player_id, window)


# ---------------------------------------------------------------------------
# /inspect/search
# ---------------------------------------------------------------------------

@router.get("/search")
def search_players(
    name: str = Query(..., min_length=2, description="Nome (parziale) del giocatore"),
    season: str | None = Query(None, description="Stagione opzionale formato YYYY-YY"),
):
    """
    Cerca un giocatore per nome in tutte le stagioni (o solo in quella specificata).
    Restituisce anche le statistiche aggregate per confronto rapido.
    """
    conditions = ["ph.name LIKE ?"]
    params: list = [f"%{name}%"]

    if season:
        conditions.append("ph.season = ?")
        params.append(_season_to_db(season))

    where = " AND ".join(conditions)

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                ph.id,
                ph.name,
                ph.role,
                ph.team,
                ph.season,
                ph.source,
                COUNT(hr.id)              AS matchdays_played,
                ROUND(AVG(hr.rating), 2)  AS avg_rating,
                SUM(hr.goals)             AS total_goals,
                MIN(hr.rating)            AS min_rating,
                MAX(hr.rating)            AS max_rating
            FROM player_historic ph
            LEFT JOIN historic_rating hr ON hr.player_historic_id = ph.id
            WHERE {where}
            GROUP BY ph.id
            ORDER BY ph.season DESC, ph.name
            LIMIT 50
            """,
            params,
        ).fetchall()

    return {"query": name, "results": [dict(r) for r in rows]}
