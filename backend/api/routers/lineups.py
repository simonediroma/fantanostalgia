import re
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin

router = APIRouter(tags=["lineups"])

_MANAGER_ALIASES = {"manager", "allenatore", "fantamanager"}
_PLAYER_ALIASES = {"giocatore", "calciatore", "nome", "player"}
_STARTER_ALIASES = {"titolare", "titular", "is_starter"}

_ROLE_SET = frozenset({"p", "d", "c", "a"})
_SCORE_RE = re.compile(r"^\d+-\d+$")


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


def _is_formazioni_format(all_rows: list) -> bool:
    """Detect the real Formazioni format: match header rows with score in col 5."""
    for row in all_rows:
        if len(row) > 6:
            cells = [str(c).strip() if c is not None else "" for c in row]
            if cells[0] and cells[6] and _SCORE_RE.match(cells[5]):
                return True
    return False


def _parse_formazioni_rows(all_rows: list) -> tuple[list[dict], list[str]]:
    """
    Parse the real Formazioni Excel format.
    Two matches side by side: left team cols 0-4, right team cols 6-10.
    Match header row: team_left in col 0, score in col 5, team_right in col 6.
    'Panchina' row separates starters from bench.
    'TOTALE:...' row marks end of each team's data.
    """
    rows_out = []

    left_team = right_team = None
    left_starter = right_starter = True
    left_done = right_done = False

    for raw_row in all_rows:
        if all(v is None for v in raw_row):
            continue

        cells = [str(c).strip() if c is not None else "" for c in raw_row]

        # Match header: score pattern in col 5, team names in cols 0 and 6
        if len(cells) > 6 and cells[0] and cells[6] and _SCORE_RE.match(cells[5]):
            left_team = cells[0]
            right_team = cells[6]
            left_starter = right_starter = True
            left_done = right_done = False
            continue

        if left_team is None:
            continue

        left_val = cells[0]
        right_val = cells[6] if len(cells) > 6 else ""

        # Panchina toggles is_starter for each side independently
        if left_val.lower() == "panchina":
            left_starter = False
        if right_val.lower() == "panchina":
            right_starter = False

        # TOTALE marks end of team block
        if left_val.lower().startswith("totale"):
            left_done = True
        if right_val.lower().startswith("totale"):
            right_done = True

        # Left player
        if not left_done and left_val.lower() in _ROLE_SET:
            player_left = cells[1] if len(cells) > 1 else ""
            if player_left:
                rows_out.append({
                    "manager": left_team,
                    "player": player_left,
                    "is_starter": 1 if left_starter else 0,
                })

        # Right player
        if not right_done and right_val.lower() in _ROLE_SET:
            player_right = cells[7] if len(cells) > 7 else ""
            if player_right:
                rows_out.append({
                    "manager": right_team,
                    "player": player_right,
                    "is_starter": 1 if right_starter else 0,
                })

    return rows_out, []


def _parse_flat_rows(all_rows: list) -> tuple[list[dict], list[str]]:
    """Parse the flat format with manager/player/is_starter header columns."""
    cols = None
    rows_out = []
    skipped = 0

    for raw_row in all_rows:
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
        rows_out.append({"manager": manager, "player": player, "is_starter": is_starter})

    if cols is None:
        raise ValueError(
            "Header non trovato: colonne obbligatorie (manager, giocatore, titolare) non trovate"
        )

    warnings = []
    if skipped:
        warnings.append(f"{skipped} righe saltate (manager o giocatore vuoti)")

    return rows_out, warnings


def _parse_excel(data: bytes) -> tuple[list[dict], list[str]]:
    import openpyxl

    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))

    if _is_formazioni_format(all_rows):
        return _parse_formazioni_rows(all_rows)
    return _parse_flat_rows(all_rows)


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

        # Build lookup: manager name or team_name (case-insensitive) -> manager_id
        managers = conn.execute(
            "SELECT id, name, team_name FROM manager WHERE league_id = ?", (league_id,)
        ).fetchall()
        manager_map: dict[str, int] = {}
        for m in managers:
            manager_map[m["name"].strip().lower()] = m["id"]
            manager_map[m["team_name"].strip().lower()] = m["id"]

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
