"""Import da Leghe Fantacalcio tramite l'estensione Chrome (`extension/`).

L'API di Fantacalcio risponde 403 alle chiamate fuori dal browser, quindi il
server non la chiama mai: l'estensione scarica i dati dalla pagina di
leghe.fantacalcio.it con la sessione dell'admin e li invia grezzi agli
endpoint `/ext/v1`, autenticati con una chiave generata dall'admin.
I token Fantacalcio non arrivano mai qui: un payload che ne contiene uno è
rifiutato.
"""
import hashlib
import io
import os
import secrets
import zipfile

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.api import fantacalcio as fc
from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin
from backend.api.routers.lineups import save_lineups
from backend.engine.rosters import RosterSyncError, sync_rosters

router = APIRouter(tags=["fantacalcio"])

EXTENSION_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "extension")


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# ── Chiavi dell'estensione (admin) ──────────────────────────────────────────

class KeyBody(BaseModel):
    label: str = ""


@router.get("/admin/fantacalcio/keys")
def list_keys(_: str = Depends(get_current_admin)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, label, created_at, last_used_at FROM ext_api_key"
            " WHERE revoked_at IS NULL ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@router.post("/admin/fantacalcio/keys", status_code=201)
def create_key(body: KeyBody, _: str = Depends(get_current_admin)):
    """La chiave si vede solo ora: nel DB resta l'hash."""
    key = "fn_" + secrets.token_urlsafe(32)
    with get_db() as conn:
        kid = conn.execute("INSERT INTO ext_api_key (label, key_hash) VALUES (?, ?)",
                           (body.label.strip() or "Estensione", _hash(key))).lastrowid
    return {"id": kid, "key": key}


@router.delete("/admin/fantacalcio/keys/{key_id}")
def revoke_key(key_id: int, _: str = Depends(get_current_admin)):
    with get_db() as conn:
        conn.execute("UPDATE ext_api_key SET revoked_at = CURRENT_TIMESTAMP"
                     " WHERE id = ? AND revoked_at IS NULL", (key_id,))
    return {"revoked": key_id}


@router.get("/admin/fantacalcio/extension.zip")
def download_extension(_: str = Depends(get_current_admin)):
    if not os.path.isdir(EXTENSION_DIR):
        raise HTTPException(status_code=404, detail="Estensione non disponibile")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(os.listdir(EXTENSION_DIR)):
            path = os.path.join(EXTENSION_DIR, name)
            if os.path.isfile(path):
                zf.write(path, f"fantanostalgia-extension/{name}")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="fantanostalgia-extension.zip"'})


# ── Endpoint per l'estensione ───────────────────────────────────────────────

def get_ext_key(authorization: str | None = Header(default=None)) -> int:
    key = authorization.removeprefix("Bearer ").strip() if authorization else ""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM ext_api_key WHERE key_hash = ? AND revoked_at IS NULL",
                           (_hash(key),)).fetchone() if key else None
        if row is None:
            raise HTTPException(status_code=401, detail="Chiave dell'estensione non valida o revocata")
        conn.execute("UPDATE ext_api_key SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    return row["id"]


def _no_tokens(body: BaseModel) -> None:
    if fc.contains_token(body.model_dump()):
        raise HTTPException(status_code=400, detail="Il payload contiene un token: non viene accettato")


def _check_league(conn, league_id: int) -> None:
    if conn.execute("SELECT 1 FROM league WHERE id = ?", (league_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


@router.get("/ext/v1/leagues")
def ext_leagues(_: int = Depends(get_ext_key)):
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT id, name FROM league ORDER BY id DESC")]


class RostersBody(BaseModel):
    teams: list[dict]           # /onboarding/v1/league/teams, tutte le pagine
    total: int | None = None    # `item` della risposta
    players: list[dict]         # /onboarding/v1/league/players
    force: bool = False


@router.post("/ext/v1/league/{league_id}/rosters")
def ext_rosters(league_id: int, body: RostersBody, _: int = Depends(get_ext_key)):
    """Allinea le rose a Leghe Fantacalcio: acquisti, spostamenti, svincoli."""
    _no_tokens(body)
    with get_db() as conn:
        _check_league(conn, league_id)
        try:
            return sync_rosters(conn, league_id, body.teams, body.total, body.players, force=body.force)
        except RosterSyncError as exc:
            raise HTTPException(status_code=409, detail=str(exc))


class LineupsBody(BaseModel):
    day: dict                       # giornata del calendario (matchDay, calculated, matches)
    lineups: list[dict]             # /gaming/v1/teamLineup/{comp}/{matchDay}/{champDay}
    competition_teams: list[dict]   # /onboarding/v1/league/competition/teams (id, n)
    players: list[dict]
    league_teams: list[dict] | None = None  # se presenti, sync rose prima dell'import
    league_total: int | None = None


@router.post("/ext/v1/league/{league_id}/lineups/{matchday}")
def ext_lineups(league_id: int, matchday: int, body: LineupsBody, _: int = Depends(get_ext_key)):
    """Formazioni e voti di una giornata calcolata, salvati come l'upload Excel."""
    _no_tokens(body)
    if not body.day.get("calculated"):
        raise HTTPException(status_code=400,
                            detail=f"La giornata {body.day.get('matchDay')} non è ancora stata calcolata su Fantacalcio.")
    roster_sync = None
    if body.league_teams is not None:
        # Sync rose non forzata: se fallisce l'import va avanti e l'errore va nel riepilogo
        with get_db() as conn:
            _check_league(conn, league_id)
            try:
                roster_sync = sync_rosters(conn, league_id, body.league_teams, body.league_total, body.players)
            except RosterSyncError as exc:
                roster_sync = {"error": str(exc)}

    team_names = {t.get("id"): (t.get("n") or t.get("name") or "").strip() for t in body.competition_teams}
    player_names = {p.get("id"): p.get("name") for p in body.players}
    player_roles = {p.get("id"): fc.FC_ROLES.get(p.get("fcrle")) for p in body.players}
    matches, pair_warnings = fc.pair_day_lineups(body.day, body.lineups)
    rows, warnings, pairings = fc.lineup_rows(matches, team_names, player_names, player_roles)
    with get_db() as conn:
        _check_league(conn, league_id)
        result = save_lineups(conn, league_id, matchday, rows, pair_warnings + warnings, pairings)
    return {**result, "roster_sync": roster_sync}
