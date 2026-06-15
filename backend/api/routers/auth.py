import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from backend.api.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

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


USER_COOKIE_NAME = "user_session"


def _make_user_session_cookie(user_id: int) -> str:
    return _signer.sign(f"user:{user_id}").decode()


def _verify_user_session_cookie(token: str) -> int:
    max_age = SESSION_EXPIRE_HOURS * 3600
    raw = _signer.unsign(token, max_age=max_age).decode()
    if not raw.startswith("user:"):
        raise BadSignature("not a user token")
    return int(raw[5:])


def get_current_user(
    session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Non autenticato")
    try:
        user_id = _verify_user_session_cookie(session)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except (BadSignature, ValueError):
        raise HTTPException(status_code=401, detail="Sessione non valida")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, name FROM user WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Utente non trovato")
    return dict(row)


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


# ── User (allenatori) auth ──────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name: str
    email: str
    password: str
    invite_token: str


class UserLoginBody(BaseModel):
    email: str
    password: str


def _set_user_cookie(response: Response, user_id: int) -> None:
    token = _make_user_session_cookie(user_id)
    response.set_cookie(
        key=USER_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_EXPIRE_HOURS * 3600,
    )


@router.post("/register", status_code=201)
def register(body: RegisterBody, response: Response):
    with get_db() as conn:
        invite = conn.execute(
            "SELECT id, league_id, manager_id, used_by_user_id FROM league_invite WHERE token = ?",
            (body.invite_token,),
        ).fetchone()
        if invite is None:
            raise HTTPException(status_code=400, detail="Token invito non valido")
        if invite["used_by_user_id"] is not None:
            raise HTTPException(status_code=400, detail="Invito già utilizzato")

        existing = conn.execute(
            "SELECT id FROM user WHERE email = ?", (body.email,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=400,
                detail="Email già registrata. Accedi con le tue credenziali e usa il link invito per unirti alla lega.",
            )

        password_hash = _pwd_ctx.hash(body.password)
        cur = conn.execute(
            "INSERT INTO user (email, name, password_hash) VALUES (?, ?, ?)",
            (body.email, body.name, password_hash),
        )
        user_id = cur.lastrowid

        conn.execute(
            "UPDATE league_invite SET used_by_user_id = ?, used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id, invite["id"]),
        )
        conn.execute(
            "UPDATE manager SET user_id = ? WHERE id = ?",
            (user_id, invite["manager_id"]),
        )

    _set_user_cookie(response, user_id)
    return {"id": user_id, "name": body.name, "email": body.email}


@router.post("/user/login")
def user_login(body: UserLoginBody, response: Response):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM user WHERE email = ?",
            (body.email,),
        ).fetchone()
    if row is None or not _pwd_ctx.verify(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    _set_user_cookie(response, row["id"])
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


@router.post("/user/logout")
def user_logout(response: Response):
    response.delete_cookie(key=USER_COOKIE_NAME)
    return {"detail": "Logout effettuato"}


@router.get("/user/me")
def user_me(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT m.id AS manager_id, m.team_name, m.assignments_locked,
                   l.id AS league_id, l.name AS league_name,
                   l.associations_closed
            FROM manager m
            JOIN league l ON l.id = m.league_id
            WHERE m.user_id = ?
            ORDER BY l.id
            """,
            (user["id"],),
        ).fetchall()
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "leagues": [dict(r) for r in rows],
    }


@router.post("/user/join")
def user_join_league(body: dict, user: dict = Depends(get_current_user)):
    invite_token = body.get("invite_token")
    if not invite_token:
        raise HTTPException(status_code=400, detail="invite_token mancante")
    with get_db() as conn:
        invite = conn.execute(
            "SELECT id, manager_id, used_by_user_id FROM league_invite WHERE token = ?",
            (invite_token,),
        ).fetchone()
        if invite is None:
            raise HTTPException(status_code=400, detail="Token invito non valido")
        if invite["used_by_user_id"] is not None:
            raise HTTPException(status_code=400, detail="Invito già utilizzato")
        conn.execute(
            "UPDATE league_invite SET used_by_user_id = ?, used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"], invite["id"]),
        )
        conn.execute(
            "UPDATE manager SET user_id = ? WHERE id = ?",
            (user["id"], invite["manager_id"]),
        )
    return {"detail": "Unito alla lega con successo"}
