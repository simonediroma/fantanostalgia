import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Header, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from backend.api.db import get_db
from backend.api.notifications import notify_league_join, notify_registration

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


USER_COOKIE_NAME = "user_session"


def _make_user_session_cookie(user_id: int) -> str:
    return _signer.sign(f"user:{user_id}").decode()


def _verify_user_session_cookie(token: str) -> int:
    max_age = SESSION_EXPIRE_HOURS * 3600
    raw = _signer.unsign(token, max_age=max_age).decode()
    if not raw.startswith("user:"):
        raise BadSignature("not a user token")
    return int(raw[5:])


def get_current_admin(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    user_session: str | None = Cookie(default=None, alias=USER_COOKIE_NAME),
) -> str:
    if session:
        try:
            return _verify_session_cookie(session)
        except SignatureExpired:
            raise HTTPException(status_code=401, detail="Sessione scaduta")
        except BadSignature:
            raise HTTPException(status_code=401, detail="Sessione non valida")
    if user_session:
        try:
            user_id = _verify_user_session_cookie(user_session)
        except SignatureExpired:
            raise HTTPException(status_code=401, detail="Sessione scaduta")
        except (BadSignature, ValueError):
            raise HTTPException(status_code=401, detail="Sessione non valida")
        with get_db() as conn:
            row = conn.execute(
                "SELECT email, COALESCE(is_admin, 0) AS is_admin FROM user WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row and row["is_admin"]:
            return row["email"]
        raise HTTPException(status_code=403, detail="Permessi amministratore richiesti")
    raise HTTPException(status_code=401, detail="Non autenticato")


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
            "SELECT id, email, name, COALESCE(is_admin, 0) AS is_admin FROM user WHERE id = ?",
            (user_id,),
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
def register(body: RegisterBody, request: Request, response: Response, background_tasks: BackgroundTasks):
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
        league = conn.execute(
            "SELECT name FROM league WHERE id = ?", (invite["league_id"],)
        ).fetchone()

    _set_user_cookie(response, user_id)
    background_tasks.add_task(
        notify_registration, body.email, body.name, league["name"], str(request.base_url).rstrip("/")
    )
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
        elevation = conn.execute(
            "SELECT status FROM admin_elevation_request WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "is_admin": bool(user["is_admin"]),
        "elevation_status": elevation["status"] if elevation else None,
        "leagues": [dict(r) for r in rows],
    }


@router.post("/user/join")
def user_join_league(
    body: dict,
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
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
        league = conn.execute(
            "SELECT l.name FROM league l JOIN manager m ON m.league_id = l.id WHERE m.id = ?",
            (invite["manager_id"],),
        ).fetchone()

    background_tasks.add_task(
        notify_league_join, user["email"], user["name"], league["name"], str(request.base_url).rstrip("/")
    )
    return {"detail": "Unito alla lega con successo"}


# ── Elevazione coach → admin ─────────────────────────────────────────────────

def _elevation_request_dict(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "status": row["status"],
        "requested_at": row["requested_at"],
        "resolved_at": row["resolved_at"],
        "resolved_by": row["resolved_by"],
    }


@router.post("/user/elevation-request", status_code=201)
def request_elevation(user: dict = Depends(get_current_user)):
    if user["is_admin"]:
        raise HTTPException(status_code=400, detail="Sei già amministratore")
    with get_db() as conn:
        pending = conn.execute(
            "SELECT id FROM admin_elevation_request WHERE user_id = ? AND status = 'pending'",
            (user["id"],),
        ).fetchone()
        if pending is not None:
            raise HTTPException(status_code=400, detail="Hai già una richiesta in attesa")
        cur = conn.execute(
            "INSERT INTO admin_elevation_request (user_id) VALUES (?)", (user["id"],)
        )
        row = conn.execute(
            """
            SELECT r.id, r.user_id, u.name, u.email, r.status, r.requested_at, r.resolved_at, r.resolved_by
            FROM admin_elevation_request r JOIN user u ON u.id = r.user_id
            WHERE r.id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
    return _elevation_request_dict(row)


@router.get("/admin/elevation-requests")
def list_elevation_requests(_: str = Depends(get_current_admin)):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.user_id, u.name, u.email, r.status, r.requested_at, r.resolved_at, r.resolved_by
            FROM admin_elevation_request r JOIN user u ON u.id = r.user_id
            ORDER BY r.requested_at DESC
            """
        ).fetchall()
    return [_elevation_request_dict(r) for r in rows]


def _resolve_elevation_request(request_id: int, approve: bool, admin: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, status FROM admin_elevation_request WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Richiesta non trovata")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail="Richiesta già evasa")

        new_status = "approved" if approve else "rejected"
        conn.execute(
            "UPDATE admin_elevation_request SET status = ?, resolved_at = CURRENT_TIMESTAMP, resolved_by = ? WHERE id = ?",
            (new_status, admin, request_id),
        )
        if approve:
            conn.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (row["user_id"],))

        updated = conn.execute(
            """
            SELECT r.id, r.user_id, u.name, u.email, r.status, r.requested_at, r.resolved_at, r.resolved_by
            FROM admin_elevation_request r JOIN user u ON u.id = r.user_id
            WHERE r.id = ?
            """,
            (request_id,),
        ).fetchone()
    return _elevation_request_dict(updated)


@router.post("/admin/elevation-requests/{request_id}/approve")
def approve_elevation_request(request_id: int, admin: str = Depends(get_current_admin)):
    return _resolve_elevation_request(request_id, approve=True, admin=admin)


@router.post("/admin/elevation-requests/{request_id}/reject")
def reject_elevation_request(request_id: int, admin: str = Depends(get_current_admin)):
    return _resolve_elevation_request(request_id, approve=False, admin=admin)
