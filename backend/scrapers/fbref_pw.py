"""
Scraper fbref.com con Playwright — bypassa Cloudflare usando un browser reale.

Usa Chrome/Chromium headful con patch anti-detection. Richiede installazione
del browser una sola volta:

    pip install playwright
    playwright install chromium

Usage:
    python -m backend.scrapers.fbref_pw --season 2015-2016 --export-csv out.csv
    python -m backend.scrapers.fbref_pw --season 2005-2006 --export-csv out.csv --weights-file pesi.json
    python -m backend.scrapers.fbref_pw --season 2015-2016 --export-csv out.csv --headless
"""

import argparse
import csv
import logging
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from backend.engine.rating import RatingWeights, compute_rating
from backend.scrapers.fbref import CSV_FIELDS

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

# Script iniettato in ogni pagina per nascondere l'automazione
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
window.chrome = {runtime: {}};
"""


# ---------------------------------------------------------------------------
# Browser session
# ---------------------------------------------------------------------------

class _BrowserSession:
    """Mantiene il browser aperto per tutta la sessione di scraping."""

    def __init__(self, headless: bool = False):
        self._pw = sync_playwright().start()
        # Prova prima Chrome installato sul sistema (fingerprint più realistico),
        # poi fallback a Chromium scaricato da playwright
        try:
            self._browser = self._pw.chromium.launch(
                channel="chrome", headless=headless
            )
            log.info("Browser: Chrome")
        except Exception:
            self._browser = self._pw.chromium.launch(headless=headless)
            log.info("Browser: Chromium")

        self._ctx = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Rome",
        )
        self._ctx.add_init_script(_STEALTH_SCRIPT)

    def fetch(self, url: str, wait_ms: int = 3000) -> BeautifulSoup:
        page = self._ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60_000)
            # Attesa extra per il challenge Cloudflare (se presente)
            page.wait_for_timeout(wait_ms)
            html = page.content()
            return BeautifulSoup(html, "lxml")
        finally:
            page.close()

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()


# ---------------------------------------------------------------------------
# Parsing (identico a fbref.py, indipendente dalla sessione HTTP)
# ---------------------------------------------------------------------------

def _int_cell(cell) -> int:
    if not cell:
        return 0
    t = cell.get_text(strip=True)
    return int(t) if t.isdigit() else 0


def _map_position(pos_raw: str) -> str:
    primary = pos_raw.split(",")[0].strip()
    return _POSITION_MAP.get(primary, "C")


def _get_fixtures(session: _BrowserSession, season: str) -> list[dict]:
    url = (
        f"{FBREF_BASE}/en/comps/{COMP_ID}/{season}/schedule"
        f"/{season}-Serie-A-Scores-and-Fixtures"
    )
    log.info("Carico fixtures: %s", url)
    soup = session.fetch(url)

    table = soup.find("table", id=lambda x: x and "sched" in x)
    if not table:
        raise ValueError(f"Tabella fixtures non trovata per {season}")

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

        score_text = (
            score_cell.get_text(strip=True)
            .replace("–", "-")
            .replace("−", "-")
        )
        if "-" not in score_text:
            continue

        try:
            home_score, away_score = map(int, score_text.split("-", 1))
            matchday = int(wk.get_text(strip=True))
        except ValueError:
            continue

        report_link = score_cell.find("a")
        if not report_link:
            continue

        fixtures.append({
            "matchday": matchday,
            "home_team": home.get_text(strip=True),
            "away_team": away.get_text(strip=True),
            "home_score": home_score,
            "away_score": away_score,
            "report_url": FBREF_BASE + report_link["href"],
        })

    return fixtures


def _parse_team_stats(
    soup: BeautifulSoup,
    *,
    team_name: str,
    table_index: int,
    goals_conceded: int,
    team_won: bool,
    weights: RatingWeights,
) -> list[dict]:
    summary_tables = soup.find_all(
        "table",
        id=lambda x: x and x.startswith("stats_") and x.endswith("_summary"),
    )
    if len(summary_tables) <= table_index:
        return []

    players = []
    for row in summary_tables[table_index].find("tbody").find_all("tr"):
        if any(c in row.get("class", []) for c in ("thead", "spacer")):
            continue

        name_cell = row.find(attrs={"data-stat": "player"})
        if not name_cell:
            continue

        minutes = _int_cell(row.find(attrs={"data-stat": "minutes"}))
        if minutes == 0:
            continue

        pos_raw = ""
        pos_cell = row.find(attrs={"data-stat": "position"})
        if pos_cell:
            pos_raw = pos_cell.get_text(strip=True)

        role = _map_position(pos_raw)
        is_gk = role == "P"
        goals = _int_cell(row.find(attrs={"data-stat": "goals"}))
        yellow = _int_cell(row.find(attrs={"data-stat": "cards_yellow"}))
        red = _int_cell(row.find(attrs={"data-stat": "cards_red"}))
        gc = goals_conceded if is_gk else 0

        rating = compute_rating(
            goals=goals,
            yellow_cards=yellow,
            red_cards=red,
            minutes=minutes,
            team_won=team_won,
            is_goalkeeper=is_gk,
            goals_conceded=gc,
            weights=weights,
        )

        players.append({
            "name": name_cell.get_text(strip=True),
            "role": role,
            "team": team_name,
            "goals": goals,
            "yellow_cards": yellow,
            "red_cards": red,
            "goals_conceded": gc,
            "team_won": int(team_won),
            "minutes": minutes,
            "rating": rating,
        })

    return players


def _scrape_match(
    session: _BrowserSession, fixture: dict, weights: RatingWeights
) -> list[dict]:
    soup = session.fetch(fixture["report_url"])
    home_score, away_score = fixture["home_score"], fixture["away_score"]

    home = _parse_team_stats(
        soup,
        team_name=fixture["home_team"],
        table_index=0,
        goals_conceded=away_score,
        team_won=home_score > away_score,
        weights=weights,
    )
    away = _parse_team_stats(
        soup,
        team_name=fixture["away_team"],
        table_index=1,
        goals_conceded=home_score,
        team_won=away_score > home_score,
        weights=weights,
    )
    return home + away


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _collect_season(season: str, weights: RatingWeights, headless: bool) -> list[dict]:
    session = _BrowserSession(headless=headless)
    records: list[dict] = []

    try:
        fixtures = _get_fixtures(session, season)
        log.info("%d partite trovate.", len(fixtures))

        for md in sorted({f["matchday"] for f in fixtures}):
            for fix in [f for f in fixtures if f["matchday"] == md]:
                try:
                    players = _scrape_match(session, fix, weights)
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
                        md,
                        fix["home_team"],
                        fix["home_score"],
                        fix["away_score"],
                        fix["away_team"],
                        len(players),
                    )
                except Exception as exc:
                    log.error(
                        "Errore %s vs %s G%d: %s",
                        fix["home_team"],
                        fix["away_team"],
                        md,
                        exc,
                    )
    finally:
        session.close()

    return records


def export_csv(
    season: str,
    output_path: str,
    weights: RatingWeights | None = None,
    headless: bool = False,
) -> None:
    records = _collect_season(season, weights or RatingWeights(), headless)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    log.info("CSV esportato: %s (%d righe)", output_path, len(records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scraper fbref.com con Playwright (bypassa Cloudflare)"
    )
    parser.add_argument("--season", required=True, help="Stagione es. 2005-2006")
    parser.add_argument("--export-csv", metavar="FILE", required=True, help="File CSV di output")
    parser.add_argument("--weights-file", metavar="FILE", help="JSON pesi rating")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Esegui browser in background (meno efficace contro Cloudflare)",
    )
    args = parser.parse_args()

    w = RatingWeights.from_json(args.weights_file) if args.weights_file else RatingWeights()
    export_csv(args.season, args.export_csv, w, headless=args.headless)
