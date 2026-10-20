import re
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.api.db import get_db
from backend.api.routers.auth import get_current_admin
from backend.engine.scoring import freeze_lineup_alter_egos

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


def _safe_float(val) -> float | None:
    """Return float or None for '-' / empty (SV)."""
    if val is None or str(val).strip() in ("", "-"):
        return None
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None


# Formazioni layouts: column of the match score, offset of the right team,
# columns (relative to the team block) of player name, voto no bonus, voto con bonus.
# Old export: Ruolo | Calciatore | vuota | Voto_no_bonus | Voto_con_bonus.
# New export (2026-10): Ruolo | Calciatore | vuota | Sq. | V | FV | G | GS | ... (17 cols),
# V = voto in pagella, FV = fantavoto (same meaning as scr/cscr of the Fantacalcio import).
_FORMAZIONI_LAYOUTS = (
    {"score": 5, "right": 6, "name": 1, "no_bonus": 3, "bonus": 4},
    {"score": 17, "right": 18, "name": 1, "no_bonus": 4, "bonus": 5},
)


def _formazioni_layout(all_rows: list) -> dict | None:
    """Detect a Formazioni format: match header rows with the score between the two teams."""
    for row in all_rows:
        cells = [str(c).strip() if c is not None else "" for c in row]
        for layout in _FORMAZIONI_LAYOUTS:
            if (len(cells) > layout["right"] and cells[0] and cells[layout["right"]]
                    and _SCORE_RE.match(cells[layout["score"]])):
                return layout
    return None


def _parse_formazioni_rows(all_rows: list, layout: dict = _FORMAZIONI_LAYOUTS[0]) -> tuple[list[dict], list[str], list[tuple[str, str]]]:
    """
    Parse the real Formazioni Excel format.
    Two matches side by side: left team from col 0, right team from col layout["right"].
    Match header row: team_left in col 0, score in col layout["score"], team_right in col layout["right"].
    'Panchina' row separates starters from bench.
    'TOTALE:...' row marks end of each team's data (old export only; the new one
    ends each block at the next match header).
    Also returns pairings as list of (left_team, right_team).
    """
    sc, rt = layout["score"], layout["right"]
    rows_out = []
    pairings: list[tuple[str, str]] = []

    left_team = right_team = None
    left_starter = right_starter = True
    left_done = right_done = False

    for raw_row in all_rows:
        if all(v is None for v in raw_row):
            continue

        cells = [str(c).strip() if c is not None else "" for c in raw_row]

        # Match header: score pattern in col 5, team names in cols 0 and 6
        if len(cells) > rt and cells[0] and cells[rt] and _SCORE_RE.match(cells[sc]):
            left_team = cells[0]
            right_team = cells[rt]
            pairings.append((left_team, right_team))
            left_starter = right_starter = True
            left_done = right_done = False
            continue

        if left_team is None:
            continue

        left_val = cells[0]
        right_val = cells[rt] if len(cells) > rt else ""

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

        for base, val, done, starter, team in (
            (0, left_val, left_done, left_starter, left_team),
            (rt, right_val, right_done, right_starter, right_team),
        ):
            if done or val.lower() not in _ROLE_SET:
                continue
            col = lambda k: cells[base + layout[k]] if len(cells) > base + layout[k] else None
            player = col("name") or ""
            if player:
                rows_out.append({
                    "manager": team,
                    "player": player,
                    "is_starter": 1 if starter else 0,
                    "score_no_bonus": _safe_float(col("no_bonus")),
                    "score_bonus": _safe_float(col("bonus")),
                })

    return rows_out, [], pairings


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


def _parse_excel(data: bytes) -> tuple[list[dict], list[str], list[tuple[str, str]]]:
    import openpyxl

    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))

    layout = _formazioni_layout(all_rows)
    if layout:
        return _parse_formazioni_rows(all_rows, layout)
    rows, warnings = _parse_flat_rows(all_rows)
    return rows, warnings, []


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
        rows, warnings, pairings = _parse_excel(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="File Excel non valido o corrotto")

    with get_db() as conn:
        return save_lineups(conn, league_id, matchday, rows, warnings, pairings)


def save_lineups(conn, league_id: int, matchday: int, rows: list[dict],
                 warnings: list[str], pairings: list[tuple[str, str]]) -> dict:
    """Sostituisce formazioni e scontri diretti di una giornata. Condiviso tra
    upload Excel e import da Leghe Fantacalcio. Righe: manager, player,
    is_starter, score_no_bonus, score_bonus."""
    locked_at = datetime.now(timezone.utc).isoformat()
    _require_league(conn, league_id)

    resolved_gp = conn.execute(
        "SELECT COUNT(*) AS c FROM gran_premio"
        " WHERE league_id = ? AND matchday = ? AND status = 'resolved'",
        (league_id, matchday),
    ).fetchone()["c"]
    if resolved_gp:
        raise HTTPException(
            status_code=400,
            detail="Impossibile ricaricare le formazioni: un Gran Premio è già stato assegnato per questa giornata",
        )

    # Build lookup: name.lower() -> player_current_id per i giocatori della lega
    players = conn.execute(
        "SELECT id, name, manager_id, fc_id FROM player_current WHERE league_id = ?",
        (league_id,),
    ).fetchall()
    player_map: dict[str, dict] = {
        p["name"].strip().lower(): {"id": p["id"], "manager_id": p["manager_id"]}
        for p in players
    }
    fc_map = {p["fc_id"]: {"id": p["id"], "manager_id": p["manager_id"]}
              for p in players if p["fc_id"] is not None}

    # Avvisi "non in rosa" solo per la giornata più recente: le formazioni passate
    # contengono legittimamente giocatori poi ceduti.
    last = conn.execute("SELECT MAX(matchday) AS m FROM lineup WHERE league_id = ?",
                        (league_id,)).fetchone()["m"]
    is_current = last is None or matchday >= last
    # Alter ego già congelati per questa giornata: un reimport non riscrive lo storico
    frozen = {
        r["player_current_id"]: r["alter_ego_id"]
        for r in conn.execute(
            "SELECT player_current_id, alter_ego_id FROM lineup"
            " WHERE league_id = ? AND matchday = ? AND alter_ego_frozen = 1",
            (league_id, matchday),
        )
    }

    # Build lookup: team_name (pivot) or manager name (case-insensitive) -> manager_id.
    # Il nome squadra vince sempre: il nome di un manager non può "rubare" la squadra di un altro.
    managers = conn.execute(
        "SELECT id, name, team_name FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()
    manager_map: dict[str, int] = {}
    for m in managers:
        manager_map[m["name"].strip().lower()] = m["id"]
    for m in managers:
        if (m["team_name"] or "").strip():
            manager_map[m["team_name"].strip().lower()] = m["id"]
    team_label = {m["id"]: (m["team_name"] or m["name"]).strip() for m in managers}

    # Idempotent: cancella lineup e pairings esistenti per questa giornata
    conn.execute(
        "DELETE FROM lineup WHERE league_id = ? AND matchday = ?",
        (league_id, matchday),
    )
    conn.execute(
        "DELETE FROM h2h_match WHERE league_id = ? AND matchday = ?",
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

        player_info = fc_map.get(row.get("fc_id")) or player_map.get(player_name_key)
        if player_info is None and row.get("role"):
            # Import Fantacalcio: giocatore assente dall'anagrafica → lo crea senza squadra.
            # La rosa la decide solo la sync rose.
            cur = conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, manager_id, fc_id)"
                " VALUES (?, ?, ?, '', NULL, ?)",
                (league_id, row["player"].strip(), row["role"], row.get("fc_id")),
            )
            player_info = {"id": cur.lastrowid, "manager_id": None}
            player_map[player_name_key] = player_info
        if player_info is None:
            warnings.append(
                f"Giocatore '{row['player']}' non trovato nella rosa di {row['manager']} — saltato"
            )
            continue

        owner_id = player_info["manager_id"]
        if is_current and owner_id != manager_id:
            warnings.append(
                f"{row['player']} schierato da {team_label[manager_id]} ma non nella sua rosa"
                + (f" (in rosa a {team_label.get(owner_id, owner_id)})" if owner_id else "")
                + ": rilancia la sync rose"
            )

        pcid = player_info["id"]
        to_insert.append((
            league_id, manager_id, matchday, pcid,
            row["is_starter"],
            row.get("score_no_bonus"),
            row.get("score_bonus"),
            locked_at,
            frozen.get(pcid), 1 if pcid in frozen else 0,
        ))
        managers_imported.add(manager_id)

    conn.executemany(
        "INSERT INTO lineup"
        " (league_id, manager_id, matchday, player_current_id, is_starter,"
        "  score_no_bonus, score_bonus, locked_at, alter_ego_id, alter_ego_frozen)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        to_insert,
    )

    freeze_lineup_alter_egos(conn, league_id, matchday)

    # Salva scontri diretti (pairings)
    for left_name, right_name in pairings:
        home_id = manager_map.get(left_name.strip().lower())
        away_id = manager_map.get(right_name.strip().lower())
        if home_id is not None and away_id is not None:
            conn.execute(
                "INSERT OR IGNORE INTO h2h_match (league_id, matchday, manager_home_id, manager_away_id)"
                " VALUES (?, ?, ?, ?)",
                (league_id, matchday, home_id, away_id),
            )
        else:
            warnings.append(
                f"Scontro diretto '{left_name}' vs '{right_name}': manager non trovato — pairing saltato"
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
            ORDER BY m.name, l.is_starter DESC,
                     CASE p.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                     p.name
            """,
            (league_id, matchday),
        ).fetchall()

    return [dict(r) for r in rows]
