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

def _post(path: str, token: str) -> dict:
    url = BASE_URL.rstrip("/") + path
    req = urllib.request.Request(url, data=b"", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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
        sys.exit(1)


def _get_token(username: str, password: str) -> str:
    url = BASE_URL.rstrip("/") + "/auth/token"
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body
        print(f"[LOGIN FALLITO {e.code}] {detail}", file=sys.stderr)
        sys.exit(1)


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


def cmd_trend(args) -> None:
    """Andamento di un giocatore con media mobile e indicatore di forma."""
    params = {"window": args.window}
    if args.player_id:
        data = _get(f"/inspect/players/{args.player_id}/trend", params)
    else:
        if not args.season:
            print("[ERRORE] --season è obbligatorio quando si usa --name (es. --season 2016-17)", file=sys.stderr)
            sys.exit(1)
        params["name"] = args.name
        params["season"] = args.season
        data = _get("/inspect/trend", params)

    if data.get("ambiguous"):
        print(f"\n  Trovati {len(data['candidates'])} giocatori con nome '{data['query']}' in {data['season']}:\n")
        _table(data["candidates"])
        print(f"\n  Usa: python scripts/inspect_db.py trend --id <id>  oppure un nome più preciso.")
        return
    p = data["player"]

    _section(f"Andamento: {p['name']}  ({p['role']}) — {p['team']} — {p['season']}")
    print(f"  Media stagionale : {data['season_avg']}")
    print(f"  Media ultimi {data['window']}   : {data['recent_avg']}  (forma: {_forma_label(data['forma_recente'])})")
    print(f"  Migliore         : giornata {data['best_matchday']['matchday']} → {data['best_matchday']['rating']}")
    print(f"  Peggiore         : giornata {data['worst_matchday']['matchday']} → {data['worst_matchday']['rating']}")

    _section(f"Voti con media mobile (finestra {data['window']})")

    for t in data["trend"]:
        bar = _bar(t["rating"])
        avg_marker = f"  ~{t['moving_avg']}" if t["moving_avg"] != t["rating"] else ""
        delta_str = ""
        if t["delta"] is not None:
            arrow = "▲" if t["delta"] > 0 else ("▼" if t["delta"] < 0 else "─")
            delta_str = f"  {arrow}{abs(t['delta']):.1f}"
        extras = []
        if t["goals"]:
            extras.append(f"⚽×{t['goals']}")
        if t["assists"]:
            extras.append(f"🅰×{t['assists']}")
        if t["yellow_cards"]:
            extras.append("🟨")
        if t["red_cards"]:
            extras.append("🟥")
        extra_str = "  " + " ".join(extras) if extras else ""
        print(f"  G{t['matchday']:>2}  {t['rating']:.1f}  {bar}{avg_marker}{delta_str}{extra_str}")

    print()
    print(f"  Legenda media mobile: ~X = media ultime {data['window']} giornate")


def _bar(rating: float) -> str:
    filled = max(0, min(10, round((rating - 4) * 2)))
    return "█" * filled + "░" * (10 - filled)


def _forma_label(delta: float) -> str:
    if delta >= 0.5:
        return f"+{delta:.2f} ↑ in forma"
    if delta <= -0.5:
        return f"{delta:.2f} ↓ sotto media"
    return f"{delta:+.2f} ─ nella norma"


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


def cmd_flush(args) -> None:
    """Svuota i dati storici dal DB (totale o per singola stagione)."""
    if args.season:
        scope_msg = f"la stagione {args.season}"
    else:
        scope_msg = "TUTTI i dati storici"

    print(f"\n  ⚠  Stai per cancellare {scope_msg} dal DB.")
    confirm = input("  Digita 'SI' per confermare: ").strip()
    if confirm != "SI":
        print("  Operazione annullata.")
        return

    token = _get_token(args.user, args.password)

    path = "/admin/historic/flush"
    if args.season:
        path += f"?season={urllib.parse.quote(args.season)}"

    data = _post(path, token)
    _section("Flush completato")
    print(f"  {data['message']}")


def cmd_normalize(args) -> None:
    """Bonifica il DB convertendo tutte le stagioni al formato canonico YYYY/YY."""
    print(f"\n  Connessione a {BASE_URL}...")
    print("  Login admin in corso...")
    token = _get_token(args.user, args.password)
    print("  Avvio bonifica — attendere...")
    data = _post("/admin/historic/normalize-seasons", token)

    _section("Risultato bonifica formato stagioni")
    print(f"  {data['message']}")

    if data["changes"]:
        print()
        print("  Stagioni aggiornate in player_historic:")
        _table(data["changes"])

    if data["leagues_changes"]:
        print()
        print("  Stagioni aggiornate in league:")
        _table(data["leagues_changes"])

    if data["conflicts"]:
        print()
        print("  ⚠  Conflitti NON risolti automaticamente (presenza di dati doppi):")
        _table(data["conflicts"])
        print()
        print("  Questi record richiedono revisione manuale.")


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
  python scripts/inspect_db.py trend --name Dybala --season 2016-17
  python scripts/inspect_db.py trend --name Dybala --season 2016-17 --window 3
  python scripts/inspect_db.py trend --id 42
  python scripts/inspect_db.py search Totti
  python scripts/inspect_db.py search Dybala --season 2016-17
  python scripts/inspect_db.py teams 2016-17
  python scripts/inspect_db.py flush --password <pwd>
  python scripts/inspect_db.py flush --season 2000-01 --password <pwd>
  python scripts/inspect_db.py normalize --password <pwd>

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

    tr = sub.add_parser("trend", help="Andamento di un giocatore con media mobile")
    tr_group = tr.add_mutually_exclusive_group(required=True)
    tr_group.add_argument("--name", help="Nome (parziale) del giocatore")
    tr_group.add_argument("--id", dest="player_id", type=int, help="ID del giocatore")
    tr.add_argument("--season", help="Stagione YYYY-YY (obbligatoria con --name)")
    tr.add_argument("--window", type=int, default=5, help="Ampiezza media mobile (default 5)")

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

    fl = sub.add_parser("flush", help="Cancella dati storici dal DB per reimportarli")
    fl.add_argument("--season", help="Stagione da cancellare (es. 2000-01). Ometti per cancellare tutto.")
    fl.add_argument("--user", default="admin", help="Username admin (default: admin)")
    fl.add_argument("--password", required=True, help="Password admin")

    nrm = sub.add_parser("normalize", help="Bonifica il DB: converte stagioni al formato YYYY/YY")
    nrm.add_argument("--user", default="admin", help="Username admin (default: admin)")
    nrm.add_argument("--password", required=True, help="Password admin")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "seasons": cmd_seasons,
        "season": cmd_season,
        "players": cmd_players,
        "player": cmd_player,
        "trend": cmd_trend,
        "matchday": cmd_matchday,
        "teams": cmd_teams,
        "search": cmd_search,
        "flush": cmd_flush,
        "normalize": cmd_normalize,
    }
    dispatch[args.command](args)
    print()


if __name__ == "__main__":
    main()
