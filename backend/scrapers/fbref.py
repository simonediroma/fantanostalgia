"""
Scraper fbref.com — statistiche storiche Serie A.

Scarica per ogni partita: lineup, gol, cartellini, minuti giocati.
Calcola il rating per ogni giocatore che è entrato in campo.

Modalità di output:
  default            scrive direttamente su SQLite (locale o GCS)
  --export-csv FILE  esporta un CSV da importare via admin panel

Usage:
    python -m backend.scrapers.fbref --season 2023-2024
    python -m backend.scrapers.fbref --season 2023-2024 --export-csv fbref_2023-2024.csv
    python -m backend.scrapers.fbref --season 1998-1999 --force
"""

import argparse
import csv
import logging
import sqlite3
import time

import cloudscraper
from bs4 import BeautifulSoup

from backend.api.db import ENV, _download_db_from_gcs, _get_db_path, _upload_db_to_gcs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FBREF_BASE = "https://fbref.com"
COMP_ID = "11"  # Serie A

_POSITION_MAP = {
    "GK": "P",
    "DF": "D",
    "MF": "C",
    "FW": "A",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Referer": "https://fbref.com/",
}


# ---------------------------------------------------------------------------
# Rating algorithm
# ---------------------------------------------------------------------------

def _compute_rating(
    *,
    goals: int,
    yellow_cards: int,
    red_cards: int,
    minutes: int,
    team_won: bool,
    is_goalkeeper: bool,
    goals_conceded: int,
) -> float:
    rating = 6.0
    if team_won:
        rating += 0.5
    rating += 3.0 * goals
    if is_goalkeeper:
        if goals_conceded == 0:
            rating += 1.0
        rating -= 1.0 * goals_conceded
    if minutes > 80:
        rating += 0.5
    if minutes < 30:
        rating -= 0.5
    rating -= 0.5 * yellow_cards
    rating -= 1.0 * red_cards
    return round(rating, 1)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _build_session() -> cloudscraper.CloudScraper:
    s = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows"})
    s.headers.update(_HEADERS)
    return s


def _fetch(session: cloudscraper.CloudScraper, url: str) -> BeautifulSoup:
    time.sleep(3)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _int_cell(cell) -> int:
    if not cell:
        return 0
    t = cell.get_text(strip=True)
    return int(t) if t.isdigit() else 0


def _map_position(pos_raw: str) -> str:
    primary = pos_raw.split(",")[0].strip()
    return _POSITION_MAP.get(primary, "C")


def _get_fixtures(session: cloudscraper.CloudScraper, season: str) -> list[dict]:
    url = (
        f"{FBREF_BASE}/en/comps/{COMP_ID}/{season}/schedule"
        f"/{season}-Serie-A-Scores-and-Fixtures"
    )
    soup = _fetch(session, url)

    table = soup.find("table", id=lambda x: x and "sched" in x)
    if not table:
        raise ValueError(f"Tabella fixtures non trovata per stagione {season}")

    fixtures = []
    for row in table.find("tbody").find_all("tr", recursive=False):
        classes = row.get("class", [])
        if "spacer" in classes or "thead" in classes:
            continue

        wk = row.find(attrs={"data-stat": "week_num"})
        home = row.find(attrs={"data-stat": "home_team"})
        away = row.find(attrs={"data-stat": "away_team"})
        score_cell = row.find(attrs={"data-stat": "score"})

        if not all([wk, home, away, score_cell]):
            continue

        # gestisce vari tipi di trattino (unicode em-dash, minus, hyphen)
        score_text = (
            score_cell.get_text(strip=True)
            .replace("–", "-")
            .replace("−", "-")
        )
        if "-" not in score_text:
            continue  # partita non ancora giocata

        try:
            home_score, away_score = map(int, score_text.split("-", 1))
        except ValueError:
            continue

        report_link = score_cell.find("a")
        if not report_link:
            continue

        try:
            matchday = int(wk.get_text(strip=True))
        except ValueError:
            continue

        fixtures.append(
            {
                "matchday": matchday,
                "home_team": home.get_text(strip=True),
                "away_team": away.get_text(strip=True),
                "home_score": home_score,
                "away_score": away_score,
                "report_url": FBREF_BASE + report_link["href"],
            }
        )

    return fixtures


def _parse_team_stats(
    soup: BeautifulSoup,
    *,
    team_name: str,
    table_index: int,
    goals_conceded: int,
    team_won: bool,
) -> list[dict]:
    """
    Estrae le stats dei giocatori da una delle due tabelle summary del match report.
    table_index 0 = casa, 1 = trasferta.
    """
    summary_tables = soup.find_all(
        "table",
        id=lambda x: x and x.startswith("stats_") and x.endswith("_summary"),
    )
    if len(summary_tables) <= table_index:
        return []

    table = summary_tables[table_index]
    players = []

    for row in table.find("tbody").find_all("tr"):
        classes = row.get("class", [])
        if "thead" in classes or "spacer" in classes:
            continue

        name_cell = row.find(attrs={"data-stat": "player"})
        if not name_cell:
            continue

        minutes = _int_cell(row.find(attrs={"data-stat": "minutes"}))
        if minutes == 0:
            continue  # non entrato in campo — nessun voto

        pos_raw = ""
        pos_cell = row.find(attrs={"data-stat": "position"})
        if pos_cell:
            pos_raw = pos_cell.get_text(strip=True)

        role = _map_position(pos_raw)
        is_gk = role == "P"
        goals = _int_cell(row.find(attrs={"data-stat": "goals"}))
        yellow = _int_cell(row.find(attrs={"data-stat": "cards_yellow"}))
        red = _int_cell(row.find(attrs={"data-stat": "cards_red"}))

        rating = _compute_rating(
            goals=goals,
            yellow_cards=yellow,
            red_cards=red,
            minutes=minutes,
            team_won=team_won,
            is_goalkeeper=is_gk,
            goals_conceded=goals_conceded if is_gk else 0,
        )

        players.append(
            {
                "name": name_cell.get_text(strip=True),
                "role": role,
                "team": team_name,
                "goals": goals,
                "yellow_cards": yellow,
                "red_cards": red,
                "goals_conceded": goals_conceded if is_gk else 0,
                "team_won": int(team_won),
                "minutes": minutes,
                "rating": rating,
            }
        )

    return players


def _scrape_match(session: cloudscraper.CloudScraper, fixture: dict) -> list[dict]:
    soup = _fetch(session, fixture["report_url"])

    home_score = fixture["home_score"]
    away_score = fixture["away_score"]

    home_players = _parse_team_stats(
        soup,
        team_name=fixture["home_team"],
        table_index=0,
        goals_conceded=away_score,
        team_won=home_score > away_score,
    )
    away_players = _parse_team_stats(
        soup,
        team_name=fixture["away_team"],
        table_index=1,
        goals_conceded=home_score,
        team_won=away_score > home_score,
    )

    return home_players + away_players


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def _season_scraped(conn: sqlite3.Connection, season: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM player_historic WHERE season = ? AND source = 'synthetic'",
        (season,),
    ).fetchone()
    return row[0] > 0


def _upsert_player(conn: sqlite3.Connection, name: str, role: str, team: str, season: str) -> int:
    row = conn.execute(
        "SELECT id FROM player_historic WHERE name = ? AND team = ? AND season = ?",
        (name, team, season),
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, ?, ?, ?, 'synthetic')",
        (name, role, team, season),
    )
    return cur.lastrowid


def _save_matchday(
    conn: sqlite3.Connection,
    season: str,
    matchday: int,
    players: list[dict],
) -> None:
    for p in players:
        pid = _upsert_player(conn, p["name"], p["role"], p["team"], season)
        conn.execute(
            """
            INSERT OR IGNORE INTO historic_rating
              (player_historic_id, matchday, rating, goals, assists,
               yellow_cards, red_cards, own_goals, penalties_scored,
               penalties_missed, goals_conceded, team_won, minutes, source)
            VALUES (?, ?, ?, ?, 0, ?, ?, 0, 0, 0, ?, ?, ?, 'synthetic')
            """,
            (
                pid, matchday, p["rating"], p["goals"],
                p["yellow_cards"], p["red_cards"], p["goals_conceded"],
                p["team_won"], p["minutes"],
            ),
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def scrape_season(season: str, *, force: bool = False) -> None:
    """
    Scarica e salva tutte le statistiche della stagione Serie A indicata.
    season formato: '2023-2024'
    """
    # Download GCS una sola volta all'inizio (no-op in development)
    if ENV != "development":
        _download_db_from_gcs()

    conn = sqlite3.connect(_get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        if not force and _season_scraped(conn, season):
            log.info("Stagione %s già nel DB. Usa --force per riscrappare.", season)
            return

        session = _build_session()
        log.info("Carico fixtures stagione %s...", season)
        fixtures = _get_fixtures(session, season)
        log.info("%d partite trovate.", len(fixtures))

        matchdays = sorted({f["matchday"] for f in fixtures})

        for md in matchdays:
            md_fixtures = [f for f in fixtures if f["matchday"] == md]
            all_players: list[dict] = []

            for fix in md_fixtures:
                try:
                    players = _scrape_match(session, fix)
                    all_players.extend(players)
                    log.info(
                        "G%d  %s %d-%d %s  (%d giocatori)",
                        md,
                        fix["home_team"],
                        fix["home_score"],
                        fix["away_score"],
                        fix["away_team"],
                        len(players),
                    )
                except Exception as exc:
                    log.error(
                        "Errore match %s vs %s (G%d): %s",
                        fix["home_team"],
                        fix["away_team"],
                        md,
                        exc,
                    )

            _save_matchday(conn, season, md, all_players)
            conn.commit()
            log.info("Giornata %d salvata — %d giocatori totali.", md, len(all_players))

    finally:
        conn.close()
        if ENV != "development":
            _upload_db_to_gcs()


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "player_name", "role", "team", "season", "matchday",
    "rating", "goals", "yellow_cards", "red_cards", "goals_conceded",
    "team_won", "minutes",
]


def _collect_season(season: str) -> list[dict]:
    """Scrapa la stagione e restituisce tutti i record in memoria (senza toccare il DB)."""
    session = _build_session()
    log.info("Carico fixtures stagione %s...", season)
    fixtures = _get_fixtures(session, season)
    log.info("%d partite trovate.", len(fixtures))

    records: list[dict] = []
    matchdays = sorted({f["matchday"] for f in fixtures})

    for md in matchdays:
        for fix in [f for f in fixtures if f["matchday"] == md]:
            try:
                players = _scrape_match(session, fix)
                for p in players:
                    records.append({
                        "player_name": p["name"],
                        "role": p["role"],
                        "team": p["team"],
                        "season": season,
                        "matchday": md,
                        "rating": p["rating"],
                        "goals": p["goals"],
                        "yellow_cards": p["yellow_cards"],
                        "red_cards": p["red_cards"],
                        "goals_conceded": p["goals_conceded"],
                        "team_won": p["team_won"],
                        "minutes": p["minutes"],
                    })
                log.info(
                    "G%d  %s %d-%d %s  (%d giocatori)",
                    md, fix["home_team"], fix["home_score"],
                    fix["away_score"], fix["away_team"], len(players),
                )
            except Exception as exc:
                log.error(
                    "Errore match %s vs %s (G%d): %s",
                    fix["home_team"], fix["away_team"], md, exc,
                )

    return records


def export_csv(season: str, output_path: str) -> None:
    """Scrapa la stagione e scrive un CSV pronto per l'import via admin panel."""
    records = _collect_season(season)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    log.info("CSV esportato: %s (%d righe)", output_path, len(records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper fbref.com — Serie A storica")
    parser.add_argument("--season", required=True, help="Stagione es. 2023-2024")
    parser.add_argument("--force", action="store_true", help="Riscrappa anche se già presente")
    parser.add_argument("--export-csv", metavar="FILE", help="Esporta CSV invece di scrivere su DB")
    args = parser.parse_args()

    if args.export_csv:
        export_csv(args.season, args.export_csv)
    else:
        scrape_season(args.season, force=args.force)
