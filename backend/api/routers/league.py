import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from api.db import get_db
from api.routers.auth import get_current_admin

router = APIRouter(tags=["league"])

SEASON_RE = re.compile(r"^\d{4}/\d{2}$")


def _validate_season(v: str) -> str:
    if not SEASON_RE.match(v):
        raise ValueError("Il formato stagione deve essere YYYY/YY (es. 2024/25)")
    return v


class LeagueCreate(BaseModel):
    name: str
    season_current: str
    season_historic: str
    budget: int = 500

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


class LeagueUpdate(BaseModel):
    name: Optional[str] = None
    season_current: Optional[str] = None
    season_historic: Optional[str] = None
    budget: Optional[int] = None

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


def _league_row_to_dict(row) -> dict:
    return dict(row)


# ── Endpoints pubblici ──────────────────────────────────────────────────────

@router.get("/league")
def list_leagues():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, season_current, season_historic FROM league ORDER BY id"
        ).fetchall()
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
            "INSERT INTO league (name, season_current, season_historic, budget) VALUES (?, ?, ?, ?)",
            (body.name, body.season_current, body.season_historic, body.budget),
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
               SET name = ?, season_current = ?, season_historic = ?, budget = ?
               WHERE id = ?""",
            (
                body.name or current["name"],
                new_season_current,
                new_season_historic,
                body.budget if body.budget is not None else current["budget"],
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
