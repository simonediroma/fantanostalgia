"""
Admin endpoint per importare dati storici da CSV generato da backend/scrapers/fbref.py.

POST /admin/historic/import
  Accetta il CSV esportato dallo scraper e popola player_historic + historic_rating.
  Idempotente: righe già presenti vengono saltate (INSERT OR IGNORE).

POST /admin/historic/normalize-seasons
  Bonifica il DB convertendo tutti i valori di season al formato canonico YYYY/YY.
"""

import csv
import io
import sqlite3

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


def _season_variants(canonical: str) -> list[str]:
    parts = canonical.split("/")
    if len(parts) != 2:
        return [canonical]
    y1 = int(parts[0])
    yy = parts[1]
    y2 = y1 + 1
    return [canonical, f"{y1}-{yy}", f"{y1}-{y2:04d}"]


def _safe_exec(conn, sql: str, params=None):
    """Esegue SQL ignorando l'errore se la tabella non esiste (schema vecchio)."""
    try:
        conn.execute(sql, params or [])
    except sqlite3.OperationalError as e:
        if "no such table" in str(e) or "no such column" in str(e):
            pass
        else:
            raise


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
                "season": normalize_season(row["season"].strip()),
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

    # Pulisce eventuali righe precedentemente importate con formati non canonici
    old_formats = [v for v in _season_variants(season) if v != season]

    already_present = 0

    with get_db() as conn:
        for old_fmt in old_formats:
            conn.execute("DELETE FROM player_historic WHERE season = ?", (old_fmt,))

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
            else:
                already_present += 1

    if ratings_inserted == 0 and already_present > 0:
        message = (
            f"Stagione {season} già presente nel DB ({already_present} voti esistenti, nessuna modifica). "
            "Usa /admin/historic/flush?season=... per reimportare da zero."
        )
    else:
        message = f"Importazione completata — {ratings_inserted} voti inseriti per stagione {season}"
        if already_present:
            message += f" ({already_present} già presenti, saltati)"

    return {
        "season": season,
        "rows_processed": len(rows),
        "ratings_imported": ratings_inserted,
        "already_present": already_present,
        "message": message,
    }


@router.post("/normalize-seasons")
def normalize_seasons_in_db(_admin=Depends(get_current_admin)):
    """
    Bonifica il DB convertendo tutti i valori di player_historic.season
    al formato canonico YYYY/YY (es. '2000-01' → '2000/01').

    Operazione idempotente e sicura:
    - Se la forma canonica esiste già, segnala il conflitto senza toccare nulla.
    - Aggiorna anche league.season_historic se non canonico.
    - Restituisce un report completo delle modifiche effettuate.
    """
    with get_db() as conn:
        # --- player_historic ---
        all_seasons = conn.execute(
            "SELECT DISTINCT season FROM player_historic"
        ).fetchall()

        updated = []
        skipped_conflicts = []

        for row in all_seasons:
            raw = row["season"]
            canonical = normalize_season(raw)
            if raw == canonical:
                continue  # già nel formato giusto

            # Controlla se la forma canonica esiste già nel DB
            conflict = conn.execute(
                "SELECT COUNT(*) FROM player_historic WHERE season = ?",
                (canonical,),
            ).fetchone()[0]

            if conflict:
                skipped_conflicts.append({
                    "raw": raw,
                    "canonical": canonical,
                    "reason": "stagione canonica già presente — merge non automatico",
                })
                continue

            conn.execute(
                "UPDATE player_historic SET season = ? WHERE season = ?",
                (canonical, raw),
            )
            updated.append({"from": raw, "to": canonical})

        # --- league.season_historic ---
        leagues = conn.execute(
            "SELECT id, season_historic FROM league WHERE season_historic IS NOT NULL"
        ).fetchall()

        leagues_updated = []
        for lg in leagues:
            raw = lg["season_historic"]
            canonical = normalize_season(raw)
            if raw != canonical:
                conn.execute(
                    "UPDATE league SET season_historic = ? WHERE id = ?",
                    (canonical, lg["id"]),
                )
                leagues_updated.append({"league_id": lg["id"], "from": raw, "to": canonical})

    return {
        "player_historic_updated": len(updated),
        "player_historic_conflicts": len(skipped_conflicts),
        "leagues_updated": len(leagues_updated),
        "changes": updated,
        "leagues_changes": leagues_updated,
        "conflicts": skipped_conflicts,
        "message": (
            f"Bonifica completata: {len(updated)} stagioni aggiornate, "
            f"{len(skipped_conflicts)} conflitti da risolvere manualmente, "
            f"{len(leagues_updated)} leghe aggiornate."
        ),
    }


@router.post("/flush")
def flush_historic_db(
    season: str | None = None,
    _admin=Depends(get_current_admin),
):
    """
    Cancella i dati storici dal DB per reimportarli da zero.

    - Senza parametri: cancella TUTTI i dati di player_historic e historic_rating.
    - Con ?season=YYYY/YY: cancella solo quella stagione (tutti i formati accettati).

    Le righe di historic_rating vengono eliminate in cascade.
    Le associazioni alter_ego e manager_nostalgia_pool che puntano ai giocatori
    cancellati vengono eliminate anch'esse (ON DELETE CASCADE nel DB).
    """
    try:
        with get_db() as conn:
            # Disabilita temporaneamente i FK per gestire manualmente l'ordine
            conn.execute("PRAGMA foreign_keys = OFF")

            if season:
                canonical = normalize_season(season)
                variants = _season_variants(canonical)

                placeholders = ",".join("?" * len(variants))
                ids = [
                    r["id"] for r in conn.execute(
                        f"SELECT id FROM player_historic WHERE season IN ({placeholders})",
                        variants,
                    ).fetchall()
                ]

                deleted_players = 0
                if ids:
                    id_ph = ",".join("?" * len(ids))
                    conn.execute(f"DELETE FROM historic_rating WHERE player_historic_id IN ({id_ph})", ids)
                    conn.execute(f"DELETE FROM alter_ego WHERE player_historic_id IN ({id_ph})", ids)
                    _safe_exec(conn, f"DELETE FROM manager_nostalgia_pool WHERE player_historic_id IN ({id_ph})", ids)
                    _safe_exec(conn, f"UPDATE gran_premio SET prize_player_historic_id = NULL WHERE prize_player_historic_id IN ({id_ph})", ids)
                    cur = conn.execute(f"DELETE FROM player_historic WHERE id IN ({id_ph})", ids)
                    deleted_players = cur.rowcount

                conn.execute("PRAGMA foreign_keys = ON")
                return {
                    "scope": "season",
                    "season": canonical,
                    "players_deleted": deleted_players,
                    "message": f"Stagione {canonical} rimossa ({deleted_players} giocatori eliminati).",
                }
            else:
                conn.execute("DELETE FROM historic_rating")
                conn.execute("DELETE FROM alter_ego")
                _safe_exec(conn, "DELETE FROM manager_nostalgia_pool")
                _safe_exec(conn, "UPDATE gran_premio SET prize_player_historic_id = NULL")
                cur_p = conn.execute("DELETE FROM player_historic")
                conn.execute("PRAGMA foreign_keys = ON")
                return {
                    "scope": "all",
                    "players_deleted": cur_p.rowcount,
                    "message": f"DB storico svuotato: {cur_p.rowcount} giocatori eliminati.",
                }
    except sqlite3.Error as e:
        raise HTTPException(500, f"Errore DB: {e}")
