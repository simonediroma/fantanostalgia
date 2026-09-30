"""Collegamento a Leghe Fantacalcio (API non ufficiale).

Ogni utente FantaNostalgia collega il proprio account incollando il suo JWT
Fantacalcio; il token è salvato cifrato su `user.fantacalcio_jwt` e non viene
mai restituito dalle API.

Fase 1: verificare che il server raggiunga l'API e trovare l'endpoint delle
formazioni/voti di giornata (esploratore admin). L'import in `lineup` arriverà
quando se ne conoscerà la forma della risposta.
"""
import requests
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from itsdangerous import BadSignature
from pydantic import BaseModel

from backend.api import fantacalcio as fc
from backend.api.db import get_db
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

@router.get("/admin/fantacalcio/explore")
def fantacalcio_explore(
    league: str = Query(..., description="alias o id della lega su Fantacalcio"),
    path: str = Query(..., description="es. /onboarding/v1/league/competitions"),
    _: str = Depends(get_current_admin),
    user_session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
):
    """GET grezzo su un endpoint della lega, con i token oscurati nella risposta.
    Serve a scoprire gli endpoint non ancora mappati (formazioni, voti)."""
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
    if not path.startswith("/") or "://" in path or ".." in path:
        raise HTTPException(status_code=400, detail="Il percorso deve iniziare con / (es. /onboarding/v1/league/status).")
    try:
        token = _call(fc.league_jwt, jwt, league)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lega '{league}' non trovata tra quelle del tuo account.")
    return fc.redact(_call(fc.get, path, token))
