from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.db import get_db
from backend.api.routers.auth import get_current_user
from backend.engine.mapping import _flush_alter_ego_for_manager

router = APIRouter(prefix="/coach", tags=["coach"])


def _get_manager_for_user(conn, league_id: int, user_id: int) -> dict:
    row = conn.execute(
        """
        SELECT m.id, m.name, m.team_name,
               COALESCE(m.assignments_locked, 0) AS assignments_locked,
               l.id AS league_id, l.name AS league_name,
               COALESCE(l.associations_closed, 0) AS associations_closed
        FROM manager m
        JOIN league l ON l.id = m.league_id
        WHERE m.league_id = ? AND m.user_id = ?
        """,
        (league_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=403,
            detail="Non sei un manager di questa lega",
        )
    return dict(row)


@router.get("/league/{league_id}/rosa")
def get_rosa(league_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        manager_id = mgr["id"]

        nostalgia_rows = conn.execute(
            """
            SELECT mnp.player_historic_id, ph.name, ph.role, ph.team, ph.season,
                   mnp.assigned_player_current_id,
                   pc.name AS assigned_to_player_current_name
            FROM manager_nostalgia_pool mnp
            JOIN player_historic ph ON ph.id = mnp.player_historic_id
            LEFT JOIN player_current pc ON pc.id = mnp.assigned_player_current_id
            WHERE mnp.manager_id = ?
            ORDER BY
                CASE ph.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                ph.name
            """,
            (manager_id,),
        ).fetchall()

        assigned_pc_ids = {
            r["assigned_player_current_id"]
            for r in nostalgia_rows
            if r["assigned_player_current_id"] is not None
        }

        current_rows = conn.execute(
            """
            SELECT id, name, role, team, starts_current_season
            FROM player_current
            WHERE league_id = ? AND manager_id = ?
            ORDER BY
                CASE role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                starts_current_season DESC, name
            """,
            (league_id, manager_id),
        ).fetchall()

    return {
        "manager": {
            "id": mgr["id"],
            "name": mgr["name"],
            "team_name": mgr["team_name"],
            "assignments_locked": bool(mgr["assignments_locked"]),
        },
        "league": {
            "id": mgr["league_id"],
            "name": mgr["league_name"],
            "associations_closed": bool(mgr["associations_closed"]),
        },
        "nostalgia_pool": [
            {
                "player_historic_id": r["player_historic_id"],
                "name": r["name"],
                "role": r["role"],
                "team": r["team"],
                "season": r["season"],
                "assigned_to_player_current_id": r["assigned_player_current_id"],
                "assigned_to_player_current_name": r["assigned_to_player_current_name"],
            }
            for r in nostalgia_rows
        ],
        "current_players": [
            {
                "id": r["id"],
                "name": r["name"],
                "role": r["role"],
                "team": r["team"],
                "starts_current_season": r["starts_current_season"],
                "has_nostalgia_assignment": r["id"] in assigned_pc_ids,
            }
            for r in current_rows
        ],
    }


class AssignBody(BaseModel):
    player_historic_id: int
    player_current_id: int | None


@router.post("/league/{league_id}/assign")
def assign_player(
    league_id: int,
    body: AssignBody,
    user: dict = Depends(get_current_user),
):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        manager_id = mgr["id"]

        if mgr["assignments_locked"]:
            raise HTTPException(status_code=400, detail="Associazioni già bloccate")
        if mgr["associations_closed"]:
            raise HTTPException(status_code=400, detail="Il periodo di associazioni è chiuso")

        pool_entry = conn.execute(
            """
            SELECT mnp.id, ph.role
            FROM manager_nostalgia_pool mnp
            JOIN player_historic ph ON ph.id = mnp.player_historic_id
            WHERE mnp.manager_id = ? AND mnp.player_historic_id = ?
            """,
            (manager_id, body.player_historic_id),
        ).fetchone()
        if pool_entry is None:
            raise HTTPException(
                status_code=400,
                detail="Giocatore nostalgia non nel tuo pool",
            )

        if body.player_current_id is not None:
            pc = conn.execute(
                "SELECT id, role FROM player_current WHERE id = ? AND manager_id = ? AND league_id = ?",
                (body.player_current_id, manager_id, league_id),
            ).fetchone()
            if pc is None:
                raise HTTPException(
                    status_code=400,
                    detail="Giocatore reale non nella tua rosa",
                )
            if pc["role"] != pool_entry["role"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ruolo non compatibile: nostalgia è {pool_entry['role']}, reale è {pc['role']}",
                )
            conflict = conn.execute(
                """
                SELECT id FROM manager_nostalgia_pool
                WHERE manager_id = ? AND assigned_player_current_id = ? AND player_historic_id != ?
                """,
                (manager_id, body.player_current_id, body.player_historic_id),
            ).fetchone()
            if conflict is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Questo giocatore reale è già assegnato a un altro giocatore nostalgia",
                )

        conn.execute(
            "UPDATE manager_nostalgia_pool SET assigned_player_current_id = ? WHERE id = ?",
            (body.player_current_id, pool_entry["id"]),
        )

    return {"detail": "Associazione aggiornata"}


@router.post("/league/{league_id}/lock")
def lock_assignments(league_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        manager_id = mgr["id"]

        if mgr["assignments_locked"]:
            raise HTTPException(status_code=400, detail="Associazioni già bloccate")
        if mgr["associations_closed"]:
            raise HTTPException(status_code=400, detail="Il periodo di associazioni è chiuso")

        pool_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM manager_nostalgia_pool WHERE manager_id = ?",
            (manager_id,),
        ).fetchone()["cnt"]
        assigned_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM manager_nostalgia_pool WHERE manager_id = ? AND assigned_player_current_id IS NOT NULL",
            (manager_id,),
        ).fetchone()["cnt"]

        if pool_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Il pool nostalgia non è ancora stato assegnato dall'amministratore",
            )
        if assigned_count < pool_count:
            raise HTTPException(
                status_code=400,
                detail=f"Devi assegnare tutti i giocatori nostalgia ({assigned_count}/{pool_count} assegnati)",
            )

        _flush_alter_ego_for_manager(conn, league_id, manager_id)
        conn.execute(
            "UPDATE manager SET assignments_locked = 1 WHERE id = ?", (manager_id,)
        )

    return {"detail": "Associazioni bloccate con successo"}
