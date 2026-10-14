"""
Ricostruisce le partite di una giornata storica dai voti per giocatore.

Il DB storico non salva le partite (manca l'avversario): per ogni squadra si
conoscono i gol dei suoi giocatori, i gol subiti e l'esito. Due squadre sono
accoppiate se i numeri sono coerenti (gol subiti da A = gol fatti da B, esito
compatibile). Gli accoppiamenti ambigui restano non accoppiati.

Se lo scraper ha salvato il calendario (tabella historic_match),
matches_from_fixtures usa le partite vere (casa/trasferta e risultato esatti).
"""

_ROLE_ORDER = {"P": 1, "D": 2, "C": 3, "A": 4}


def _team_summaries(rows) -> dict[str, dict]:
    teams: dict[str, dict] = {}
    for r in rows:
        t = teams.setdefault(r["team"], {
            "team": r["team"], "players": [], "goals": 0, "own_goals": 0,
            "conceded": 0, "won": False,
        })
        t["players"].append(dict(r))
        t["goals"] += r["goals"] or 0
        t["own_goals"] += r["own_goals"] or 0
        t["conceded"] = max(t["conceded"], r["goals_conceded"] or 0)
        t["won"] = t["won"] or bool(r["team_won"])
    for t in teams.values():
        t["players"].sort(key=lambda p: (_ROLE_ORDER.get(p["role"], 9), p["name"]))
    return teams


def _compatible(a: dict, b: dict) -> bool:
    a_score = b["conceded"]
    b_score = a["conceded"]
    if a_score != a["goals"] + b["own_goals"] or b_score != b["goals"] + a["own_goals"]:
        return False
    if a["won"] and b["won"]:
        return False
    if a["won"]:
        return a_score > b_score
    if b["won"]:
        return b_score > a_score
    return a_score == b_score


def _tabellino(team: dict) -> dict:
    scorers, cards = [], []
    for p in team["players"]:
        if p["goals"]:
            scorers.append({"name": p["name"], "goals": p["goals"],
                            "penalties": p.get("penalties_scored") or 0, "own": False})
        if p.get("own_goals"):
            scorers.append({"name": p["name"], "goals": p["own_goals"], "penalties": 0, "own": True})
        if p["red_cards"]:
            cards.append({"name": p["name"], "card": "red"})
        elif p["yellow_cards"]:
            cards.append({"name": p["name"], "card": "yellow"})
    return {"team": team["team"], "players": team["players"], "scorers": scorers, "cards": cards}


def reconstruct_matches(rows) -> dict:
    """
    rows: righe historic_rating + player_historic di una giornata e stagione
    (campi name, role, team, rating, goals, own_goals, penalties_scored,
    yellow_cards, red_cards, goals_conceded, team_won, minutes).

    Ritorna {"matches": [{home, away, home_goals, away_goals}], "unpaired": [team]}.
    "home"/"away" indicano solo la posizione (casa/trasferta non è nota).
    """
    teams = _team_summaries(rows)
    names = sorted(teams)
    candidates = {
        n: {m for m in names if m != n and _compatible(teams[n], teams[m])}
        for n in names
    }

    pairs: list[tuple[str, str]] = []
    changed = True
    while changed:
        changed = False
        for n in names:
            if len(candidates.get(n, ())) != 1:
                continue
            m = next(iter(candidates[n]))
            if candidates.get(m) != {n}:
                continue
            pairs.append((n, m))
            for k in (n, m):
                candidates.pop(k)
            for c in candidates.values():
                c.discard(n)
                c.discard(m)
            changed = True

    paired = {k for p in pairs for k in p}
    matches = [{
        "home": _tabellino(teams[a]),
        "away": _tabellino(teams[b]),
        "home_goals": teams[b]["conceded"],
        "away_goals": teams[a]["conceded"],
    } for a, b in sorted(pairs)]
    unpaired = [{
        **_tabellino(teams[n]),
        "conceded": teams[n]["conceded"],
        "won": teams[n]["won"],
    } for n in names if n not in paired]
    return {"matches": matches, "unpaired": unpaired}


def matches_from_fixtures(rows, fixtures) -> dict:
    """
    rows: come reconstruct_matches. fixtures: righe historic_match della stessa
    giornata (home_team, away_team, home_goals, away_goals).
    Stesso formato di ritorno di reconstruct_matches; le squadre con voti ma
    senza partita nel calendario finiscono in "unpaired".
    """
    teams = _team_summaries(rows)

    def side(name: str) -> dict:
        t = teams.get(name) or {"team": name, "players": []}
        return _tabellino(t)

    matches = [{
        "home": side(f["home_team"]),
        "away": side(f["away_team"]),
        "home_goals": f["home_goals"],
        "away_goals": f["away_goals"],
    } for f in fixtures]
    in_fixtures = {f[k] for f in fixtures for k in ("home_team", "away_team")}
    unpaired = [{
        **_tabellino(teams[n]),
        "conceded": teams[n]["conceded"],
        "won": teams[n]["won"],
    } for n in sorted(teams) if n not in in_fixtures]
    return {"matches": matches, "unpaired": unpaired}
