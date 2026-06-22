"""
Ricalcola i rating storici nel DB usando nuovi pesi, senza riscrappare.

Richiede che team_won e minutes siano già presenti in historic_rating
(popolati dallo scraper fbref).

Usage:
    # ricalcola con pesi di default
    python -m backend.engine.recalculate --season 2023-2024

    # ricalcola con pesi custom
    python -m backend.engine.recalculate --season 2023-2024 --weights-file pesi.json

    # esporta i pesi di default per editarli
    python -m backend.engine.recalculate --dump-weights pesi.json
"""

import argparse
import logging
import sqlite3

from backend.api.db import ENV, _download_db_from_gcs, _get_db_path, _upload_db_to_gcs
from backend.engine.rating import RatingWeights, compute_rating

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def recalculate_season(season: str, weights: RatingWeights) -> int:
    """
    Aggiorna il campo rating per tutti i giocatori della stagione indicata.
    Restituisce il numero di righe aggiornate.
    """
    if ENV != "development":
        _download_db_from_gcs()

    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        rows = conn.execute(
            """
            SELECT hr.id, hr.goals, hr.yellow_cards, hr.red_cards,
                   hr.goals_conceded, hr.team_won, hr.minutes, ph.role
            FROM historic_rating hr
            JOIN player_historic ph ON hr.player_historic_id = ph.id
            WHERE ph.season = ? AND hr.source = 'synthetic'
            """,
            (season,),
        ).fetchall()

        if not rows:
            log.warning("Nessun dato trovato per stagione %s.", season)
            return 0

        updated = 0
        for row in rows:
            rating = compute_rating(
                goals=row["goals"],
                yellow_cards=row["yellow_cards"],
                red_cards=row["red_cards"],
                minutes=row["minutes"],
                team_won=bool(row["team_won"]),
                is_goalkeeper=row["role"] == "P",
                goals_conceded=row["goals_conceded"],
                weights=weights,
            )
            conn.execute(
                "UPDATE historic_rating SET rating = ? WHERE id = ?",
                (rating, row["id"]),
            )
            updated += 1

        conn.commit()
        log.info("Stagione %s: %d rating aggiornati.", season, updated)
        return updated

    finally:
        conn.close()
        if ENV != "development":
            _upload_db_to_gcs()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ricalcola rating storici con nuovi pesi")
    parser.add_argument("--season", help="Stagione es. 2023-2024")
    parser.add_argument("--weights-file", metavar="FILE", help="JSON con i pesi (default: pesi standard)")
    parser.add_argument("--dump-weights", metavar="FILE", help="Esporta i pesi di default e termina")
    args = parser.parse_args()

    if args.dump_weights:
        RatingWeights().to_json(args.dump_weights)
        log.info("Pesi di default esportati in %s", args.dump_weights)
    elif args.season:
        from backend.api.routers.historic import normalize_season
        weights = RatingWeights.from_json(args.weights_file) if args.weights_file else RatingWeights()
        recalculate_season(normalize_season(args.season), weights)
    else:
        parser.error("Specifica --season oppure --dump-weights")
