"""
Scraper calcio-seriea.net — statistiche storiche Serie A.

Scarica per ogni partita: lineup, gol, cartellini, minuti giocati.
I ruoli vengono estratti automaticamente dalle pagine rosa (/rose/{year}/).
Calcola il rating sintetico per ogni giocatore che è entrato in campo.

Modalità di output:
  default            scrive direttamente su SQLite (locale o GCS)
  --export-csv FILE  esporta un CSV da importare via admin panel

Usage:
    python -m backend.scrapers.calcioseriea --season 2016-2017 --export-csv out.csv
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

_ROLE_MAP = {
    "PORTIERI": "P",
    "DIFENSORI": "D",
    "CENTROCAMPISTI": "C",
    "ATTACCANTI": "A",
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
    log.debug("  GET %s", url)
    time.sleep(1.5)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    if resp.url != url:
        log.debug("  → redirect: %s", resp.url)
    return BeautifulSoup(resp.text, "lxml")


def _player_id_from_href(href: str) -> int | None:
    """Estrae l'ID numerico da '/scheda_giocatore/{year}/{id}/'."""
    m = re.search(r"/scheda_giocatore/\d+/(\d+)/", href)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Ruoli dalle pagine rosa
# ---------------------------------------------------------------------------

def _get_team_rose_urls(session: requests.Session, year: int) -> list[str]:
    """
    Scarica /rose/{year}/ e restituisce gli URL di tutte le squadre.
    Segue eventuali redirect (es. /rose/1999/ → /rose/1999/1633/) e cerca
    i link squadra come sotto-percorsi dell'URL finale.
    """
    index_url = f"{BASE}/rose/{year}/"

    def _fetch_rose_index() -> tuple[str, BeautifulSoup]:
        log.info("  GET rose index: %s", index_url)
        time.sleep(1.5)
        resp = session.get(index_url, timeout=30)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        if resp.url != index_url:
            log.info("  → redirect: %s", resp.url)
        return resp.url, BeautifulSoup(resp.text, "lxml")

    def _extract_urls(final_url: str, soup: BeautifulSoup) -> list[str]:
        # Estrai l'anno dall'URL finale (può essere diverso da `year` se c'è redirect).
        # I link squadra sono FRATELLI dell'URL finale, non figli:
        #   final_url = /rose/1999/1163/  →  pattern = /rose/1999/\d+/
        m = re.search(r"/rose/(\d+)/", final_url)
        actual_year = m.group(1) if m else str(year)
        pattern = re.compile(rf"/rose/{actual_year}/\d+/")
        found: list[str] = []
        for a in soup.find_all("a", href=pattern):
            href = a.get("href", "")
            url = href if href.startswith("http") else BASE + href
            if url not in found:
                found.append(url)
        return found

    final_url, soup = _fetch_rose_index()
    urls = _extract_urls(final_url, soup)

    if not urls:
        # Prima risposta vuota (cookie gate): il server ha impostato la sessione.
        # Riprova: questa volta dovrebbe arrivare il 302 con la pagina corretta.
        log.info("  Pagina rose vuota (cookie gate), retry...")
        final_url, soup = _fetch_rose_index()
        urls = _extract_urls(final_url, soup)

    log.info("  %d URL squadre trovate.", len(urls))
    for u in urls:
        log.info("    %s", u)
    return urls


def _scrape_rose(session: requests.Session, url: str) -> dict[int, str]:
    """
    Scarica la pagina rosa di una squadra e restituisce {player_id: role}.
    Ruoli da sezioni SubTitle: PORTIERI/DIFENSORI/CENTROCAMPISTI/ATTACCANTI.
    """
    log.info("    GET rosa squadra: %s", url)
    soup = _fetch(session, url)
    roles: dict[int, str] = {}
    current_role = "C"  # fallback

    for row in soup.find_all("tr"):
        # Rileva cambio sezione
        sub = row.find("td", class_="SubTitle")
        if sub:
            text = sub.get_text(strip=True).upper()
            for key, role in _ROLE_MAP.items():
                if key in text:
                    current_role = role
                    break
            continue

        # Riga giocatore: cerca link scheda_giocatore
        for a in row.find_all("a", href=re.compile(r"/scheda_giocatore/")):
            pid = _player_id_from_href(a.get("href", ""))
            if pid is not None:
                roles[pid] = current_role

    log.info("      → %d giocatori con ruolo estratti.", len(roles))
    return roles


def _get_roles_map(session: requests.Session, season: str) -> dict[int, str]:
    """
    Scarica le rose di tutte le squadre e restituisce {player_id: role}.
    """
    year = _season_to_year(season)
    log.info("Carico ruoli dalle pagine rosa (anno %d)...", year)
    team_urls = _get_team_rose_urls(session, year)
    log.info("  %d squadre trovate.", len(team_urls))

    roles: dict[int, str] = {}
    for url in team_urls:
        try:
            team_roles = _scrape_rose(session, url)
            roles.update(team_roles)
        except Exception as exc:
            log.warning("  Errore rosa %s: %s", url, exc)

    log.info("  %d giocatori con ruolo.", len(roles))
    return roles


# ---------------------------------------------------------------------------
# Parsing risultati page
# ---------------------------------------------------------------------------

def _season_to_year(season: str) -> int:
    """'2016-2017' → 2016"""
    return int(season.split("-")[0])


def _get_matchday_urls(session: requests.Session, season: str) -> list[tuple[int, str]]:
    """
    Scarica /risultati/{year}/ per estrarre i link a tutte le giornate regolari
    (skippa recuperi come '3r', '19r').
    Ritorna lista di (matchday_num, url) ordinata.
    """
    year = _season_to_year(season)
    soup = _fetch(session, f"{BASE}/risultati/{year}/")

    matchdays: list[tuple[int, str]] = []
    seen: set[int] = set()
    for td in soup.find_all("td", class_=lambda c: c and "Nav3" in c):
        a = td.find("a", class_="Nav3")
        if not a:
            continue
        label = a.get_text(strip=True)
        if re.match(r"^\d+r$", label):
            continue  # recupero
        try:
            num = int(label)
        except ValueError:
            continue
        if num in seen:
            continue
        seen.add(num)
        href = a.get("href", "")
        url = href if href.startswith("http") else BASE + href
        matchdays.append((num, url))

    return sorted(matchdays, key=lambda x: x[0])


def _parse_matches(soup: BeautifulSoup) -> list[dict]:
    """
    Estrae le partite da una pagina giornata.
    Ritorna lista di dict con home, away, home_goals, away_goals, tabellino_url.
    """
    matches = []
    for row in soup.find_all("tr"):
        tds = row.find_all("td", class_="TableCell")
        if len(tds) < 5:
            continue

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
    """Estrae il minuto da un td contenente es. '63'' o '90+2''."""
    text = td.get_text(strip=True).replace("\xa0", "").replace("'", "").strip()
    m = re.match(r"^(\d+)(?:\+\d+)?$", text)
    return int(m.group(1)) if m else None


def _parse_scorers(soup: BeautifulSoup) -> tuple[dict[int, int], dict[int, int]]:
    """
    Estrae i marcatori dalla sezione gol del tabellino.
    Usa player_id come chiave (da link scheda_giocatore nei TITOLARI).
    Fallback: ritorna dict vuoti — i gol verranno assegnati 0.

    Nota: la sezione marcatori usa nomi testuali, non link. Per abbinare
    i gol ai giocatori usiamo i nomi nei tabellini come fallback (non affidabile
    per nomi composti). Metodo più robusto: contare i gol dalla sezione testo
    e assegnarli per nome normalizzato, poi risolvere via player_id nel parsing
    righe giocatore.
    Ritorna (home_goals_by_name, away_goals_by_name) — chiavi: nome uppercase strip.
    """
    home_goals: dict[str, int] = {}
    away_goals: dict[str, int] = {}

    in_scorers = False
    for row in soup.find_all("tr"):
        tds = row.find_all("td")

        if any("MainTitle" in (td.get("class") or []) for td in tds):
            in_scorers = True
            continue

        if any("SubTitle" in (td.get("class") or []) for td in tds):
            if in_scorers:
                break
            continue

        if not in_scorers:
            continue

        all_tds = row.find_all("td")
        if len(all_tds) < 8:
            continue

        # Verifica che sia una riga marcatori (ha TableCellBorder)
        if not any("TableCellBorder" in (td.get("class") or []) for td in all_tds):
            continue

        home_name = all_tds[0].get_text(strip=True).replace("\xa0", "").strip()
        home_min = all_tds[3].get_text(strip=True).replace("\xa0", "").strip()
        away_min = all_tds[5].get_text(strip=True).replace("\xa0", "").strip() if len(all_tds) > 5 else ""
        away_name = all_tds[7].get_text(strip=True).replace("\xa0", "").strip() if len(all_tds) > 7 else ""

        if home_name and home_min and home_min not in ("", "&nbsp;"):
            key = home_name.upper()
            home_goals[key] = home_goals.get(key, 0) + 1

        if away_name and away_min and away_min not in ("", "&nbsp;"):
            key = away_name.upper()
            away_goals[key] = away_goals.get(key, 0) + 1

    return home_goals, away_goals


def _parse_player_rows(
    soup: BeautifulSoup,
    home_team: str,
    away_team: str,
    home_goals_map: dict[str, int],
    away_goals_map: dict[str, int],
    home_goals: int,
    away_goals: int,
    roles_map: dict[int, str],
    weights: RatingWeights,
) -> list[dict]:
    """
    Parsea TITOLARI e A DISPOSIZIONE. Ritorna un record per ogni giocatore
    che ha giocato > 0 minuti.
    """
    home_won = home_goals > away_goals
    away_won = away_goals > home_goals

    home_players: list[dict] = []
    away_players: list[dict] = []

    section = None  # 'titolari' | 'disposizione' | None

    for row in soup.find_all("tr"):
        tds = row.find_all("td")

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
        if len(tds) < 10:
            continue
        if not any("TableCellBorder" in (td.get("class") or []) for td in tds):
            continue

        for side, name_td, sub_td, card_td, team, won, gc, goals_map in [
            ("home", tds[1], tds[3], tds[0],
             home_team, home_won, away_goals, home_goals_map),
            ("away", tds[8], tds[6], tds[9],
             away_team, away_won, home_goals, away_goals_map),
        ]:
            name_link = name_td.find("a")
            if not name_link:
                continue

            raw_name = name_link.get_text(strip=True)
            if not raw_name:
                continue

            # Ruolo da roles_map via player_id
            pid = _player_id_from_href(name_link.get("href", ""))
            role = roles_map.get(pid, "C") if pid is not None else "C"

            # Minuti da icone uscito/entrato
            sub_imgs = sub_td.find_all("img")
            sub_minute = _extract_minute(sub_td)

            if section == "titolari":
                has_uscito = any("uscito" in (img.get("alt") or "") for img in sub_imgs)
                minutes = sub_minute if (has_uscito and sub_minute is not None) else 90
            else:
                has_entrato = any("entrato" in (img.get("alt") or "") for img in sub_imgs)
                minutes = (90 - sub_minute) if (has_entrato and sub_minute is not None) else 0

            if minutes == 0:
                continue

            # Cartellini
            card_imgs = card_td.find_all("img")
            yellow = sum(1 for img in card_imgs if "ammonit" in (img.get("alt") or "").lower())
            red = sum(1 for img in card_imgs if "espuls" in (img.get("alt") or "").lower())

            # Gol per nome normalizzato
            name_key = raw_name.upper()
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
    roles_map: dict[int, str],
    weights: RatingWeights,
) -> list[dict]:
    soup = _fetch(session, match["tabellino_url"])

    home_goals_map, away_goals_map = _parse_scorers(soup)

    players = _parse_player_rows(
        soup,
        home_team=match["home"],
        away_team=match["away"],
        home_goals_map=home_goals_map,
        away_goals_map=away_goals_map,
        home_goals=match["home_goals"],
        away_goals=match["away_goals"],
        roles_map=roles_map,
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
) -> list[dict]:
    """Scrapa la stagione e ritorna tutti i record in memoria."""
    session = _build_session()

    # 1. Pre-scraping ruoli dalle rose
    roles_map = _get_roles_map(session, season)

    # 2. Lista giornate
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
                log.info(
                    "  Tabellino: %s vs %s → %s",
                    match["home"], match["away"], match["tabellino_url"],
                )
                match_records = _scrape_tabellino(
                    session, match, season, matchday_num, roles_map, weights
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
) -> None:
    if weights is None:
        weights = RatingWeights()

    if ENV != "development":
        _download_db_from_gcs()

    conn = sqlite3.connect(_get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        if not force and _season_scraped(conn, season):
            log.info("Stagione %s già nel DB. Usa --force per riscrappare.", season)
            return

        records = _collect_season(season, weights)
        log.info("Totale record raccolti: %d", len(records))

        _save_records(conn, records)
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
) -> None:
    records = _collect_season(season, weights or RatingWeights())
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
    args = parser.parse_args()

    weights = RatingWeights.from_json(args.weights_file) if args.weights_file else RatingWeights()

    if args.export_csv:
        export_csv(args.season, args.export_csv, weights)
    else:
        scrape_season(args.season, force=args.force, weights=weights)
