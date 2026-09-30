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
