from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.db import get_db
from backend.api.notifications import enqueue_email
from backend.api.routers.auth import get_current_admin, get_current_user
from backend.api.routers.coach import _get_manager_for_user
from backend.engine import market as market_engine
from backend.engine.granpremio import free_historic_players

router = APIRouter(tags=["market"])


def _require_league(conn, league_id: int) -> None:
    row = conn.execute("SELECT id FROM league WHERE id = ?", (league_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lega non trovata")


def _get_session_or_404(conn, league_id: int, market_session_id: int):
    row = conn.execute(
        "SELECT id, league_id, status, created_at, cuts_closed_at, resolved_at"
        " FROM market_session WHERE id = ?",
        (market_session_id,),
    ).fetchone()
    if row is None or row["league_id"] != league_id:
        raise HTTPException(status_code=404, detail="Sessione di mercato non trovata")
    return row


def _listing_rows(conn, market_session_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT ph.id AS player_historic_id, ph.name, ph.role, ph.team, ph.season,
               ROUND(AVG(hr.rating), 2) AS avg_rating
        FROM market_listing ml
        JOIN player_historic ph ON ph.id = ml.player_historic_id
        LEFT JOIN historic_rating hr ON hr.player_historic_id = ph.id
        WHERE ml.market_session_id = ?
        GROUP BY ph.id
        ORDER BY CASE ph.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                 ph.team, AVG(hr.rating) DESC
        """,
        (market_session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _latest_session(conn, league_id: int):
    return conn.execute(
        "SELECT id, status FROM market_session WHERE league_id = ? ORDER BY id DESC LIMIT 1",
        (league_id,),
    ).fetchone()


# ── Admin ────────────────────────────────────────────────────────────────────


@router.get("/admin/league/{league_id}/market/free-players")
def list_free_players(
    league_id: int,
    role: str | None = None,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        try:
            return free_historic_players(conn, league_id, role)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


class CreateMarketSession(BaseModel):
    player_historic_ids: list[int]


@router.post("/admin/league/{league_id}/market")
def create_market(
    league_id: int,
    body: CreateMarketSession,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        try:
            session_id = market_engine.create_market_session(
                conn, league_id, body.player_historic_ids
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        listing = _listing_rows(conn, session_id)

    return {"id": session_id, "status": "cuts_open", "listing": listing}


@router.get("/admin/league/{league_id}/market/current")
def get_current_market(
    league_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        session = _latest_session(conn, league_id)
        if session is None:
            return None

        listing = _listing_rows(conn, session["id"])
        result = {"id": session["id"], "status": session["status"], "listing": listing}

        if session["status"] == "bids_open":
            counts = conn.execute(
                "SELECT player_historic_id, COUNT(*) AS n FROM market_bid"
                " WHERE market_session_id = ? AND status = 'pending' GROUP BY player_historic_id",
                (session["id"],),
            ).fetchall()
            bid_counts = {r["player_historic_id"]: r["n"] for r in counts}
            for row in result["listing"]:
                row["bid_count"] = bid_counts.get(row["player_historic_id"], 0)
        elif session["status"] == "resolved":
            outcomes = conn.execute(
                """
                SELECT mb.player_historic_id, mb.manager_id, mb.amount, m.name AS manager_name
                FROM market_bid mb
                JOIN manager m ON m.id = mb.manager_id
                WHERE mb.market_session_id = ? AND mb.status = 'won'
                """,
                (session["id"],),
            ).fetchall()
            by_player = {r["player_historic_id"]: dict(r) for r in outcomes}
            for row in result["listing"]:
                winner = by_player.get(row["player_historic_id"])
                row["winner_manager_id"] = winner["manager_id"] if winner else None
                row["winner_name"] = winner["manager_name"] if winner else None
                row["amount"] = winner["amount"] if winner else None

    return result


@router.post("/admin/league/{league_id}/market/{market_session_id}/close-cuts")
def close_cuts(
    league_id: int,
    market_session_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        _get_session_or_404(conn, league_id, market_session_id)
        try:
            market_engine.close_cuts(conn, market_session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"id": market_session_id, "status": "bids_open"}


@router.post("/admin/league/{league_id}/market/{market_session_id}/resolve")
def resolve_market(
    league_id: int,
    market_session_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        _get_session_or_404(conn, league_id, market_session_id)
        try:
            results = market_engine.resolve_market_session(conn, market_session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        league = conn.execute("SELECT name FROM league WHERE id = ?", (league_id,)).fetchone()

        won_by_manager: dict[int, list[str]] = {}
        for r in results:
            if r["winner_manager_id"] is not None:
                won_by_manager.setdefault(r["winner_manager_id"], []).append(r["name"])

        for manager_id, player_names in won_by_manager.items():
            manager = conn.execute(
                "SELECT name, user_id FROM manager WHERE id = ?", (manager_id,)
            ).fetchone()
            if manager["user_id"] is None:
                continue
            user = conn.execute(
                "SELECT email FROM user WHERE id = ?", (manager["user_id"],)
            ).fetchone()
            enqueue_email(conn, "market_won", user["email"], {
                "name": manager["name"], "league_name": league["name"], "league_id": league_id,
                "won_players_names": player_names,
            })

    return {"id": market_session_id, "status": "resolved", "results": results}


@router.post("/admin/league/{league_id}/market/{market_session_id}/cancel")
def cancel_market(
    league_id: int,
    market_session_id: int,
    _: str = Depends(get_current_admin),
):
    with get_db() as conn:
        _require_league(conn, league_id)
        _get_session_or_404(conn, league_id, market_session_id)
        try:
            market_engine.cancel_market_session(conn, market_session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"id": market_session_id, "status": "cancelled"}


# ── Pubblico ─────────────────────────────────────────────────────────────────


@router.get("/league/{league_id}/market")
def list_market_sessions(league_id: int):
    with get_db() as conn:
        _require_league(conn, league_id)
        sessions = conn.execute(
            "SELECT id, status, created_at, resolved_at FROM market_session"
            " WHERE league_id = ? ORDER BY id DESC",
            (league_id,),
        ).fetchall()

        result = []
        for session in sessions:
            entry = dict(session)
            if session["status"] == "resolved":
                outcomes = conn.execute(
                    """
                    SELECT mb.player_historic_id, ph.name, ph.role, mb.manager_id, mb.amount,
                           m.name AS manager_name
                    FROM market_bid mb
                    JOIN player_historic ph ON ph.id = mb.player_historic_id
                    JOIN manager m ON m.id = mb.manager_id
                    WHERE mb.market_session_id = ? AND mb.status = 'won'
                    """,
                    (session["id"],),
                ).fetchall()
                entry["results"] = [dict(r) for r in outcomes]
            else:
                entry["listing"] = _listing_rows(conn, session["id"])
            result.append(entry)

    return result


# ── Coach ────────────────────────────────────────────────────────────────────


@router.get("/coach/league/{league_id}/market")
def get_coach_market(league_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        manager_id = mgr["id"]

        session = _latest_session(conn, league_id)
        session_out = None
        listing: list[dict] = []
        my_bids: dict[int, int] = {}

        if session is not None and session["status"] in ("cuts_open", "bids_open", "resolved"):
            session_out = {"id": session["id"], "status": session["status"]}
            if session["status"] != "cuts_open":
                listing = _listing_rows(conn, session["id"])
                bid_rows = conn.execute(
                    "SELECT player_historic_id, amount FROM market_bid"
                    " WHERE market_session_id = ? AND manager_id = ? AND status = 'pending'",
                    (session["id"], manager_id),
                ).fetchall()
                my_bids = {r["player_historic_id"]: r["amount"] for r in bid_rows}
                for row in listing:
                    row["my_bid"] = my_bids.get(row["player_historic_id"])
                if session["status"] == "resolved":
                    outcomes = conn.execute(
                        "SELECT player_historic_id, manager_id, amount FROM market_bid"
                        " WHERE market_session_id = ? AND status = 'won'",
                        (session["id"],),
                    ).fetchall()
                    by_player = {r["player_historic_id"]: r for r in outcomes}
                    for row in listing:
                        winner = by_player.get(row["player_historic_id"])
                        row["winner_manager_id"] = winner["manager_id"] if winner else None
                        row["amount"] = winner["amount"] if winner else None

        pool_rows = conn.execute(
            """
            SELECT ph.id AS player_historic_id, ph.name, ph.role, ph.team, ph.season,
                   ROUND(AVG(hr.rating), 2) AS avg_rating
            FROM manager_nostalgia_pool mnp
            JOIN player_historic ph ON ph.id = mnp.player_historic_id
            LEFT JOIN historic_rating hr ON hr.player_historic_id = ph.id
            WHERE mnp.manager_id = ?
            GROUP BY ph.id
            ORDER BY CASE ph.role WHEN 'P' THEN 1 WHEN 'D' THEN 2 WHEN 'C' THEN 3 WHEN 'A' THEN 4 END,
                     ph.team, AVG(hr.rating) DESC
            """,
            (manager_id,),
        ).fetchall()
        cut_candidates = []
        for r in pool_rows:
            entry = dict(r)
            entry["cut_value"] = market_engine.compute_cut_value(conn, r["player_historic_id"])
            cut_candidates.append(entry)

        credits = conn.execute(
            "SELECT credits FROM manager WHERE id = ?", (manager_id,)
        ).fetchone()["credits"]
        free_slots = market_engine.free_slots_by_role(conn, manager_id)

    return {
        "session": session_out,
        "listing": listing,
        "cut_candidates": cut_candidates,
        "credits": credits,
        "free_slots": free_slots,
    }


class CutBody(BaseModel):
    player_historic_id: int


@router.post("/coach/league/{league_id}/market/cut")
def cut_player(league_id: int, body: CutBody, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        try:
            value = market_engine.cut_player(conn, league_id, mgr["id"], body.player_historic_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        credits = conn.execute(
            "SELECT credits FROM manager WHERE id = ?", (mgr["id"],)
        ).fetchone()["credits"]

    return {"detail": "Giocatore tagliato", "credited": value, "credits": credits}


class BidBody(BaseModel):
    player_historic_id: int
    amount: int


@router.post("/coach/league/{league_id}/market/bid")
def place_bid(league_id: int, body: BidBody, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        session = _latest_session(conn, league_id)
        if session is None:
            raise HTTPException(status_code=400, detail="Nessun mercato attivo per questa lega")
        try:
            market_engine.place_bid(
                conn, session["id"], mgr["id"], body.player_historic_id, body.amount
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"detail": "Offerta registrata"}


@router.delete("/coach/league/{league_id}/market/bid/{player_historic_id}")
def withdraw_bid(league_id: int, player_historic_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        mgr = _get_manager_for_user(conn, league_id, user["id"])
        session = _latest_session(conn, league_id)
        if session is None:
            raise HTTPException(status_code=400, detail="Nessun mercato attivo per questa lega")
        try:
            market_engine.withdraw_bid(conn, session["id"], mgr["id"], player_historic_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"detail": "Offerta ritirata"}
