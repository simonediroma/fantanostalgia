import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
SESSION_EXPIRE_HOURS = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))

COOKIE_NAME = "session"
_signer = TimestampSigner(SECRET_KEY)


def _make_session_cookie(username: str) -> str:
    return _signer.sign(username).decode()


def _verify_session_cookie(token: str) -> str:
    max_age = SESSION_EXPIRE_HOURS * 3600
    username = _signer.unsign(token, max_age=max_age)
    return username.decode()


def get_current_admin(session: str | None = Cookie(default=None, alias=COOKIE_NAME)) -> str:
    if not session:
        raise HTTPException(status_code=401, detail="Non autenticato")
    try:
        return _verify_session_cookie(session)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Sessione non valida")


def get_current_admin_or_bearer(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    authorization: str | None = Header(default=None),
) -> str:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        if token == SECRET_KEY:
            return "github-actions"
        raise HTTPException(status_code=401, detail="Bearer token non valido")
    if session:
        try:
            return _verify_session_cookie(session)
        except SignatureExpired:
            raise HTTPException(status_code=401, detail="Sessione scaduta")
        except BadSignature:
            raise HTTPException(status_code=401, detail="Sessione non valida")
    raise HTTPException(status_code=401, detail="Non autenticato")


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginBody, response: Response):
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    token = _make_session_cookie(body.username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_EXPIRE_HOURS * 3600,
    )
    return {"detail": "Login effettuato"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"detail": "Logout effettuato"}


@router.get("/me")
def me(username: str = Depends(get_current_admin)):
    return {"username": username}
