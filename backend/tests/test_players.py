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


def test_list_players_ordered_by_role_then_name(client, league_id):
    _upload_sample(client, league_id)
    r = client.get(f"/league/{league_id}/players")
    assert r.status_code == 200
    assert [p["name"] for p in r.json()] == ["Buffon", "Maldini", "Nesta", "Pirlo", "Totti"]
    assert [p["role"] for p in r.json()] == ["P", "D", "D", "C", "A"]


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


# ── Rose (dual-column) format ────────────────────────────────────────────────

def _make_rose_excel(teams: list[tuple[str, list[tuple[str, str, str, int]]]]) -> bytes:
    """
    Build a Rose-format Excel with teams paired side by side.
    teams: list of (team_name, [(role, player_name, squad, cost), ...])
    Pairs teams in groups of 2.
    """
    wb = openpyxl.Workbook()
    ws = wb.active

    # Metadata rows
    ws.append(["Rose lega Test", None, None, None, None, None, None, None, None])
    ws.append([None] * 9)

    for i in range(0, len(teams), 2):
        left_name, left_players = teams[i]
        right_name = right_players = None
        if i + 1 < len(teams):
            right_name, right_players = teams[i + 1]

        # Team name row
        ws.append([left_name, None, None, None, None, right_name, None, None, None])
        # Header row
        ws.append(["Ruolo", "Calciatore", "Squadra", "Costo", None, "Ruolo", "Calciatore", "Squadra", "Costo"])

        max_players = max(len(left_players), len(right_players or []))
        for j in range(max_players):
            l_row = list(left_players[j]) if j < len(left_players) else [None] * 4
            r_row = list(right_players[j]) if right_players and j < len(right_players) else [None] * 4
            ws.append(l_row[:4] + [None] + r_row[:4])

        # Crediti residui
        ws.append(["Crediti Residui: 0", None, None, None, None, "Crediti Residui: 0", None, None, None])
        ws.append([None] * 9)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_upload_listone_rose_format_basic(client, league_id):
    """Rose format: both left and right column players are imported."""
    xlsx = _make_rose_excel([
        ("Team A", [("P", "Buffon", "Juv", 15), ("D", "Maldini", "Mil", 20)]),
        ("Team B", [("P", "Toldo", "Int", 10), ("A", "Totti", "Rom", 30)]),
    ])
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("rose.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 4
    assert data["by_role"] == {"P": 2, "D": 1, "C": 0, "A": 1}

    players = client.get(f"/league/{league_id}/players").json()
    names = {p["name"] for p in players}
    assert names == {"Buffon", "Maldini", "Toldo", "Totti"}


def test_upload_listone_rose_format_auto_assigns(client):
    """Rose format: players are auto-assigned to managers matching team_name."""
    from backend.api.db import get_db

    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    r = client.post("/admin/league", json={
        "name": "Lega Rose Auto-Assign",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    lid = r.json()["id"]

    with get_db() as conn:
        conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (lid, "Simone", "Team A"),
        )
        conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (lid, "Marco", "Team B"),
        )

    xlsx = _make_rose_excel([
        ("Team A", [("P", "Buffon", "Juv", 15), ("D", "Maldini", "Mil", 20)]),
        ("Team B", [("A", "Totti", "Rom", 30)]),
    ])
    r = client.post(
        f"/admin/league/{lid}/listone",
        files={"file": ("rose.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 3
    assert r.json()["warnings"] == []

    players = client.get(f"/league/{lid}/players").json()
    team_a_players = [p for p in players if p["name"] in ("Buffon", "Maldini")]
    team_b_players = [p for p in players if p["name"] == "Totti"]
    assert all(p["manager_id"] is not None for p in team_a_players)
    assert all(p["manager_id"] is not None for p in team_b_players)
    # Different managers
    assert team_a_players[0]["manager_id"] != team_b_players[0]["manager_id"]

    client.post("/auth/logout")


def test_upload_listone_rose_format_costo_as_quota(client, league_id):
    """Rose format: 'Costo' column is imported as quotation."""
    xlsx = _make_rose_excel([
        ("Team A", [("P", "Portiere X", "Juv", 42)]),
        ("Team B", [("A", "Attaccante Y", "Rom", 99)]),
    ])
    r = client.post(
        f"/admin/league/{league_id}/listone",
        files={"file": ("rose.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    players = client.get(f"/league/{league_id}/players").json()
    by_name = {p["name"]: p for p in players}
    assert by_name["Portiere X"]["quotation"] == 42
    assert by_name["Attaccante Y"]["quotation"] == 99
