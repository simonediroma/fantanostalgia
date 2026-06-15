"""
Scraper calcio-seriea.net — statistiche storiche Serie A.

Scarica per ogni partita: lineup, gol, cartellini, minuti giocati.
Calcola il rating sintetico per ogni giocatore che è entrato in campo.
Il sito non fornisce voti reali né ruoli: il portiere è rilevato dalla
maglia #1, tutti gli altri sono trattati come 'C' (default configurabile
con --roles-csv).

Modalità di output:
  default            scrive direttamente su SQLite (locale o GCS)
  --export-csv FILE  esporta un CSV da importare via admin panel

Usage:
    python -m backend.scrapers.calcioseriea --season 2016-2017 --export-csv out.csv
    python -m backend.scrapers.calcioseriea --season 2016-2017 --export-csv out.csv --roles-csv ruoli.csv
    python -m backend.scrapers.calcioseriea --season 2016-2017 --force
"""

import argparse
import csv
import logging
import re
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

from backend.api.db import ENV, _download_db_from_gcs, _get_db_path, _upload_db_to_gcs
from backend.engine.rating import RatingWeights, compute_rating

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE = "http://calcio-seriea.net"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Referer": "http://calcio-seriea.net/",
}

CSV_FIELDS = [
    "player_name", "role", "team", "season", "matchday",
    "rating", "goals", "yellow_cards", "red_cards", "goals_conceded",
    "team_won", "minutes",
]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


def _fetch(session: requests.Session, url: str) -> BeautifulSoup:
    time.sleep(1.5)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")


# ---------------------------------------------------------------------------
# Roles override
# ---------------------------------------------------------------------------

def _load_roles_csv(path: str) -> dict[str, str]:
    """Carica un CSV con colonne name,role per override del default 'C'."""
    roles: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("name", "").strip()
            role = row.get("role", "").strip().upper()
            if name and role in ("P", "D", "C", "A"):
                roles[name] = role
    return roles


# ---------------------------------------------------------------------------
# Parsing risultati page
# ---------------------------------------------------------------------------

def _season_to_year(season: str) -> int:
    """'2016-2017' → 2016"""
    return int(season.split("-")[0])


def _get_matchday_urls(session: requests.Session, season: str) -> list[tuple[int, str]]:
    """
    Scarica la prima giornata della stagione per estrarre tutti i link
    alle giornate regolari (skippa recuperi come '3r', '19r').
    Ritorna lista di (matchday_num, url) ordinata.
    """
    year = _season_to_year(season)
    index_url = f"{BASE}/risultati/{year}/"
    soup = _fetch(session, index_url)

    # La pagina index fa redirect alla prima giornata disponibile.
    # I link alle giornate sono in <td class="Nav3Off"> e <td class="Nav3On">.
    matchdays: list[tuple[int, str]] = []
    for td in soup.find_all("td", class_=lambda c: c and "Nav3" in c):
        a = td.find("a", class_="Nav3")
        if not a:
            continue
        label = a.get_text(strip=True)
        # Skippa recuperi (es. "3r", "19r", "12r")
        if re.match(r"^\d+r$", label):
            continue
        try:
            num = int(label)
        except ValueError:
            continue
        href = a.get("href", "")
        if href:
            matchdays.append((num, href if href.startswith("http") else BASE + href))

    # Deduplica (stessa giornata può comparire in righe diverse della nav)
    seen: set[int] = set()
    result: list[tuple[int, str]] = []
    for num, url in matchdays:
        if num not in seen:
            seen.add(num)
            result.append((num, url))

    return sorted(result, key=lambda x: x[0])


def _parse_matches(soup: BeautifulSoup) -> list[dict]:
    """
    Estrae le partite da una pagina giornata.
    Ritorna lista di dict con home, away, home_goals, away_goals, tabellino_url.
    """
    matches = []
    # Le partite sono in <tr> con <td class="TableCell"> contenenti <b>SQUADRA</b>
    for row in soup.find_all("tr"):
        tds = row.find_all("td", class_="TableCell")
        if len(tds) < 5:
            continue

        # td[1]: nomi squadre, td[2]: punteggio, td[4]: link tabellino
        teams_td = tds[1]
        score_td = tds[2]
        tab_td = tds[4]

        team_tags = teams_td.find_all("b")
        score_tags = score_td.find_all("b")
        tab_link = tab_td.find("a", href=re.compile(r"/tabellini/"))

        if len(team_tags) < 2 or len(score_tags) < 2 or not tab_link:
            continue

        try:
            home_goals = int(score_tags[0].get_text(strip=True))
            away_goals = int(score_tags[1].get_text(strip=True))
        except ValueError:
            continue

        href = tab_link.get("href", "")
        tab_url = href if href.startswith("http") else BASE + href

        matches.append({
            "home": team_tags[0].get_text(strip=True).title(),
            "away": team_tags[1].get_text(strip=True).title(),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "tabellino_url": tab_url,
        })

    return matches


# ---------------------------------------------------------------------------
# Parsing tabellino page
# ---------------------------------------------------------------------------

def _extract_minute(td) -> int | None:
    """Estrae il minuto da un td contenente es. '63'' o '&nbsp;63'' o '63'&nbsp;'."""
    text = td.get_text(strip=True).replace("\xa0", "").replace("'", "").strip()
    if text.isdigit():
        return int(text)
    # Gestisce "90+2" e "45+1"
    m = re.match(r"^(\d+)(?:\+\d+)?$", text)
    if m:
        return int(m.group(1))
    return None


def _parse_scorers(soup: BeautifulSoup, home_team: str, away_team: str) -> tuple[dict[str, int], dict[str, int]]:
    """
    Estrae i marcatori dalla sezione gol del tabellino (righe prima di TITOLARI).
    Ritorna (home_goals_by_player, away_goals_by_player) — chiavi: nome normalizzato.
    """
    home_goals: dict[str, int] = {}
    away_goals: dict[str, int] = {}

    in_scorers = False
    for row in soup.find_all("tr"):
        tds = row.find_all("td")

        # Inizia dopo il MainTitle (header partita) e finisce a TITOLARI
        if any("MainTitle" in (td.get("class") or []) for td in tds):
            in_scorers = True
            continue

        if any("SubTitle" in (td.get("class") or []) for td in tds):
            if in_scorers:
                break  # TITOLARI trovato, fine sezione gol
            continue

        if not in_scorers:
            continue

        # Riga gol: 10 td, divider in posizione 4 e 5
        border_tds = row.find_all("td", class_=lambda c: c and "TableCellBorder" in c)
        if len(border_tds) < 3:
            continue

        # Struttura: [nome_home colspan=3] [minuto] [divR] [divL] [minuto] [nome_away colspan=3]
        all_tds = row.find_all("td")
        if len(all_tds) < 8:
            continue

        # Home scorer: nome in all_tds[0] (colspan=3), minuto in all_tds[3]
        home_name = all_tds[0].get_text(strip=True)
        home_min_text = all_tds[3].get_text(strip=True)
        # Away scorer: minuto in all_tds[5], nome in all_tds[7]
        away_min_text = all_tds[5].get_text(strip=True) if len(all_tds) > 5 else ""
        away_name = all_tds[7].get_text(strip=True) if len(all_tds) > 7 else ""

        if home_name and home_name != "\xa0" and home_min_text and home_min_text != "\xa0":
            key = _normalize_name(home_name)
            home_goals[key] = home_goals.get(key, 0) + 1

        if away_name and away_name != "\xa0" and away_min_text and away_min_text != "\xa0":
            key = _normalize_name(away_name)
            away_goals[key] = away_goals.get(key, 0) + 1

    return home_goals, away_goals


def _normalize_name(raw: str) -> str:
    """Normalizza nome per lookup: uppercase, rimuove spazi extra."""
    return " ".join(raw.upper().split())


def _parse_player_rows(
    soup: BeautifulSoup,
    home_team: str,
    away_team: str,
    home_goals_map: dict[str, int],
    away_goals_map: dict[str, int],
    home_goals: int,
    away_goals: int,
    roles_override: dict[str, str],
    weights: RatingWeights,
) -> list[dict]:
    """
    Parsea le sezioni TITOLARI e A DISPOSIZIONE del tabellino.
    Ritorna lista di dict per ogni giocatore che ha giocato > 0 minuti.
    """
    home_won = home_goals > away_goals
    away_won = away_goals > home_goals

    home_players: list[dict] = []
    away_players: list[dict] = []

    section = None  # 'titolari' | 'disposizione' | None

    for row in soup.find_all("tr"):
        tds = row.find_all("td")

        # Rileva sezione
        sub_tds = [td for td in tds if "SubTitle" in (td.get("class") or [])]
        if sub_tds:
            text = sub_tds[0].get_text(strip=True).upper()
            if "TITOLARI" in text:
                section = "titolari"
            elif "DISPOSIZIONE" in text or "DISPONIBILI" in text:
                section = "disposizione"
            elif "ALLENATORE" in text:
                section = None
            continue

        if section is None:
            continue

        # Riga giocatore: deve avere almeno 10 td con la struttura attesa
        if len(tds) < 10:
            continue

        # Verifica che sia una riga dati (ha TableCellBorder)
        if not any("TableCellBorder" in (td.get("class") or []) for td in tds):
            continue

        # --- Home player (cols 0-3) ---
        home_name_td = tds[1]
        home_num_td = tds[2]
        home_sub_td = tds[3]
        home_card_td = tds[0]

        # --- Away player (cols 6-9) ---
        away_sub_td = tds[6]
        away_num_td = tds[7]
        away_name_td = tds[8]
        away_card_td = tds[9]

        for side, name_td, num_td, sub_td, card_td, team, won, gc, goals_map in [
            ("home", home_name_td, home_num_td, home_sub_td, home_card_td,
             home_team, home_won, away_goals, home_goals_map),
            ("away", away_name_td, away_num_td, away_sub_td, away_card_td,
             away_team, away_won, home_goals, away_goals_map),
        ]:
            name_link = name_td.find("a")
            if not name_link:
                continue  # riga vuota (bench padding asimmetrico)

            raw_name = name_link.get_text(strip=True)
            if not raw_name:
                continue

            shirt_text = num_td.find("b")
            shirt = shirt_text.get_text(strip=True) if shirt_text else ""

            # Ruolo: portiere da maglia 1, altrimenti override o default 'C'
            if shirt == "1":
                role = "P"
            else:
                role = roles_override.get(_normalize_name(raw_name), "C")

            # Minuti: calcola da icone uscito/entrato
            sub_imgs = sub_td.find_all("img")
            sub_minute = _extract_minute(sub_td)

            if section == "titolari":
                has_uscito = any("uscito" in (img.get("alt") or "") for img in sub_imgs)
                minutes = sub_minute if (has_uscito and sub_minute is not None) else 90
            else:  # disposizione
                has_entrato = any("entrato" in (img.get("alt") or "") for img in sub_imgs)
                if has_entrato and sub_minute is not None:
                    minutes = 90 - sub_minute
                else:
                    minutes = 0

            if minutes == 0:
                continue  # non entrato in campo

            # Cartellini
            card_imgs = card_td.find_all("img")
            yellow = sum(1 for img in card_imgs if "ammonit" in (img.get("alt") or "").lower())
            red = sum(1 for img in card_imgs if "espuls" in (img.get("alt") or "").lower())

            # Gol: lookup per nome normalizzato
            name_key = _normalize_name(raw_name)
            goals = goals_map.get(name_key, 0)

            is_gk = role == "P"
            rating = compute_rating(
                goals=goals,
                yellow_cards=yellow,
                red_cards=red,
                minutes=minutes,
                team_won=won,
                is_goalkeeper=is_gk,
                goals_conceded=gc if is_gk else 0,
                weights=weights,
            )

            record = {
                "name": raw_name,
                "role": role,
                "team": team,
                "goals": goals,
                "yellow_cards": yellow,
                "red_cards": red,
                "goals_conceded": gc if is_gk else 0,
                "team_won": int(won),
                "minutes": minutes,
                "rating": rating,
            }

            if side == "home":
                home_players.append(record)
            else:
                away_players.append(record)

    return home_players + away_players


def _scrape_tabellino(
    session: requests.Session,
    match: dict,
    season: str,
    matchday: int,
    roles_override: dict[str, str],
    weights: RatingWeights,
) -> list[dict]:
    soup = _fetch(session, match["tabellino_url"])

    home_goals_map, away_goals_map = _parse_scorers(
        soup, match["home"], match["away"]
    )

    players = _parse_player_rows(
        soup,
        home_team=match["home"],
        away_team=match["away"],
        home_goals_map=home_goals_map,
        away_goals_map=away_goals_map,
        home_goals=match["home_goals"],
        away_goals=match["away_goals"],
        roles_override=roles_override,
        weights=weights,
    )

    return [
        {
            "player_name": p["name"],
            "role": p["role"],
            "team": p["team"],
            "season": season,
            "matchday": matchday,
            "rating": p["rating"],
            "goals": p["goals"],
            "yellow_cards": p["yellow_cards"],
            "red_cards": p["red_cards"],
            "goals_conceded": p["goals_conceded"],
            "team_won": p["team_won"],
            "minutes": p["minutes"],
        }
        for p in players
    ]


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


def _save_records(conn: sqlite3.Connection, records: list[dict]) -> None:
    for r in records:
        pid = _upsert_player(conn, r["player_name"], r["role"], r["team"], r["season"])
        conn.execute(
            """
            INSERT OR IGNORE INTO historic_rating
              (player_historic_id, matchday, rating, goals, assists,
               yellow_cards, red_cards, own_goals, penalties_scored,
               penalties_missed, goals_conceded, team_won, minutes, source)
            VALUES (?, ?, ?, ?, 0, ?, ?, 0, 0, 0, ?, ?, ?, 'synthetic')
            """,
            (
                pid, r["matchday"], r["rating"], r["goals"],
                r["yellow_cards"], r["red_cards"], r["goals_conceded"],
                r["team_won"], r["minutes"],
            ),
        )


# ---------------------------------------------------------------------------
# Core scraping loop
# ---------------------------------------------------------------------------

def _collect_season(
    season: str,
    weights: RatingWeights,
    roles_override: dict[str, str],
) -> list[dict]:
    """Scrapa la stagione e ritorna tutti i record in memoria."""
    session = _build_session()
    year = _season_to_year(season)

    log.info("Carico giornate stagione %s (year=%d)...", season, year)
    matchday_urls = _get_matchday_urls(session, season)
    log.info("%d giornate trovate.", len(matchday_urls))

    records: list[dict] = []

    for matchday_num, md_url in matchday_urls:
        log.info("Scraping giornata %d...", matchday_num)
        try:
            md_soup = _fetch(session, md_url)
        except Exception as exc:
            log.error("Errore caricamento giornata %d: %s", matchday_num, exc)
            continue

        matches = _parse_matches(md_soup)
        log.info("  %d partite trovate.", len(matches))

        for match in matches:
            try:
                match_records = _scrape_tabellino(
                    session, match, season, matchday_num, roles_override, weights
                )
                records.extend(match_records)
                log.info(
                    "  G%d  %s %d-%d %s  (%d giocatori)",
                    matchday_num,
                    match["home"], match["home_goals"],
                    match["away_goals"], match["away"],
                    len(match_records),
                )
            except Exception as exc:
                log.error(
                    "  Errore tabellino %s vs %s (G%d): %s",
                    match["home"], match["away"], matchday_num, exc,
                )

    return records


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def scrape_season(
    season: str,
    *,
    force: bool = False,
    weights: RatingWeights | None = None,
    roles_override: dict[str, str] | None = None,
) -> None:
    if weights is None:
        weights = RatingWeights()
    if roles_override is None:
        roles_override = {}

    if ENV != "development":
        _download_db_from_gcs()

    conn = sqlite3.connect(_get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        if not force and _season_scraped(conn, season):
            log.info("Stagione %s già nel DB. Usa --force per riscrappare.", season)
            return

        records = _collect_season(season, weights, roles_override)
        log.info("Totale record raccolti: %d", len(records))

        for r in records:
            _save_records(conn, [r])
        conn.commit()
        log.info("Stagione %s salvata.", season)

    finally:
        conn.close()
        if ENV != "development":
            _upload_db_to_gcs()


def export_csv(
    season: str,
    output_path: str,
    weights: RatingWeights | None = None,
    roles_override: dict[str, str] | None = None,
) -> None:
    records = _collect_season(season, weights or RatingWeights(), roles_override or {})
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    log.info("CSV esportato: %s (%d righe)", output_path, len(records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper calcio-seriea.net — Serie A storica")
    parser.add_argument("--season", required=True, help="Stagione es. 2016-2017")
    parser.add_argument("--force", action="store_true", help="Riscrappa anche se già presente nel DB")
    parser.add_argument("--export-csv", metavar="FILE", help="Esporta CSV invece di scrivere su DB")
    parser.add_argument("--weights-file", metavar="FILE", help="JSON con i pesi del rating")
    parser.add_argument("--roles-csv", metavar="FILE", help="CSV con colonne name,role per override del default 'C'")
    args = parser.parse_args()

    weights = RatingWeights.from_json(args.weights_file) if args.weights_file else RatingWeights()
    roles_override = _load_roles_csv(args.roles_csv) if args.roles_csv else {}

    if args.export_csv:
        export_csv(args.season, args.export_csv, weights, roles_override)
    else:
        scrape_season(args.season, force=args.force, weights=weights, roles_override=roles_override)
