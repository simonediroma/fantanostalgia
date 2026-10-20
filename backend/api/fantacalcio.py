"""Dati di Leghe Fantacalcio (API non ufficiale) → formato FantaNostalgia.

Il server non chiama mai apileague.fantacalcio.it: da Cloud Run e da client non
browser l'API risponde 403. I dati li scarica l'estensione Chrome (`extension/`)
dalla pagina di leghe.fantacalcio.it, con la sessione dell'admin, e li invia
grezzi agli endpoint `/ext/v1`. Qui restano solo le conversioni.
"""
from typing import Any


def contains_token(value: Any) -> bool:
    """True se il payload contiene una stringa a forma di JWT: l'estensione non
    deve mai inviare token Fantacalcio al nostro server."""
    if isinstance(value, dict):
        return any(contains_token(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_token(v) for v in value)
    return isinstance(value, str) and value.startswith("eyJ") and value.count(".") == 2


def as_list(body: Any, key: str = "data") -> list:
    """Le risposte sono liste o oggetti con la lista sotto `key`."""
    if isinstance(body, dict):
        return body.get(key) or []
    return body or []


def parse_roster(team: dict) -> list[dict]:
    ids = [int(x) for x in (team.get("cal") or "").split(";") if x]
    prices = [x for x in (team.get("cs") or "").split(";") if x != ""]
    return [{"player_id": pid, "purchase_price": int(prices[i]) if i < len(prices) else None}
            for i, pid in enumerate(ids)]


# ── Conversione formazioni → righe per lineups.save_lineups ─────────────────

NO_VOTE_THRESHOLD = 50  # scr 55/56 (con cscr 100) = senza voto


def _scores(p: dict) -> tuple[float | None, float | None]:
    """(voto in pagella `scr`, fantavoto `cscr`) di un giocatore; (None, None) se s.v.
    Per i giocatori senza alter ego il calcolo usa solo il voto in pagella."""
    scr, cscr = p.get("scr"), p.get("cscr")
    if scr is None or cscr is None or scr >= NO_VOTE_THRESHOLD:
        return None, None
    return float(scr), float(cscr)


FC_ROLES = {1: "P", 2: "D", 3: "C", 4: "A"}


def lineup_rows(lineups: list[dict], team_names: dict, player_names: dict,
                player_roles: dict | None = None
                ) -> tuple[list[dict], list[str], list[tuple[str, str]]]:
    """Converte le risposte teamLineup di una giornata nel formato del parser Excel.
    `player_roles` (pid → P/D/C/A) aggiunge `role` alle righe: serve a save_lineups
    per creare in anagrafica (senza squadra) i giocatori che non conosce."""
    rows, warnings, pairings = [], [], []
    for match in lineups:
        names = []
        for side in ("home", "away"):
            team = match.get(side) or {}
            tname = team_names.get(team.get("tid"))
            if tname is None:
                warnings.append(f"Squadra Fantacalcio {team.get('tid')} non trovata — saltata")
                names.append(None)
                continue
            names.append(tname)
            for slot, is_starter in (("starts", 1), ("bench", 0)):
                for p in team.get(slot) or []:
                    pname = player_names.get(p.get("pid"))
                    if pname is None:
                        warnings.append(f"Giocatore Fantacalcio {p.get('pid')} non in anagrafica — saltato")
                        continue
                    no_bonus, with_bonus = _scores(p)
                    row = {"manager": tname, "player": pname, "is_starter": is_starter,
                           "score_no_bonus": no_bonus, "score_bonus": with_bonus,
                           "fc_id": p.get("pid")}
                    role = (player_roles or {}).get(p.get("pid"))
                    if role:
                        row["role"] = role
                    rows.append(row)
        if all(names):
            pairings.append((names[0], names[1]))
    return rows, warnings, pairings


def pair_day_lineups(day: dict, team_lineups: list[dict]) -> tuple[list[dict], list[str]]:
    """teamLineup/{comp}/{matchDay}/{champDay} restituisce tutte le squadre della
    giornata: le accoppia casa/trasferta con le partite del calendario."""
    by_tid = {t.get("tid"): t for t in team_lineups}
    matches, warnings = [], []
    for m in day.get("matches") or []:
        home, away = by_tid.get(m.get("tIdH")), by_tid.get(m.get("tIdA"))
        for tid, team in ((m.get("tIdH"), home), (m.get("tIdA"), away)):
            if team is None:
                warnings.append(f"Formazione della squadra Fantacalcio {tid} assente — saltata")
        matches.append({"home": home or {"tid": m.get("tIdH")}, "away": away or {"tid": m.get("tIdA")}})
    return matches, warnings
