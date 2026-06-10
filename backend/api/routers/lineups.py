from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin

router = APIRouter(tags=["lineups"])

_MANAGER_ALIASES = {"manager", "allenatore", "fantamanager"}
_PLAYER_ALIASES = {"giocatore", "calciatore", "nome", "player"}
_STARTER_ALIASES = {"titolare", "titular", "is_starter"}


def _find_columns(headers: list) -> dict:
    cols = {}
    for i, h in enumerate(headers):
        key = str(h).strip().lower() if h is not None else ""
        if key in _MANAGER_ALIASES:
            cols.setdefault("manager", i)
        elif key in _PLAYER_ALIASES:
            cols.setdefault("player", i)
        elif key in _STARTER_ALIASES:
            cols.setdefault("is_starter", i)
    for required in ("manager", "player", "is_starter"):
        if required not in cols:
            raise ValueError(f"Colonna obbligatoria mancante: {required}")
    return cols


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(float(str(val))) if val not in (None, "") else default
    except (ValueError, TypeError):
        return default


def _parse_excel(data: bytes) -> tuple[list[dict], list[str]]:
    import openpyxl

    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    ws = wb.active

    cols = None
    rows = []
    skipped = 0

    for raw_row in ws.iter_rows(values_only=True):
        if all(v is None for v in raw_row):
            continue

        cells = [str(c).strip() if c is not None else "" for c in raw_row]

        if cols is None:
            try:
                cols = _find_columns(cells)
            except ValueError:
                continue
            continue

        manager = cells[cols["manager"]]
        player = cells[cols["player"]]

        if not manager or not player:
            skipped += 1
            continue

        is_starter = _safe_int(cells[cols["is_starter"]], default=1)
        rows.append({"manager": manager, "player": player, "is_starter": is_starter})

    if cols is None:
        raise ValueError(
            "Header non trovato: colonne obbligatorie (manager, giocatore, titolare) non trovate"
        )

    warnings = []
    if skipped:
        warnings.append(f"{skipped} righe saltate (manager o giocatore vuoti)")

    return rows, warnings


def _require_league(conn, league_id: int):
    row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


# ── Admin endpoint ───────────────────────────────────────────────────────────

@router.post("/admin/league/{league_id}/lineups/{matchday}")
async def upload_lineups(
    league_id: int,
    matchday: int,
    file: UploadFile,
    _: str = Depends(get_current_admin),
):
    data = await file.read()
    try:
        rows, warnings = _parse_excel(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="File Excel non valido o corrotto")

    locked_at = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        _require_league(conn, league_id)

        # Build lookup: name.lower() -> player_current_id per i giocatori della lega
        players = conn.execute(
            "SELECT id, name, manager_id FROM player_current WHERE league_id = ?",
            (league_id,),
        ).fetchall()
        player_map: dict[str, dict] = {
            p["name"].strip().lower(): {"id": p["id"], "manager_id": p["manager_id"]}
            for p in players
        }

        # Build lookup: name.lower() -> manager_id
        managers = conn.execute(
            "SELECT id, name FROM manager WHERE league_id = ?", (league_id,)
        ).fetchall()
        manager_map: dict[str, int] = {
            m["name"].strip().lower(): m["id"] for m in managers
        }

        # Idempotent: cancella lineup esistente per questa giornata
        conn.execute(
            "DELETE FROM lineup WHERE league_id = ? AND matchday = ?",
            (league_id, matchday),
        )

        managers_imported: set[int] = set()
        to_insert = []

        for row in rows:
            manager_name_key = row["manager"].strip().lower()
            player_name_key = row["player"].strip().lower()

            manager_id = manager_map.get(manager_name_key)
            if manager_id is None:
                warnings.append(
                    f"Manager '{row['manager']}' non trovato nella lega — riga saltata"
                )
                continue

            player_info = player_map.get(player_name_key)
            if player_info is None:
                warnings.append(
                    f"Giocatore '{row['player']}' non trovato nella rosa di {row['manager']} — saltato"
                )
                continue

            to_insert.append((league_id, manager_id, matchday, player_info["id"], row["is_starter"], locked_at))
            managers_imported.add(manager_id)

        conn.executemany(
            "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter, locked_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            to_insert,
        )

    return {
        "matchday": matchday,
        "managers_imported": len(managers_imported),
        "warnings": warnings,
    }


# ── Public endpoint ──────────────────────────────────────────────────────────

@router.get("/league/{league_id}/lineups/{matchday}")
def get_lineups(league_id: int, matchday: int):
    with get_db() as conn:
        _require_league(conn, league_id)

        rows = conn.execute(
            """
            SELECT l.id, l.manager_id, m.name AS manager_name,
                   l.player_current_id, p.name AS player_name, p.role,
                   l.is_starter, l.locked_at
            FROM lineup l
            JOIN manager m ON m.id = l.manager_id
            JOIN player_current p ON p.id = l.player_current_id
            WHERE l.league_id = ? AND l.matchday = ?
            ORDER BY m.name, l.is_starter DESC, p.role, p.name
            """,
            (league_id, matchday),
        ).fetchall()

    return [dict(r) for r in rows]
