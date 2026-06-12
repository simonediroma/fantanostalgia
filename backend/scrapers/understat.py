"""
Scraper understat.com — statistiche storiche Serie A (2014-2015 in poi).
Alternativa a fbref.com: non usa Cloudflare, dati embedded come JSON.

Usage:
    python -m backend.scrapers.understat --season 2015-2016 --export-csv out.csv
    python -m backend.scrapers.understat --season 2022-2023 --export-csv out.csv --weights-file pesi.json
"""

import argparse
import csv
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

import requests

from backend.engine.rating import RatingWeights, compute_rating
from backend.scrapers.fbref import CSV_FIELDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

UNDERSTAT_BASE = "https://understat.com"

_POSITION_MAP = {
    "GK": "P",
    "D":  "D",
    "M":  "C",
    "AM": "A",
    "F":  "A",
    "S":  "A",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


def _fetch(session: requests.Session, url: str) -> str:
    time.sleep(2)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def _extract_json_var(html: str, var_name: str) -> Any:
    """Estrae la variabile JavaScript JSON embedded da understat."""
    pattern = rf"var\s+{re.escape(var_name)}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if not match:
        return None
    raw = match.group(1)
    # understat codifica i dati con escape unicode/hex
    decoded = raw.encode().decode("unicode_escape")
    return json.loads(decoded)


# ---------------------------------------------------------------------------
# Matchday assignment
# ---------------------------------------------------------------------------

def _assign_matchdays(matches: list[dict]) -> list[dict]:
    """
    Deriva il numero di giornata raggruppando le partite per finestre
    temporali: se due partite distano più di 4 giorni, è una nuova giornata.
    """
    if not matches:
        return matches

    sorted_m = sorted(matches, key=lambda m: m["datetime"])
    matchday = 1
    window_start = datetime.strptime(sorted_m[0]["datetime"], "%Y-%m-%d %H:%M:%S")

    for m in sorted_m:
        dt = datetime.strptime(m["datetime"], "%Y-%m-%d %H:%M:%S")
        if (dt - window_start).days > 4:
            matchday += 1
            window_start = dt
        m["matchday"] = matchday

    return sorted_m


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _get_matches(session: requests.Session, season: str) -> list[dict]:
    """
    Scarica la lista di tutte le partite completate per la stagione.
    season formato: '2015-2016' → year = 2015
    """
    year = season.split("-")[0]
    url = f"{UNDERSTAT_BASE}/league/Serie_A/{year}"
    html = _fetch(session, url)

    dates_data = _extract_json_var(html, "datesData")
    if not dates_data:
        raise ValueError(f"datesData non trovato per stagione {season} (URL: {url})")

    matches = []
    for m in dates_data:
        if not m.get("isResult"):
            continue
        matches.append({
            "id": m["id"],
            "datetime": m.get("datetime", "2000-01-01 00:00:00"),
            "home_team": m["h"]["title"],
            "away_team": m["a"]["title"],
            "home_score": int(m["goals"]["h"]),
            "away_score": int(m["goals"]["a"]),
            "matchday": 0,  # assegnato da _assign_matchdays
        })

    return _assign_matchdays(matches)


def _map_position(pos_raw: str) -> str:
    return _POSITION_MAP.get(pos_raw.strip(), "C")


def _get_player_stats(session: requests.Session, match: dict) -> list[dict]:
    """Scarica e restituisce le stats per giocatore di una singola partita."""
    url = f"{UNDERSTAT_BASE}/match/{match['id']}"
    html = _fetch(session, url)

    rosters_data = _extract_json_var(html, "rostersData")
    if not rosters_data:
        return []

    home_score = match["home_score"]
    away_score = match["away_score"]

    players = []
    for side, team_name, goals_conceded, team_won in [
        ("h", match["home_team"], away_score, home_score > away_score),
        ("a", match["away_team"], home_score, away_score > home_score),
    ]:
        roster = rosters_data.get(side, {})
        # roster può essere dict {id: player} o list [player]
        entries = roster.values() if isinstance(roster, dict) else roster

        for p in entries:
            minutes = int(p.get("time", 0))
            if minutes == 0:
                continue  # non entrato in campo — nessun voto

            role = _map_position(p.get("position", ""))
            is_gk = role == "P"

            players.append({
                "name": p.get("player", ""),
                "role": role,
                "team": team_name,
                "goals": int(p.get("goals", 0)),
                "yellow_cards": int(p.get("yellow_card", 0)),
                "red_cards": int(p.get("red_card", 0)),
                "goals_conceded": goals_conceded if is_gk else 0,
                "team_won": int(team_won),
                "minutes": minutes,
            })

    return players


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _collect_season(season: str, weights: RatingWeights) -> list[dict]:
    session = _build_session()

    log.info("Carico partite stagione %s da understat...", season)
    matches = _get_matches(session, season)
    log.info("%d partite trovate.", len(matches))

    records: list[dict] = []
    matchdays = sorted({m["matchday"] for m in matches})

    for md in matchdays:
        for match in [m for m in matches if m["matchday"] == md]:
            try:
                players = _get_player_stats(session, match)

                for p in players:
                    rating = compute_rating(
                        goals=p["goals"],
                        yellow_cards=p["yellow_cards"],
                        red_cards=p["red_cards"],
                        minutes=p["minutes"],
                        team_won=bool(p["team_won"]),
                        is_goalkeeper=p["role"] == "P",
                        goals_conceded=p["goals_conceded"],
                        weights=weights,
                    )
                    records.append({
                        "player_name": p["name"],
                        "role": p["role"],
                        "team": p["team"],
                        "season": season,
                        "matchday": md,
                        "rating": rating,
                        "goals": p["goals"],
                        "yellow_cards": p["yellow_cards"],
                        "red_cards": p["red_cards"],
                        "goals_conceded": p["goals_conceded"],
                        "team_won": p["team_won"],
                        "minutes": p["minutes"],
                    })

                log.info(
                    "G%d  %s %d-%d %s  (%d giocatori)",
                    md,
                    match["home_team"],
                    match["home_score"],
                    match["away_score"],
                    match["away_team"],
                    len(players),
                )
            except Exception as exc:
                log.error(
                    "Errore match %s vs %s (G%d): %s",
                    match["home_team"],
                    match["away_team"],
                    md,
                    exc,
                )

    return records


def export_csv(season: str, output_path: str, weights: RatingWeights | None = None) -> None:
    records = _collect_season(season, weights or RatingWeights())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    log.info("CSV esportato: %s (%d righe)", output_path, len(records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scraper understat.com — Serie A storica (2014-2015 in poi)"
    )
    parser.add_argument("--season", required=True, help="Stagione es. 2015-2016")
    parser.add_argument("--export-csv", metavar="FILE", required=True, help="File CSV di output")
    parser.add_argument("--weights-file", metavar="FILE", help="JSON con i pesi del rating")
    args = parser.parse_args()

    w = RatingWeights.from_json(args.weights_file) if args.weights_file else RatingWeights()
    export_csv(args.season, args.export_csv, w)
