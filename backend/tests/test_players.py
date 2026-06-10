from io import BytesIO

import openpyxl
import pytest


def _make_excel(rows: list[list], headers: list[str] | None = None) -> bytes:
    """Build an in-memory .xlsx with optional header row followed by data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def league_id(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    r = client.post("/admin/league", json={
        "name": "Test Lega Players",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    yield r.json()["id"]
    client.post("/auth/logout")


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


# ── Upload listone ───────────────────────────────────────────────────────────

def test_upload_listone_basic(client, league_id):
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[
            ["P", "Buffon G.", "Juventus", 15],
            ["D", "Maldini P.", "Milan", 25],
            ["C", "Pirlo A.", "Milan", 20],
            ["A", "Totti F.", "Roma", 30],
        ],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 4
    assert data["by_role"] == {"P": 1, "D": 1, "C": 1, "A": 1}
    assert any("presenze" in w.lower() for w in data["warnings"])


def test_upload_listone_with_starts(client, league_id):
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A", "Pv"],
        rows=[
            ["P", "Portiere X", "Team A", 10, 20],
            ["A", "Attaccante Y", "Team B", 8, 15],
        ],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 2
    assert not any("presenze" in w.lower() for w in data["warnings"])


def test_upload_listone_idempotent(client, league_id):
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[["P", "Portiere A", "Team X", 5]],
    )
    client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    # Second upload replaces the first
    xlsx2 = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[["D", "Difensore B", "Team Y", 3]],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    players = client.get(f"/league/{league_id}/players").json()
    assert len(players) == 1
    assert players[0]["name"] == "Difensore B"


def test_upload_listone_skips_invalid_rows(client, league_id):
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[
            ["X", "Giocatore Invalido", "Team Z", 10],  # ruolo non valido
            ["", "Nome Vuoto Ruolo", "Team Z", 10],      # ruolo vuoto
            ["A", "", "Team Z", 10],                     # nome vuoto
            ["P", "Portiere Valido", "Team A", 10],
        ],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 1
    assert any("saltate" in w for w in data["warnings"])


def test_upload_listone_role_aliases(client, league_id):
    xlsx = _make_excel(
        headers=["Ruolo", "Nome", "Squadra", "Quotazione"],
        rows=[
            ["Por", "Portiere Long", "Team", 5],
            ["Dif", "Difensore Long", "Team", 5],
            ["Cen", "Centrocampista Long", "Team", 5],
            ["Att", "Attaccante Long", "Team", 5],
        ],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 4


def test_upload_listone_header_not_in_first_row(client, league_id):
    # Extra junk rows before the real header
    xlsx = _make_excel(
        rows=[
            ["Fantacalcio 2024/25", None, None, None],
            ["Listone ufficiale", None, None, None],
            ["R", "Nome", "Squadra", "Qt A"],
            ["P", "Portiere Test", "Juventus", 12],
        ],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1


def test_upload_listone_not_found(client):
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[["P", "X", "Y", 5]],
    )
    r = client.post(
        "/admin/league/99999/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 404


def test_upload_listone_requires_auth(client, league_id):
    client.post("/auth/logout")
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[["P", "X", "Y", 5]],
    )
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("listone.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 401


# ── List players ─────────────────────────────────────────────────────────────

def _upload_sample(client, league_id):
    xlsx = _make_excel(
        headers=["R", "Nome", "Squadra", "Qt A"],
        rows=[
            ["P", "Buffon", "Juve", 15],
            ["D", "Maldini", "Milan", 20],
            ["D", "Nesta", "Milan", 18],
            ["C", "Pirlo", "Milan", 22],
            ["A", "Totti", "Roma", 30],
        ],
    )
    client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("l.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def test_list_players(client, league_id):
    _upload_sample(client, league_id)
    r = client.get(f"/league/{league_id}/players")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_list_players_filter_role(client, league_id):
    _upload_sample(client, league_id)
    r = client.get(f"/league/{league_id}/players?role=D")
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert all(p["role"] == "D" for p in r.json())


def test_list_players_invalid_role(client, league_id):
    r = client.get(f"/league/{league_id}/players?role=X")
    assert r.status_code == 400


def test_list_players_league_not_found(client):
    r = client.get("/league/99999/players")
    assert r.status_code == 404


# ── Assign players ───────────────────────────────────────────────────────────

def _create_manager(league_id, name="Manager Test"):
    from backend.api.db import get_db
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, name, f"Team {name}"),
        )
        return cur.lastrowid


def test_assign_players(client, league_id):
    _upload_sample(client, league_id)
    players = client.get(f"/league/{league_id}/players").json()
    manager_id = _create_manager(league_id)

    assign_body = [{"player_id": players[0]["id"], "manager_id": manager_id}]
    r = client.post(f"/admin/league/{league_id}/assign", json=assign_body)
    assert r.status_code == 200
    assert r.json()["assigned"] == 1

    updated = client.get(f"/league/{league_id}/players?manager_id={manager_id}").json()
    assert len(updated) == 1
    assert updated[0]["id"] == players[0]["id"]


def test_assign_players_wrong_player(client, league_id):
    manager_id = _create_manager(league_id)
    r = client.post(f"/admin/league/{league_id}/assign", json=[
        {"player_id": 99999, "manager_id": manager_id}
    ])
    assert r.status_code == 400


def test_assign_players_wrong_manager(client, league_id):
    _upload_sample(client, league_id)
    players = client.get(f"/league/{league_id}/players").json()
    r = client.post(f"/admin/league/{league_id}/assign", json=[
        {"player_id": players[0]["id"], "manager_id": 99999}
    ])
    assert r.status_code == 400


def test_assign_requires_auth(client, league_id):
    client.post("/auth/logout")
    r = client.post(f"/admin/league/{league_id}/assign", json=[])
    assert r.status_code == 401
