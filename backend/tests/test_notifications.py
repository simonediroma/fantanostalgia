import pytest

from backend.api import notifications
from backend.api.db import get_db


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")
    client.post("/auth/user/logout")


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, html: calls.append((to, subject, html)))
    return calls


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


# ── Registrazione ────────────────────────────────────────────────────────────

def test_registration_sends_welcome_email(client, sent):
    league_id = _create_league(client)
    _, token = _create_manager_and_invite(client, league_id)
    client.post("/auth/logout")

    r = client.post("/auth/register", json={
        "name": "Mario", "email": "mario@test.com", "password": "pass1234", "invite_token": token,
    })
    assert r.status_code == 201

    assert len(sent) == 1
    to, subject, html = sent[0]
    assert to == "mario@test.com"
    assert "Benvenuto" in subject
    assert "NotifLega" in html


# ── Join lega ─────────────────────────────────────────────────────────────────

def test_join_league_sends_confirmation_email(client, sent):
    league1 = _create_league(client, "Lega Uno")
    _, token1 = _create_manager_and_invite(client, league1)
    client.post("/auth/logout")
    client.post("/auth/register", json={
        "name": "Mario", "email": "mario2@test.com", "password": "pass1234", "invite_token": token1,
    })
    sent.clear()  # ignore the registration email

    client.post("/auth/user/logout")
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    league2 = _create_league(client, "Lega Due")
    _, token2 = _create_manager_and_invite(client, league2, name="Mario2")
    client.post("/auth/logout")

    client.post("/auth/user/login", json={"email": "mario2@test.com", "password": "pass1234"})
    r = client.post("/auth/user/join", json={"invite_token": token2})
    assert r.status_code == 200

    assert len(sent) == 1
    to, subject, html = sent[0]
    assert to == "mario2@test.com"
    assert "Lega Due" in subject


# ── Conclusione giornata ─────────────────────────────────────────────────────

def test_matchday_scores_sends_results_email_to_linked_managers(client, sent):
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

    assert len(sent) == 1
    to, subject, html = sent[0]
    assert to == "coach@test.com"
    assert "giornata 1" in subject


# ── Reminder pool iniziale ───────────────────────────────────────────────────

def test_assign_pools_sends_reminder_to_linked_managers(client, sent):
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

    assert len(sent) == 1
    to, subject, html = sent[0]
    assert to == "coach2@test.com"
    assert "rosa nostalgia" in subject.lower()


# ── Reminder Gran Premio vinto ───────────────────────────────────────────────

def test_gran_premio_resolve_notifies_winner(client, sent):
    league_id = _create_league(client)
    m1, _ = _create_manager_and_invite(client, league_id, name="M1")
    m2, _ = _create_manager_and_invite(client, league_id, name="M2")

    with get_db() as conn:
        _link_user(conn, m2, "winner@test.com", name="M2")
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

    r = client.post(f"/admin/league/{league_id}/scores/1", json={})
    assert r.status_code == 200, r.text
    sent.clear()  # ignore the matchday-results emails (neither manager linked yet except m2)

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": prize,
    })
    gp_id = r.json()["id"]
    r = client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")
    assert r.status_code == 200, r.text
    assert r.json()["winner_manager_id"] == m2

    assert len(sent) == 1
    to, subject, html = sent[0]
    assert to == "winner@test.com"
    assert "Gran Premio" in subject
    assert "PrizeGuy" in html


def test_gran_premio_resolve_no_email_if_winner_not_linked(client, sent):
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
            " VALUES ('PrizeGuy2', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid

    client.post(f"/admin/league/{league_id}/scores/1", json={})
    sent.clear()

    r = client.post(f"/admin/league/{league_id}/granpremio", json={
        "matchday": 1, "criterion": "best_score", "prize_player_historic_id": prize,
    })
    gp_id = r.json()["id"]
    r = client.post(f"/admin/league/{league_id}/granpremio/{gp_id}/resolve")
    assert r.status_code == 200, r.text

    assert sent == []


# ── send_email best-effort ───────────────────────────────────────────────────

def test_send_email_noop_without_api_key(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(notifications, "RESEND_API_KEY", None)
    # Must not raise even without an API key configured.
    notifications.send_email("x@test.com", "subj", "<p>hi</p>")


def test_send_email_failure_does_not_raise(monkeypatch):
    monkeypatch.setattr(notifications, "RESEND_API_KEY", "fake-key")

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(notifications.httpx, "post", _boom)
    # Best-effort: failures are logged, never propagated.
    notifications.send_email("x@test.com", "subj", "<p>hi</p>")
