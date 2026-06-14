"""
Converte il CSV esportato dal plugin Chrome "Web Scraper" nel formato
compatibile con POST /admin/historic/import.

Il CSV di Web Scraper ha colonne:
  web-scraper-order, web-scraper-start-url, match_link, match_link-href,
  player_name, position, minutes, goals, yellow_card, red_card

Output: CSV con colonne standard (player_name, role, team, season,
        matchday, rating, goals, yellow_cards, red_cards, goals_conceded,
        team_won, minutes)

NOTA: Web Scraper non cattura il risultato della partita né il team del
giocatore (la tabella summary su fbref non ha la colonna team). Questi
valori vengono derivati dall'URL del match report e dall'ordine delle
tabelle home/away.

Usage:
    python -m backend.scrapers.convert_webscraper \\
        --input webscraper_export.csv \\
        --season 2005-2006 \\
        --output fbref_2005-2006.csv
"""

import argparse
import csv
import logging
import re
import sys

from backend.engine.rating import RatingWeights, compute_rating

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_POSITION_MAP = {
    "GK": "P",
    "DF": "D",
    "MF": "C",
    "FW": "A",
}

CSV_OUT_FIELDS = [
    "player_name", "role", "team", "season", "matchday",
    "rating", "goals", "yellow_cards", "red_cards",
    "goals_conceded", "team_won", "minutes",
]


def _map_position(pos_raw: str) -> str:
    primary = pos_raw.split(",")[0].strip()
    return _POSITION_MAP.get(primary, "C")


def _int(val: str) -> int:
    try:
        return int(val.strip()) if val.strip() else 0
    except ValueError:
        return 0


def _extract_match_info(href: str) -> dict | None:
    """
    Estrae home_team, away_team dall'URL del match report fbref.
    Formato: /en/matches/{id}/{Home}-vs-{Away}-{date}-Serie-A
    """
    m = re.search(r"/en/matches/[^/]+/(.+?)-vs-(.+?)-(\d{4}-\d{2}-\d{2})", href)
    if not m:
        return None
    home = m.group(1).replace("-", " ").title()
    away = m.group(2).replace("-", " ").title()
    return {"home_team": home, "away_team": away}


def _parse_score(val: str) -> int:
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return -1


def convert(input_path: str, season: str, output_path: str, weights: RatingWeights) -> None:
    with open(input_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        log.error("CSV vuoto.")
        sys.exit(1)

    # Raggruppa per match (match_link-href)
    matches: dict[str, list[dict]] = {}
    for row in rows:
        href = row.get("match_link-href", "")
        if not href or not row.get("player_name", "").strip():
            continue
        matches.setdefault(href, []).append(row)

    log.info("%d match trovati nel CSV.", len(matches))

    out_rows = []
    for href, player_rows in matches.items():
        match_info = _extract_match_info(href)
        if not match_info:
            log.warning("Impossibile estrarre info match da URL: %s", href)
            continue

        # Prova a ricavare il risultato dai campi home_score/away_score
        first = player_rows[0]
        home_score = _parse_score(first.get("home_score", ""))
        away_score = _parse_score(first.get("away_score", ""))
        score_available = home_score >= 0 and away_score >= 0

        if not score_available:
            log.warning(
                "Match %s vs %s: risultato non disponibile. "
                "team_won e goals_conceded saranno 0.",
                match_info["home_team"],
                match_info["away_team"],
            )

        home_won = score_available and home_score > away_score
        away_won = score_available and away_score > home_score

        # Prova a ricavare matchday dal campo se presente
        matchday = _int(first.get("matchday", "0")) or 0

        # Le prime ~11 righe sono home, le successive ~11 sono away
        # (ordine tabelle fbref: sempre home prima, away dopo)
        mid = len(player_rows) // 2
        for i, p in enumerate(player_rows):
            is_home = i < mid
            team = match_info["home_team"] if is_home else match_info["away_team"]
            minutes = _int(p.get("minutes", "0"))
            if minutes == 0:
                continue

            role = _map_position(p.get("position", ""))
            goals = _int(p.get("goals", "0"))
            yellow = _int(p.get("yellow_card", "0"))
            red = _int(p.get("red_card", "0"))

            if score_available:
                team_won = home_won if is_home else away_won
                # goals conceded = goals scored by the opponent
                goals_conceded = away_score if is_home else home_score
            else:
                team_won = False
                goals_conceded = 0

            rating = compute_rating(
                goals=goals,
                yellow_cards=yellow,
                red_cards=red,
                minutes=minutes,
                team_won=team_won,
                is_goalkeeper=role == "P",
                goals_conceded=goals_conceded,
                weights=weights,
            )

            out_rows.append({
                "player_name": p.get("player_name", "").strip(),
                "role": role,
                "team": team,
                "season": season,
                "matchday": matchday,
                "rating": rating,
                "goals": goals,
                "yellow_cards": yellow,
                "red_cards": red,
                "goals_conceded": goals_conceded,
                "team_won": 1 if team_won else 0,
                "minutes": minutes,
            })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_OUT_FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    log.info("Convertite %d righe → %s", len(out_rows), output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converti CSV Web Scraper → formato import admin"
    )
    parser.add_argument("--input", required=True, help="CSV esportato da Web Scraper")
    parser.add_argument("--season", required=True, help="Stagione es. 2005-2006")
    parser.add_argument("--output", required=True, help="CSV di output")
    parser.add_argument("--weights-file", metavar="FILE", help="JSON pesi rating")
    args = parser.parse_args()

    w = RatingWeights.from_json(args.weights_file) if args.weights_file else RatingWeights()
    convert(args.input, args.season, args.output, w)
