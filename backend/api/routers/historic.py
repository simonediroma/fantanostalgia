"""
Admin endpoint per importare dati storici da CSV generato da backend/scrapers/fbref.py.

POST /admin/historic/import
  Accetta il CSV esportato dallo scraper e popola player_historic + historic_rating.
  Idempotente: righe già presenti vengono saltate (INSERT OR IGNORE).
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin
from backend.utils.season import normalize_season

router = APIRouter(prefix="/admin/historic", tags=["historic"])

_REQUIRED_FIELDS = {
    "player_name", "role", "team", "season", "matchday",
    "rating", "goals", "yellow_cards", "red_cards", "goals_conceded",
    "team_won", "minutes",
}

_VALID_ROLES = {"P", "D", "C", "A"}

_normalize_season = normalize_season


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    missing = _REQUIRED_FIELDS - set(reader.fieldnames or [])
    if missing:
        raise HTTPException(400, f"Colonne mancanti nel CSV: {', '.join(sorted(missing))}")

    rows = []
    for i, row in enumerate(reader, start=2):
        role = row["role"].strip().upper()
        if role not in _VALID_ROLES:
            raise HTTPException(400, f"Riga {i}: ruolo non valido '{role}'")
        try:
            rows.append({
                "player_name": row["player_name"].strip(),
                "role": role,
                "team": row["team"].strip(),
                "season": _normalize_season(row["season"].strip()),
                "matchday": int(row["matchday"]),
                "rating": float(row["rating"]),
                "goals": int(row["goals"]),
                "yellow_cards": int(row["yellow_cards"]),
                "red_cards": int(row["red_cards"]),
                "goals_conceded": int(row["goals_conceded"]),
                "team_won": int(row["team_won"]),
                "minutes": int(row["minutes"]),
            })
        except (ValueError, KeyError) as e:
            raise HTTPException(400, f"Riga {i}: formato non valido — {e}")

    return rows


def _upsert_player(conn, name: str, role: str, team: str, season: str) -> int:
    row = conn.execute(
        "SELECT id FROM player_historic WHERE name = ? AND team = ? AND season = ?",
        (name, team, season),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, ?, ?, ?, 'synthetic')",
        (name, role, team, season),
    )
    return cur.lastrowid


@router.post("/import")
async def import_historic_csv(
    file: UploadFile,
    _admin=Depends(get_current_admin),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Il file deve essere un CSV")

    content = await file.read()
    rows = _parse_csv(content)

    if not rows:
        raise HTTPException(400, "CSV vuoto")

    ratings_inserted = 0
    season = rows[0]["season"]

    # Build the raw (un-normalized) season string so we can delete any rows
    # that were previously imported with the old YYYY-YYYY format.
    raw_season_parts = season.split("/")
    old_format_season = None
    if len(raw_season_parts) == 2 and len(raw_season_parts[0]) == 4 and len(raw_season_parts[1]) == 2:
        old_format_season = f"{raw_season_parts[0]}-{raw_season_parts[0][:2]}{raw_season_parts[1]}"

    with get_db() as conn:
        if old_format_season:
            conn.execute(
                "DELETE FROM player_historic WHERE season = ?", (old_format_season,)
            )

        for row in rows:
            pid = _upsert_player(
                conn,
                row["player_name"],
                row["role"],
                row["team"],
                row["season"],
            )
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO historic_rating
                  (player_historic_id, matchday, rating, goals, assists,
                   yellow_cards, red_cards, own_goals, penalties_scored,
                   penalties_missed, goals_conceded, team_won, minutes, source)
                VALUES (?, ?, ?, ?, 0, ?, ?, 0, 0, 0, ?, ?, ?, 'synthetic')
                """,
                (
                    pid,
                    row["matchday"],
                    row["rating"],
                    row["goals"],
                    row["yellow_cards"],
                    row["red_cards"],
                    row["goals_conceded"],
                    row["team_won"],
                    row["minutes"],
                ),
            )
            if cur.rowcount:
                ratings_inserted += 1

    return {
        "season": season,
        "rows_processed": len(rows),
        "ratings_imported": ratings_inserted,
        "message": f"Importazione completata — {ratings_inserted} voti inseriti per stagione {season}",
    }
