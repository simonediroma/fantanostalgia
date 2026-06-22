#!/usr/bin/env python3
"""
Strumento CLI per interrogare le API /inspect/ di FantaNostalgia.

Uso rapido:
    python scripts/inspect_db.py seasons
    python scripts/inspect_db.py season 2016-17
    python scripts/inspect_db.py players 2016-17 --role A --team Juve
    python scripts/inspect_db.py matchday 2016-17 10
    python scripts/inspect_db.py player 42
    python scripts/inspect_db.py search Dybala
    python scripts/inspect_db.py teams 2016-17

Variabili d'ambiente:
    BASE_URL   URL base del server (default: http://localhost:8000)
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _get(path: str, params: dict | None = None) -> dict:
    url = BASE_URL.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        print(f"[ERRORE {e.code}] {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[CONNESSIONE FALLITA] {url}\n{e.reason}", file=sys.stderr)
        print("Assicurati che il server sia attivo (uvicorn backend.api.main:app)", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Formattazione output
# ---------------------------------------------------------------------------

def _table(rows: list[dict], columns: list[str] | None = None) -> None:
    if not rows:
        print("  (nessun risultato)")
        return
    cols = columns or list(rows[0].keys())
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = "  " + "  ".join(str(c).ljust(widths[c]) for c in cols)
    sep    = "  " + "  ".join("-" * widths[c] for c in cols)
    print(header)
    print(sep)
    for r in rows:
        print("  " + "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ---------------------------------------------------------------------------
# Comandi
# ---------------------------------------------------------------------------

def cmd_seasons(_args) -> None:
    """Elenca tutte le stagioni con statistiche di copertura."""
    data = _get("/inspect/seasons")
    if not data:
        print("Nessuna stagione nel DB.")
        return
    _section("Stagioni nel DB")
    _table(data, ["season", "source", "players", "teams", "matchdays_covered", "first_matchday", "last_matchday", "total_ratings"])


def cmd_season(args) -> None:
    """Riepilogo di una stagione."""
    data = _get(f"/inspect/seasons/{args.season}")

    _section(f"Stagione {data['season']} — distribuzione ruoli")
    _table(data["by_role"])

    _section(f"Stagione {data['season']} — squadre ({len(data['by_team'])} totali)")
    _table(data["by_team"])

    _section(f"Stagione {data['season']} — copertura giornate")
    _table(data["matchday_coverage"])

    _section(f"Stagione {data['season']} — fonti dati")
    _table(data["sources"])


def cmd_players(args) -> None:
    """Lista giocatori di una stagione con filtri."""
    params = {
        "role": args.role,
        "team": args.team,
        "name": args.name,
        "limit": args.limit,
        "offset": args.offset,
    }
    data = _get(f"/inspect/seasons/{args.season}/players", params)
    _section(f"Giocatori stagione {data['season']} — {data['total']} totali (offset={data['offset']})")
    _table(
        data["players"],
        ["id", "name", "role", "team", "source", "matchdays_played", "avg_rating", "total_goals", "total_assists"],
    )
    if data["total"] > data["offset"] + data["limit"]:
        remaining = data["total"] - data["offset"] - data["limit"]
        print(f"\n  ... altri {remaining} giocatori. Usa --offset {data['offset'] + data['limit']} per la pagina successiva.")


def cmd_player(args) -> None:
    """Dettaglio voti giornata per giornata di un singolo giocatore."""
    data = _get(f"/inspect/players/{args.player_id}")
    p = data["player"]
    s = data["stats"]

    _section(f"Giocatore: {p['name']}  ({p['role']}) — {p['team']} — {p['season']}")
    print(f"  fonte: {p['source']}  |  id: {p['id']}")
    print()
    print(f"  Giornate giocate : {s['matchdays_played']}")
    print(f"  Media voto       : {s['avg_rating']}")
    print(f"  Gol totali       : {s['total_goals']}")
    print(f"  Assist totali    : {s['total_assists']}")
    print(f"  Gialli           : {s['total_yellow']}")
    print(f"  Rossi            : {s['total_red']}")
    print(f"  Minuti           : {s['total_minutes']}")

    _section("Voti giornata per giornata")
    _table(
        data["ratings"],
        ["matchday", "rating", "goals", "assists", "yellow_cards", "red_cards", "goals_conceded", "team_won", "minutes"],
    )


def cmd_matchday(args) -> None:
    """Voti di una singola giornata."""
    params = {
        "role": args.role,
        "team": args.team,
        "min_rating": args.min_rating,
    }
    data = _get(f"/inspect/seasons/{args.season}/matchday/{args.matchday}", params)

    _section(f"Stagione {data['season']} — Giornata {data['matchday']}  ({data['players']} giocatori, media {data['avg_rating']})")
    _table(
        data["ratings"],
        ["name", "role", "team", "rating", "goals", "assists", "yellow_cards", "red_cards", "goals_conceded", "team_won", "minutes"],
    )


def cmd_teams(args) -> None:
    """Squadre presenti in una stagione."""
    data = _get(f"/inspect/seasons/{args.season}/teams")
    _section(f"Stagione {data['season']} — squadre reali")
    _table(data["teams"])


def cmd_search(args) -> None:
    """Cerca giocatori per nome."""
    params = {"name": args.name, "season": args.season}
    data = _get("/inspect/search", params)

    _section(f"Ricerca '{data['query']}' — {len(data['results'])} risultati")
    _table(
        data["results"],
        ["id", "name", "role", "team", "season", "source", "matchdays_played", "avg_rating", "total_goals", "min_rating", "max_rating"],
    )
    if data["results"]:
        print("\n  Usa `player <id>` per vedere il dettaglio completo.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Interroga le API /inspect/ di FantaNostalgia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
esempi:
  python scripts/inspect_db.py seasons
  python scripts/inspect_db.py season 2016-17
  python scripts/inspect_db.py players 2016-17 --role A --team Juve
  python scripts/inspect_db.py players 2016-17 --name Dybala
  python scripts/inspect_db.py matchday 2016-17 10
  python scripts/inspect_db.py matchday 2016-17 10 --role P
  python scripts/inspect_db.py matchday 2016-17 10 --min-rating 7
  python scripts/inspect_db.py player 42
  python scripts/inspect_db.py search Totti
  python scripts/inspect_db.py search Dybala --season 2016-17
  python scripts/inspect_db.py teams 2016-17

variabili d'ambiente:
  BASE_URL   (default: http://localhost:8000)
        """,
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("seasons", help="Lista tutte le stagioni nel DB")

    s = sub.add_parser("season", help="Riepilogo di una stagione")
    s.add_argument("season", help="Stagione in formato YYYY-YY (es. 2016-17)")

    pl = sub.add_parser("players", help="Lista giocatori di una stagione")
    pl.add_argument("season", help="Stagione in formato YYYY-YY")
    pl.add_argument("--role", choices=["P", "D", "C", "A"], help="Filtra per ruolo")
    pl.add_argument("--team", help="Filtra per squadra (match parziale)")
    pl.add_argument("--name", help="Filtra per nome (match parziale)")
    pl.add_argument("--limit", type=int, default=50, help="Numero max risultati (default 50)")
    pl.add_argument("--offset", type=int, default=0, help="Offset per paginazione")

    pd = sub.add_parser("player", help="Dettaglio voti di un giocatore")
    pd.add_argument("player_id", type=int, help="ID del giocatore (da 'players' o 'search')")

    md = sub.add_parser("matchday", help="Voti di una giornata")
    md.add_argument("season", help="Stagione in formato YYYY-YY")
    md.add_argument("matchday", type=int, help="Numero giornata")
    md.add_argument("--role", choices=["P", "D", "C", "A"], help="Filtra per ruolo")
    md.add_argument("--team", help="Filtra per squadra (match parziale)")
    md.add_argument("--min-rating", type=float, dest="min_rating", help="Mostra solo voti >= soglia")

    tm = sub.add_parser("teams", help="Squadre di una stagione")
    tm.add_argument("season", help="Stagione in formato YYYY-YY")

    sr = sub.add_parser("search", help="Cerca giocatori per nome")
    sr.add_argument("name", help="Nome (parziale) del giocatore")
    sr.add_argument("--season", help="Limita la ricerca a una stagione (YYYY-YY)")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "seasons": cmd_seasons,
        "season": cmd_season,
        "players": cmd_players,
        "player": cmd_player,
        "matchday": cmd_matchday,
        "teams": cmd_teams,
        "search": cmd_search,
    }
    dispatch[args.command](args)
    print()


if __name__ == "__main__":
    main()
