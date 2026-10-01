"""Collegamento a Leghe Fantacalcio (API non ufficiale).

Ogni utente FantaNostalgia collega il proprio account incollando il suo JWT
Fantacalcio; il token è salvato cifrato su `user.fantacalcio_jwt` e non viene
mai restituito dalle API.

L'import delle formazioni usa il token dell'admin loggato come utente e salva
tramite lo stesso `save_lineups` dell'upload Excel.
"""
import requests
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from itsdangerous import BadSignature
from pydantic import BaseModel

from backend.api import fantacalcio as fc
from backend.api.db import get_db
from backend.api.routers.lineups import save_lineups
from backend.api.routers.auth import (
    USER_COOKIE_NAME,
    _verify_user_session_cookie,
    get_current_admin,
    get_current_user,
)

router = APIRouter(tags=["fantacalcio"])


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except fc.FantacalcioError as exc:
        raise HTTPException(status_code=502, detail=f"Fantacalcio ha risposto {exc}")
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Fantacalcio non raggiungibile: {exc}")


# ── Collegamento account (utente loggato) ───────────────────────────────────

class TokenBody(BaseModel):
    jwt: str


@router.get("/auth/user/fantacalcio")
def get_fantacalcio_link(user: dict = Depends(get_current_user)):
    """Stato del collegamento: scadenza del token e leghe visibili. Mai il token."""
    with get_db() as conn:
        jwt = fc.load_user_jwt(conn, user["id"])
    if not jwt:
        return {"connected": False, "token": None, "leagues": [], "error": None}
    result = {"connected": True, "token": fc.token_expiry(jwt), "leagues": [], "error": None}
    try:
        result["leagues"] = [
            {"id": lg.get("id"), "alias": lg.get("alias"), "name": lg.get("nome")}
            for lg in fc.leagues(jwt)
        ]
    except fc.FantacalcioError as exc:
        result["error"] = f"Fantacalcio ha risposto {exc}"
    except requests.RequestException as exc:
        result["error"] = f"Fantacalcio non raggiungibile: {exc}"
    return result


@router.put("/auth/user/fantacalcio")
def set_fantacalcio_link(body: TokenBody, user: dict = Depends(get_current_user)):
    jwt = body.jwt.strip().strip('"')
    expiry = fc.token_expiry(jwt)
    if expiry is None:
        raise HTTPException(status_code=422, detail="Token non valido: deve essere un JWT (inizia con eyJ…).")
    if expiry["days_left"] < 0:
        raise HTTPException(status_code=422, detail="Token scaduto: rigeneralo accedendo di nuovo a Fantacalcio.")
    with get_db() as conn:
        conn.execute("UPDATE user SET fantacalcio_jwt = ? WHERE id = ?", (fc.encrypt_token(jwt), user["id"]))
    return {"connected": True, "token": expiry}


@router.delete("/auth/user/fantacalcio")
def delete_fantacalcio_link(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        conn.execute("UPDATE user SET fantacalcio_jwt = NULL WHERE id = ?", (user["id"],))
    return {"connected": False}


# ── Esploratore (admin, con il token dell'admin loggato) ────────────────────

def _session_user_jwt(user_session: str | None) -> str:
    """JWT Fantacalcio dell'utente loggato nell'admin (cookie user_session)."""
    user_id = None
    if user_session:
        try:
            user_id = _verify_user_session_cookie(user_session)
        except (BadSignature, ValueError):
            user_id = None
    with get_db() as conn:
        jwt = fc.load_user_jwt(conn, user_id) if user_id else None
    if not jwt:
        raise HTTPException(
            status_code=400,
            detail="Nessun account Fantacalcio collegato: accedi con il tuo utente e collegalo da “Le mie leghe”.",
        )
    return jwt


def _league_token(user_session: str | None, league: str) -> str:
    jwt = _session_user_jwt(user_session)
    try:
        return _call(fc.league_jwt, jwt, league)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lega '{league}' non trovata tra quelle del tuo account.")


@router.get("/admin/fantacalcio/explore")
def fantacalcio_explore(
    league: str = Query(..., description="alias o id della lega su Fantacalcio"),
    path: str = Query(..., description="es. /onboarding/v1/league/competitions"),
    _: str = Depends(get_current_admin),
    user_session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
):
    """GET grezzo su un endpoint della lega, con i token oscurati nella risposta.
    Serve a scoprire gli endpoint non ancora mappati."""
    if not path.startswith("/") or "://" in path or ".." in path:
        raise HTTPException(status_code=400, detail="Il percorso deve iniziare con / (es. /onboarding/v1/league/status).")
    token = _league_token(user_session, league)
    return fc.redact(_call(fc.get, path, token))


# ── Import formazioni di giornata ───────────────────────────────────────────

@router.get("/admin/fantacalcio/{league}/competitions")
def fantacalcio_competitions(
    league: str,
    _: str = Depends(get_current_admin),
    user_session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
):
    token = _league_token(user_session, league)
    return [{"id": c.get("id"), "name": c.get("name")} for c in _call(fc.competitions, token)]


@router.get("/admin/fantacalcio/{league}/calendar/{competition_id}")
def fantacalcio_calendar(
    league: str,
    competition_id: int,
    _: str = Depends(get_current_admin),
    user_session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
):
    token = _league_token(user_session, league)
    return [
        {"match_day": d.get("matchDay"), "championship_match_day": d.get("championshipMatchDay"),
         "calculated": bool(d.get("calculated"))}
        for d in _call(fc.calendar, token, competition_id)
    ]


class ImportBody(BaseModel):
    fc_league: str
    competition_id: int
    fc_match_day: int


@router.post("/admin/league/{league_id}/lineups/{matchday}/fantacalcio")
def import_lineups_from_fantacalcio(
    league_id: int,
    matchday: int,
    body: ImportBody,
    _: str = Depends(get_current_admin),
    user_session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
):
    """Scarica formazioni e voti di una giornata calcolata e li salva come l'upload Excel."""
    token = _league_token(user_session, body.fc_league)
    day = next((d for d in _call(fc.calendar, token, body.competition_id)
                if d.get("matchDay") == body.fc_match_day), None)
    if day is None:
        raise HTTPException(status_code=404, detail=f"Giornata {body.fc_match_day} non trovata nel calendario.")
    if not day.get("calculated"):
        raise HTTPException(status_code=400, detail=f"La giornata {body.fc_match_day} non è ancora stata calcolata su Fantacalcio.")

    team_names = {t.get("id"): (t.get("n") or t.get("name") or "").strip()
                  for t in _call(fc.teams, token, body.competition_id)}
    player_names = {p.get("id"): p.get("name") for p in _call(fc.players, token)}
    lineups = [
        _call(fc.team_lineup, token, body.competition_id, day["matchDay"],
              day["championshipMatchDay"], m["tIdH"], m["tIdA"])
        for m in day.get("matches") or []
    ]
    rows, warnings, pairings = fc.lineup_rows(lineups, team_names, player_names)
    with get_db() as conn:
        return save_lineups(conn, league_id, matchday, rows, warnings, pairings)
