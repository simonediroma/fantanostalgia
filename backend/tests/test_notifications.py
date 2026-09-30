import json

import pytest

from backend.api import notifications
from backend.api.db import get_db


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")
    client.post("/auth/user/logout")


def _queue_rows_for(conn, to_email: str):
    """Filtra per destinatario, non per template: la fixture `client` è
    session-scoped e condivisa con l'intera suite (es. test_elevation.py
    registra più coach), quindi un conteggio per template soltanto
    catturerebbe anche righe accodate da altri test/file."""
    return conn.execute(
        "SELECT * FROM email_queue WHERE to_email = ? ORDER BY id", (to_email,)
    ).fetchall()


def _create_league(client, name="NotifLega", season_historic="2003/04") -> int:
    r = client.post("/admin/league", json={
        "name": name, "season_current": "2024/25", "season_historic": season_historic, "budget": 500,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _create_manager_and_invite(client, league_id: int, name="Mario") -> tuple[int, str]:
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": name, "team_name": f"{name} FC"}
    ).json()
    invite = client.post(f"/admin/league/{league_id}/managers/{manager['id']}/invite").json()
    return manager["id"], invite["token"]


def _link_user(conn, manager_id: int, email: str, name="Coach") -> int:
    user_id = conn.execute(
        "INSERT INTO user (email, name, password_hash) VALUES (?, ?, 'x')", (email, name)
    ).lastrowid
    conn.execute("UPDATE manager SET user_id = ? WHERE id = ?", (user_id, manager_id))
    return user_id


def _drain_queue() -> None:
    """La fixture `client` è session-scoped (DB condiviso con l'intera suite):
    prima dei test sul processore di coda, svuota qualunque riga 'pending'
    lasciata da test precedenti (in questo file o in altri) per isolamento."""
    with get_db() as conn:
        conn.execute("UPDATE email_queue SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE status = 'pending'")


# ── Registrazione ────────────────────────────────────────────────────────────

def test_registration_enqueues_welcome_email(client):
    league_id = _create_league(client)
    _, token = _create_manager_and_invite(client, league_id)
    client.post("/auth/logout")

    r = client.post("/auth/register", json={
        "name": "Mario", "email": "mario@test.com", "password": "pass1234", "invite_token": token,
    })
    assert r.status_code == 201

    with get_db() as conn:
        rows = _queue_rows_for(conn, "mario@test.com")
    assert len(rows) == 1
    assert rows[0]["template"] == "registration"
    assert rows[0]["status"] == "pending"
    assert json.loads(rows[0]["params"]) == {"name": "Mario", "league_name": "NotifLega"}


# ── Invito via email ──────────────────────────────────────────────────────────

def test_invite_with_email_enqueues_invite(client):
    league_id = _create_league(client, name="InvitoLega")
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "Gino", "team_name": "Gino FC"}
    ).json()
    r = client.post(
        f"/admin/league/{league_id}/managers/{manager['id']}/invite",
        json={"email": "gino@test.com"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email_sent_to"] == "gino@test.com"

    with get_db() as conn:
        rows = _queue_rows_for(conn, "gino@test.com")
        invite = conn.execute(
            "SELECT email FROM league_invite WHERE token = ?", (body["token"],)
        ).fetchone()
    assert len(rows) == 1
    assert rows[0]["template"] == "league_invite"
    assert json.loads(rows[0]["params"]) == {
        "manager_name": "Gino", "team_name": "Gino FC",
        "league_name": "InvitoLega", "token": body["token"],
    }
    assert invite["email"] == "gino@test.com"

    subject, html = notifications.render_email(
        "league_invite", json.loads(rows[0]["params"]), "https://fanta.test"
    )
    assert "InvitoLega" in subject
    assert f"https://fanta.test/coach/join?token={body['token']}" in html

    status = client.get(f"/admin/league/{league_id}/coaches-status").json()
    assert status[0]["invited_email"] == "gino@test.com"


def test_get_invite_returns_email_for_prefill(client):
    league_id = _create_league(client, name="InvitoLegaPrefill")
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "Ugo", "team_name": "Ugo FC"}
    ).json()
    with_email = client.post(
        f"/admin/league/{league_id}/managers/{manager['id']}/invite", json={"email": "ugo@test.com"},
    ).json()["token"]
    without_email = client.post(f"/admin/league/{league_id}/managers/{manager['id']}/invite").json()["token"]
    client.post("/auth/logout")

    r = client.get(f"/auth/invite/{with_email}")
    assert r.status_code == 200
    assert r.json() == {"email": "ugo@test.com"}
    assert client.get(f"/auth/invite/{without_email}").json() == {"email": None}
    assert client.get("/auth/invite/tokeninesistente").status_code == 404

    client.post("/auth/register", json={
        "name": "Ugo", "email": "ugo@test.com", "password": "pass1234", "invite_token": with_email,
    })
    assert client.get(f"/auth/invite/{with_email}").status_code == 404


def test_invite_without_email_enqueues_nothing(client):
    league_id = _create_league(client, name="InvitoLega2")
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "Pino", "team_name": "Pino FC"}
    ).json()
    with get_db() as conn:
        before = conn.execute("SELECT COUNT(*) FROM email_queue").fetchone()[0]
    r = client.post(f"/admin/league/{league_id}/managers/{manager['id']}/invite")
    assert r.status_code == 200, r.text
    assert r.json()["email_sent_to"] is None
    assert "/coach/join?token=" in r.json()["join_url"]
    with get_db() as conn:
        after = conn.execute("SELECT COUNT(*) FROM email_queue").fetchone()[0]
    assert after == before


def test_invite_rejects_invalid_email(client):
    league_id = _create_league(client, name="InvitoLega3")
    manager = client.post(
        f"/admin/league/{league_id}/managers", json={"name": "Lino", "team_name": "Lino FC"}
    ).json()
    r = client.post(
        f"/admin/league/{league_id}/managers/{manager['id']}/invite",
        json={"email": "non-una-email"},
    )
    assert r.status_code == 422


# ── Join lega ─────────────────────────────────────────────────────────────────

def test_join_league_enqueues_confirmation_email(client):
    league1 = _create_league(client, "Lega Uno")
    _, token1 = _create_manager_and_invite(client, league1)
    client.post("/auth/logout")
    client.post("/auth/register", json={
        "name": "Mario", "email": "mario2@test.com", "password": "pass1234", "invite_token": token1,
    })

    client.post("/auth/user/logout")
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    league2 = _create_league(client, "Lega Due")
    _, token2 = _create_manager_and_invite(client, league2, name="Mario2")
    client.post("/auth/logout")

    client.post("/auth/user/login", json={"email": "mario2@test.com", "password": "pass1234"})
    r = client.post("/auth/user/join", json={"invite_token": token2})
    assert r.status_code == 200

    with get_db() as conn:
        rows = _queue_rows_for(conn, "mario2@test.com")
    # mario2@test.com riceve sia l'email di registrazione (Lega Uno) sia quella di join (Lega Due).
    join_rows = [r for r in rows if r["template"] == "league_join"]
    assert len(join_rows) == 1
    assert json.loads(join_rows[0]["params"]) == {"name": "Mario", "league_name": "Lega Due"}


# ── Conclusione giornata ─────────────────────────────────────────────────────

def test_matchday_scores_enqueues_results_email_to_linked_managers(client):
    league_id = _create_league(client)
    manager_id, _ = _create_manager_and_invite(client, league_id)
    with get_db() as conn:
        _link_user(conn, manager_id, "coach@test.com")
        pc = conn.execute(
            "INSERT INTO player_current (league_id, name, role, team, quotation, manager_id)"
            " VALUES (?, 'Buffon G.', 'P', 'Juventus', 1, ?)",
            (league_id, manager_id),
        ).lastrowid
        conn.execute(
            "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter)"
            " VALUES (?, ?, 1, ?, 1)",
            (league_id, manager_id, pc),
        )

    client.post(f"/admin/league/{league_id}/draw/1")
    r = client.post(f"/admin/league/{league_id}/scores/1")
    assert r.status_code == 200, r.text

    with get_db() as conn:
        rows = _queue_rows_for(conn, "coach@test.com")
    assert len(rows) == 1
    assert rows[0]["template"] == "matchday_results"
    assert json.loads(rows[0]["params"]) == {
        "name": "Mario", "league_name": "NotifLega", "league_id": league_id, "matchday": 1,
    }


# ── Reminder pool iniziale ───────────────────────────────────────────────────

def test_assign_pools_enqueues_reminder_to_linked_managers(client):
    league_id = _create_league(client)
    manager_id, _ = _create_manager_and_invite(client, league_id)
    with get_db() as conn:
        _link_user(conn, manager_id, "coach2@test.com")
        conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('Buffon G.', 'P', 'Juventus', '2003/04', 'archive')"
        )

    r = client.post(f"/admin/league/{league_id}/mapping/assign-pools")
    assert r.status_code == 200, r.text

    with get_db() as conn:
        rows = _queue_rows_for(conn, "coach2@test.com")
    assert len(rows) == 1
    assert rows[0]["template"] == "pool_assignment"
    assert json.loads(rows[0]["params"]) == {
        "name": "Mario", "league_name": "NotifLega", "league_id": league_id,
    }


# ── Reminder Gran Premio vinto ───────────────────────────────────────────────

def _setup_gran_premio_league(client):
    league_id = _create_league(client)
    m1, _ = _create_manager_and_invite(client, league_id, name="M1")
    m2, _ = _create_manager_and_invite(client, league_id, name="M2")

    with get_db() as conn:
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic, cycle)"
            " VALUES (?, 1, 5, 1)",
            (league_id,),
        )
        for mid, pname, role, rating in [(m1, "A1", "A", 5.0), (m2, "A2", "A", 8.0)]:
            pc = conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, manager_id)"
                " VALUES (?, ?, ?, 'Milan', ?)",
                (league_id, pname, role, mid),
            ).lastrowid
            conn.execute(
                "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter)"
                " VALUES (?, ?, 1, ?, 1)",
                (league_id, mid, pc),
            )
            hist = conn.execute(
                "INSERT INTO player_historic (name, role, team, season, source)"
                " VALUES (?, ?, 'Milan', '2003/04', 'archive')",
                (f"H_{pname}", role),
            ).lastrowid
            conn.execute(
                "INSERT INTO historic_rating (player_historic_id, matchday, rating, source)"
                " VALUES (?, 5, ?, 'archive')",
                (hist, rating),
            )
            conn.execute(
                "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id)"
                " VALUES (?, ?, ?)",
                (league_id, pc, hist),
            )
        prize = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('PrizeGuy', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid

    client.post(f"/admin/league/{league_id}/scores/1", json={})
    return league_id, m1, m2, prize


def test_gran_premio_resolve_enqueues_email_for_linked_winner(client):
    league_id, m1, m2, prize = _setup_gran_premio_league(client)
    with get_db() as conn:
        _link_user(conn, m2, "winner@test.com", name="M2")

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": prize,
    })
    gp_id = r.json()["id"]
    r = client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")
    assert r.status_code == 200, r.text
    assert r.json()["winner_manager_id"] == m2

    with get_db() as conn:
        rows = _queue_rows_for(conn, "winner@test.com")
    assert len(rows) == 1
    assert rows[0]["template"] == "gran_premio_won"
    assert json.loads(rows[0]["params"]) == {
        "name": "M2", "league_name": "NotifLega", "league_id": league_id, "prize_player_name": "PrizeGuy",
    }


def test_gran_premio_resolve_no_email_if_winner_not_linked(client):
    """No manager in the league has a joined coach, so there's no eligible
    winner at all — resolve fails and no email is ever queued."""
    league_id, m1, m2, prize = _setup_gran_premio_league(client)
    with get_db() as conn:
        before = conn.execute(
            "SELECT COUNT(*) AS c FROM email_queue WHERE template = 'gran_premio_won'"
        ).fetchone()["c"]

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": prize,
    })
    gp_id = r.json()["id"]
    r = client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")
    assert r.status_code == 400, r.text

    with get_db() as conn:
        after = conn.execute(
            "SELECT COUNT(*) AS c FROM email_queue WHERE template = 'gran_premio_won'"
        ).fetchone()["c"]
    assert after == before


# ── POST /admin/process-email-queue ──────────────────────────────────────────

def test_process_email_queue_sends_pending_rows(client, monkeypatch):
    _drain_queue()
    calls = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, html: calls.append((to, subject, html)))

    league_id = _create_league(client)
    _, token = _create_manager_and_invite(client, league_id)
    client.post("/auth/logout")
    client.post("/auth/register", json={
        "name": "Mario", "email": "mario3@test.com", "password": "pass1234", "invite_token": token,
    })
    client.post("/auth/user/logout")
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})

    r = client.post("/admin/process-email-queue")
    assert r.status_code == 200, r.text
    assert r.json()["sent"] == 1
    assert r.json()["failed"] == 0
    assert r.json()["remaining_pending"] == 0

    assert len(calls) == 1
    to, subject, html = calls[0]
    assert to == "mario3@test.com"
    assert "Benvenuto" in subject
    assert "NotifLega" in html

    with get_db() as conn:
        row = _queue_rows_for(conn, "mario3@test.com")[0]
    assert row["status"] == "sent"
    assert row["sent_at"] is not None


def test_process_email_queue_dead_letters_after_max_attempts(client, monkeypatch):
    _drain_queue()

    def _boom(to, subject, html):
        raise RuntimeError("resend down")

    monkeypatch.setattr(notifications, "send_email", _boom)

    with get_db() as conn:
        row_id = notifications.enqueue_email(
            conn, "registration", "fail@test.com", {"name": "X", "league_name": "Y"}
        )

    for attempt in range(1, notifications.MAX_EMAIL_ATTEMPTS):
        r = client.post("/admin/process-email-queue")
        assert r.status_code == 200, r.text
        assert r.json()["retrying"] == 1
        assert r.json()["failed"] == 0
        with get_db() as conn:
            row = conn.execute("SELECT * FROM email_queue WHERE id = ?", (row_id,)).fetchone()
        assert row["status"] == "pending"
        assert row["attempts"] == attempt

    r = client.post("/admin/process-email-queue")
    assert r.json()["failed"] == 1
    with get_db() as conn:
        row = conn.execute("SELECT * FROM email_queue WHERE id = ?", (row_id,)).fetchone()
    assert row["status"] == "failed"
    assert row["attempts"] == notifications.MAX_EMAIL_ATTEMPTS

    # Un ulteriore giro non deve più toccare la riga dead-letter.
    r = client.post("/admin/process-email-queue")
    assert r.json()["processed"] == 0


def test_process_email_queue_requires_auth(client):
    client.post("/auth/logout")
    r = client.post("/admin/process-email-queue")
    assert r.status_code == 401


# ── send_email — contratto ────────────────────────────────────────────────────

def test_send_email_noop_without_api_key(monkeypatch):
    monkeypatch.setattr(notifications, "RESEND_API_KEY", None)
    # Non deve sollevare anche senza API key configurata.
    notifications.send_email("x@test.com", "subj", "<p>hi</p>")


def test_send_email_raises_on_failure(monkeypatch):
    monkeypatch.setattr(notifications, "RESEND_API_KEY", "fake-key")

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(notifications.httpx, "post", _boom)
    with pytest.raises(RuntimeError):
        notifications.send_email("x@test.com", "subj", "<p>hi</p>")


# ── Diagnostica email (pannello admin) ────────────────────────────────────────

def test_email_status_reports_config_and_queue(client, monkeypatch):
    monkeypatch.setattr(notifications, "RESEND_API_KEY", None)
    with get_db() as conn:
        notifications.enqueue_email(conn, "registration", "stato@test.com", {"name": "X", "league_name": "Y"})
        conn.execute(
            "UPDATE email_queue SET last_error = 'boom' WHERE to_email = 'stato@test.com'"
        )
    r = client.get("/admin/email/status")
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is False
    assert body["email_from"] == notifications.EMAIL_FROM
    assert body["queue"]["pending"] >= 1
    assert any(e["to_email"] == "stato@test.com" and e["last_error"] == "boom" for e in body["recent_errors"])


def test_email_test_fails_clearly_without_api_key(client, monkeypatch):
    monkeypatch.setattr(notifications, "RESEND_API_KEY", None)
    r = client.post("/admin/email/test", json={"to": "admin@test.com"})
    assert r.status_code == 400
    assert "RESEND_API_KEY" in r.json()["detail"]


def test_email_test_sends_immediately(client, monkeypatch):
    monkeypatch.setattr(notifications, "RESEND_API_KEY", "re_test")
    calls = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, html: calls.append((to, subject, html)))
    r = client.post("/admin/email/test", json={"to": "admin@test.com"})
    assert r.status_code == 200, r.text
    assert r.json()["sent_to"] == "admin@test.com"
    assert len(calls) == 1
    assert calls[0][0] == "admin@test.com"
    assert "prova" in calls[0][1]


def test_email_test_reports_resend_error(client, monkeypatch):
    import httpx

    monkeypatch.setattr(notifications, "RESEND_API_KEY", "re_test")

    def _reject(to, subject, html):
        req = httpx.Request("POST", notifications.RESEND_API_URL)
        resp = httpx.Response(403, request=req, text='{"message":"The domain is not verified"}')
        raise httpx.HTTPStatusError("403", request=req, response=resp)

    monkeypatch.setattr(notifications, "send_email", _reject)
    r = client.post("/admin/email/test", json={"to": "admin@test.com"})
    assert r.status_code == 502
    assert "403" in r.json()["detail"]
    assert "domain is not verified" in r.json()["detail"]


def test_email_admin_endpoints_require_auth(client):
    client.post("/auth/logout")
    assert client.get("/admin/email/status").status_code == 401
    assert client.post("/admin/email/test", json={"to": "a@test.com"}).status_code == 401
