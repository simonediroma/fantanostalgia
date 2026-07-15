import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin

router = APIRouter(tags=["league"])

SEASON_RE = re.compile(r"^\d{4}/\d{2}$")


class ManagerCreate(BaseModel):
    name: str
    team_name: str


class ManagerUpdate(BaseModel):
    name: Optional[str] = None
    team_name: Optional[str] = None


def _validate_season(v: str) -> str:
    if not SEASON_RE.match(v):
        raise ValueError("Il formato stagione deve essere YYYY/YY (es. 2024/25)")
    return v


class LeagueCreate(BaseModel):
    name: str
    season_current: str
    season_historic: str
    budget: int = 500
    max_manager: Optional[int] = None
    platform: Optional[str] = None

    @field_validator("season_current", "season_historic")
    @classmethod
    def validate_season_format(cls, v: str) -> str:
        return _validate_season(v)

    @model_validator(mode="after")
    def seasons_must_differ(self) -> "LeagueCreate":
        if self.season_current == self.season_historic:
            raise ValueError("season_current e season_historic devono essere diverse")
        return self

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: int) -> int:
        if v < 100:
            raise ValueError("Il budget deve essere almeno 100")
        return v

    @field_validator("max_manager")
    @classmethod
    def validate_max_manager(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Il numero massimo di manager deve essere almeno 1")
        return v


class LeagueUpdate(BaseModel):
    name: Optional[str] = None
    season_current: Optional[str] = None
    season_historic: Optional[str] = None
    budget: Optional[int] = None
    max_manager: Optional[int] = None
    platform: Optional[str] = None

    @field_validator("season_current", "season_historic")
    @classmethod
    def validate_season_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_season(v)
        return v

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 100:
            raise ValueError("Il budget deve essere almeno 100")
        return v

    @field_validator("max_manager")
    @classmethod
    def validate_max_manager(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Il numero massimo di manager deve essere almeno 1")
        return v


def _league_row_to_dict(row) -> dict:
    return dict(row)


# ── Endpoints pubblici ──────────────────────────────────────────────────────

@router.get("/league")
def list_leagues():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM league ORDER BY id").fetchall()
    return [_league_row_to_dict(r) for r in rows]


@router.get("/league/{league_id}")
def get_league(league_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")
    return _league_row_to_dict(row)


# ── Endpoints admin (protetti) ──────────────────────────────────────────────

@router.post("/admin/league", status_code=201)
def create_league(body: LeagueCreate, _: str = Depends(get_current_admin)):
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO league (name, season_current, season_historic, budget, max_manager, platform)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (body.name, body.season_current, body.season_historic, body.budget, body.max_manager, body.platform),
        )
        league_id = cur.lastrowid
        row = conn.execute("SELECT * FROM league WHERE id = ?", (league_id,)).fetchone()
    return _league_row_to_dict(row)


@router.put("/admin/league/{league_id}")
def update_league(league_id: int, body: LeagueUpdate, _: str = Depends(get_current_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM league WHERE id = ?", (league_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Lega non trovata")

        current = _league_row_to_dict(row)
        new_season_current = body.season_current or current["season_current"]
        new_season_historic = body.season_historic or current["season_historic"]

        if new_season_current == new_season_historic:
            raise HTTPException(
                status_code=422, detail="season_current e season_historic devono essere diverse"
            )

        conn.execute(
            """UPDATE league
               SET name = ?, season_current = ?, season_historic = ?, budget = ?, max_manager = ?, platform = ?
               WHERE id = ?""",
            (
                body.name or current["name"],
                new_season_current,
                new_season_historic,
                body.budget if body.budget is not None else current["budget"],
                body.max_manager if body.max_manager is not None else current["max_manager"],
                body.platform if body.platform is not None else current["platform"],
                league_id,
            ),
        )
        row = conn.execute("SELECT * FROM league WHERE id = ?", (league_id,)).fetchone()
    return _league_row_to_dict(row)


@router.delete("/admin/league/{league_id}", status_code=204)
def delete_league(league_id: int, _: str = Depends(get_current_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Lega non trovata")
        conn.execute("DELETE FROM league WHERE id = ?", (league_id,))


# ── Manager endpoints ───────────────────────────────────────────────────────

@router.get("/league/{league_id}/managers")
def list_managers(league_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Lega non trovata")
        rows = conn.execute(
            """
            SELECT m.id, m.name, m.team_name,
                   CASE WHEN m.user_id IS NOT NULL THEN 1 ELSE 0 END AS user_linked,
                   COALESCE(m.assignments_locked, 0) AS assignments_locked
            FROM manager m
            WHERE m.league_id = ?
            ORDER BY m.name
            """,
            (league_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.put("/admin/league/{league_id}/managers/{manager_id}")
def update_manager(
    league_id: int,
    manager_id: int,
    body: ManagerUpdate,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM manager WHERE id = ? AND league_id = ?", (manager_id, league_id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Manager non trovato")
        current = dict(row)
        conn.execute(
            "UPDATE manager SET name = ?, team_name = ? WHERE id = ?",
            (
                body.name if body.name is not None else current["name"],
                body.team_name if body.team_name is not None else current["team_name"],
                manager_id,
            ),
        )
        updated = conn.execute("SELECT id, name, team_name FROM manager WHERE id = ?", (manager_id,)).fetchone()
    return dict(updated)


@router.post("/admin/league/{league_id}/managers", status_code=201)
def create_manager(
    league_id: int,
    body: ManagerCreate,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        row = conn.execute("SELECT id, max_manager FROM league WHERE id = ?", (league_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Lega non trovata")
        if row["max_manager"] is not None:
            count = conn.execute(
                "SELECT COUNT(*) FROM manager WHERE league_id = ?", (league_id,)
            ).fetchone()[0]
            if count >= row["max_manager"]:
                raise HTTPException(status_code=422, detail="Numero massimo di manager raggiunto")
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, body.name, body.team_name),
        )
        mid = cur.lastrowid
        manager_row = conn.execute("SELECT * FROM manager WHERE id = ?", (mid,)).fetchone()
    return dict(manager_row)


@router.post("/admin/league/{league_id}/managers/{manager_id}/invite")
def create_invite(
    league_id: int,
    manager_id: int,
    request: Request,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        mgr = conn.execute(
            "SELECT id FROM manager WHERE id = ? AND league_id = ?",
            (manager_id, league_id),
        ).fetchone()
        if mgr is None:
            raise HTTPException(status_code=404, detail="Manager non trovato")

        token = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO league_invite (league_id, manager_id, token) VALUES (?, ?, ?)",
            (league_id, manager_id, token),
        )

    base_url = str(request.base_url).rstrip("/")
    return {"token": token, "join_url": f"{base_url}/coach/join?token={token}"}
