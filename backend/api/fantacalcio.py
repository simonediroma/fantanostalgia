"""Client minimale per apileague.fantacalcio.it (Leghe Fantacalcio).

API NON ufficiale, ricavata dal frontend del sito: può cambiare senza preavviso.
Due livelli di token JWT (validità ~1 anno, nessun cookie):
  - user JWT   (role=user): serve solo per GET /onboarding/v2/profile
  - league JWT (role=user_league): tutti gli endpoint della lega, letti da profile.leghe[i].jwt

Il user JWT è per utente FantaNostalgia (colonna `user.fantacalcio_jwt`, cifrata
con una chiave derivata da SECRET_KEY); i league JWT non vengono mai salvati.
"""
import base64
import hashlib
import json
import os
import time
from typing import Any

import requests
from cryptography.fernet import Fernet, InvalidToken

BASE_URL = "https://apileague.fantacalcio.it"
# Chiave client statica e pubblica, presente nella config del bundle JS del sito.
APP_KEY = os.getenv("FANTACALCIO_APP_KEY", "ICiELOObd5DF5uJEATi77CRvHiiRuMU0")
USER_AGENT = "fantanostalgia/1.0"
MIN_INTERVAL = 0.5  # secondi tra una chiamata e l'altra
TIMEOUT = 20

_last_call = 0.0


class FantacalcioError(RuntimeError):
    def __init__(self, status: int, code: str | None, message: str, url: str):
        super().__init__(f"{status} {code or ''} {message}".strip())
        self.status, self.code, self.message, self.url = status, code, message, url


def _fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY", "dev-secret-key").encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret).digest()))


def encrypt_token(jwt: str) -> str:
    return _fernet().encrypt(jwt.encode()).decode()


def load_user_jwt(conn, user_id: int) -> str | None:
    """JWT Fantacalcio dell'utente, o None se non collegato (o se SECRET_KEY è cambiata)."""
    row = conn.execute("SELECT fantacalcio_jwt FROM user WHERE id = ?", (user_id,)).fetchone()
    if not row or not row["fantacalcio_jwt"]:
        return None
    try:
        return _fernet().decrypt(row["fantacalcio_jwt"].encode()).decode()
    except InvalidToken:
        return None


def token_expiry(jwt: str) -> dict | None:
    """Scadenza del JWT letta dal payload, senza verificarne la firma."""
    try:
        payload = jwt.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        exp = int(claims["exp"])
    except (IndexError, KeyError, ValueError, TypeError):
        return None
    return {"exp": exp, "days_left": int((exp - time.time()) // 86400)}


def get(path: str, token: str, params: dict | None = None, headers: dict | None = None) -> Any:
    """GET su {BASE_URL}{path} con rate limit lato client. Solleva FantacalcioError su HTTP >= 400."""
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    url = BASE_URL + path
    r = requests.get(
        url,
        params=params,
        headers={
            "app_key": APP_KEY,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
            **(headers or {}),
        },
        timeout=TIMEOUT,
    )
    _last_call = time.monotonic()
    try:
        body = r.json()
    except ValueError:
        body = r.text
    if r.status_code >= 400:
        code = body.get("code") if isinstance(body, dict) else None
        msg = body.get("message", "") if isinstance(body, dict) else str(body)[:200]
        raise FantacalcioError(r.status_code, code, msg, url)
    return body


def profile(user_jwt: str) -> dict:
    body = get("/onboarding/v2/profile", user_jwt, headers={"state_user": str(int(time.time() * 1000))})
    return body.get("data", body) if isinstance(body, dict) else {}


def leagues(user_jwt: str) -> list[dict]:
    return profile(user_jwt).get("leghe") or []


def league_jwt(user_jwt: str, alias: str) -> str:
    for lg in leagues(user_jwt):
        if alias in (str(lg.get("id")), lg.get("alias")):
            tok = lg.get("jwt")
            if tok:
                return tok
    raise KeyError(alias)


def redact(value: Any) -> Any:
    """Toglie token e JWT da una risposta prima di mostrarla nell'admin."""
    if isinstance(value, dict):
        return {
            k: "***" if k.lower() in {"jwt", "token", "token_auth", "sendbird_token"} else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str) and value.startswith("eyJ"):
        return "***"
    return value


# ── Endpoint di lega (league JWT) ───────────────────────────────────────────

def competitions(token: str) -> list[dict]:
    return get("/onboarding/v1/league/competitions", token)


def calendar(token: str, competition_id: int) -> list[dict]:
    """[{matchDay, championshipMatchDay, calculated, matches: [{tIdH, tIdA, ...}]}]"""
    return get(f"/onboarding/v1/league/competition/calendar/{competition_id}", token)


def teams(token: str, competition_id: int) -> list[dict]:
    out, page = [], 1
    while True:
        r = get("/onboarding/v1/league/competition/teams", token,
                params={"page": page, "pageSize": 50, "competitionId": competition_id})
        out += r.get("data", [])
        if not r.get("nextPage"):
            return out
        page += 1


def players(token: str) -> list[dict]:
    """Anagrafica: id (= pid delle formazioni), name, fcrle (1=P 2=D 3=C 4=A)."""
    return get("/onboarding/v1/league/players", token).get("players", [])


def team_lineup(token: str, competition_id: int, match_day: int, championship_match_day: int,
                home_id: int, away_id: int) -> dict:
    return get(f"/gaming/v1/teamLineup/{competition_id}/{match_day}/{championship_match_day}"
               f"/{home_id}/{away_id}", token)


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
    per inserire in rosa i giocatori acquistati dopo l'import del listone."""
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
                           "score_no_bonus": no_bonus, "score_bonus": with_bonus}
                    role = (player_roles or {}).get(p.get("pid"))
                    if role:
                        row["role"] = role
                    rows.append(row)
        if all(names):
            pairings.append((names[0], names[1]))
    return rows, warnings, pairings
