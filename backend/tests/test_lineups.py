from io import BytesIO

import openpyxl
import pytest


def _make_excel(rows: list[list], headers: list[str] | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


@pytest.fixture()
def setup(client):
    """Crea lega, due manager, carica giocatori e restituisce (league_id, manager_ids)."""
    r = client.post("/admin/league", json={
        "name": "Lega Lineups Test",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = r.json()["id"]

    from backend.api.db import get_db
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, "Simone", "TeamS"),
        )
        m1 = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, "Marco", "TeamM"),
        )
        m2 = cur.lastrowid

    # Inserisci giocatori direttamente via DB e assegnali ai manager
    player_names = [
        ("P", "Buffon G.", "Juventus"),
        ("D", "Maldini P.", "Milan"),
        ("D", "Nesta A.", "Milan"),
        ("D", "Cannavaro F.", "Parma"),
        ("D", "Costacurta A.", "Milan"),
        ("C", "Pirlo A.", "Milan"),
        ("C", "Totti F.", "Roma"),
        ("C", "Seedorf C.", "Milan"),
        ("C", "Vieri C.", "Inter"),
        ("A", "Del Piero A.", "Juventus"),
        ("A", "Inzaghi F.", "Milan"),
        ("P", "Toldo F.", "Inter"),
        ("D", "Zanetti J.", "Inter"),
        ("D", "Thuram L.", "Juventus"),
        ("D", "Cafu", "Milan"),
        ("D", "Panucci C.", "Roma"),
        ("C", "Nedved P.", "Juventus"),
        ("C", "Figo L.", "Real"),
        ("C", "Zidane Z.", "Real"),
        ("A", "Ronaldo R.", "Real"),
        ("A", "Shevchenko A.", "Milan"),
    ]
    with get_db() as conn:
        for i, (role, name, team) in enumerate(player_names):
            manager_id = m1 if i < 11 else m2
            conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, quotation, manager_id)"
                " VALUES (?, ?, ?, ?, 1, ?)",
                (league_id, name, role, team, manager_id),
            )

    all_players = client.get(f"/league/{league_id}/players").json()
    return league_id, m1, m2, all_players


def _lineup_xlsx(simone_players, marco_players) -> bytes:
    rows = [["Manager", "Giocatore", "Titolare"]]
    for p in simone_players:
        rows.append(["Simone", p["name"], 1])
    for p in marco_players:
        rows.append(["Marco", p["name"], 1])
    return _make_excel(rows=rows[1:], headers=rows[0])


# ── Upload ───────────────────────────────────────────────────────────────────

def test_upload_basic(client, setup):
    league_id, m1, m2, players = setup
    simone_players = [p for p in players if p["manager_id"] == m1][:11]
    marco_players = [p for p in players if p["manager_id"] == m2][:10]

    xlsx = _lineup_xlsx(simone_players, marco_players)
    r = client.post(
        f"/admin/league/{league_id}/lineups/1",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["matchday"] == 1
    assert body["managers_imported"] == 2
    assert body["warnings"] == []


def test_upload_idempotent(client, setup):
    league_id, m1, m2, players = setup
    simone_players = [p for p in players if p["manager_id"] == m1][:11]
    marco_players = [p for p in players if p["manager_id"] == m2][:10]
    xlsx = _lineup_xlsx(simone_players, marco_players)

    for _ in range(2):
        r = client.post(
            f"/admin/league/{league_id}/lineups/2",
            files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200

    # Deve esserci una sola formazione importata, non duplicati
    lineups = client.get(f"/league/{league_id}/lineups/2").json()
    player_ids = [l["player_current_id"] for l in lineups]
    assert len(player_ids) == len(set(player_ids)), "Duplicati dopo reimport idempotente"


def test_upload_player_not_found_warning(client, setup):
    league_id, m1, *_ = setup
    xlsx = _make_excel(
        headers=["Manager", "Giocatore", "Titolare"],
        rows=[["Simone", "Fantasma X.", 1]],
    )
    r = client.post(
        f"/admin/league/{league_id}/lineups/3",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    assert any("Fantasma X." in w for w in warnings)
    assert r.json()["managers_imported"] == 0


def test_upload_manager_not_found_warning(client, setup):
    league_id, *_ = setup
    xlsx = _make_excel(
        headers=["Manager", "Giocatore", "Titolare"],
        rows=[["ManagerInesistente", "Buffon G.", 1]],
    )
    r = client.post(
        f"/admin/league/{league_id}/lineups/4",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    assert any("ManagerInesistente" in w for w in warnings)


def test_upload_case_insensitive_match(client, setup):
    league_id, m1, m2, players = setup
    simone_player = [p for p in players if p["manager_id"] == m1][0]
    # Nome in maiuscolo e manager con case diverso
    xlsx = _make_excel(
        headers=["Manager", "Giocatore", "Titolare"],
        rows=[["SIMONE", simone_player["name"].upper(), 1]],
    )
    r = client.post(
        f"/admin/league/{league_id}/lineups/5",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    assert r.json()["managers_imported"] == 1
    assert r.json()["warnings"] == []


def test_upload_missing_header(client, setup):
    league_id, *_ = setup
    xlsx = _make_excel(rows=[["Simone", "Buffon G.", 1]])  # no header
    r = client.post(
        f"/admin/league/{league_id}/lineups/6",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 400


def test_upload_requires_auth(client, setup):
    league_id, *_ = setup
    client.post("/auth/logout")
    xlsx = _make_excel(headers=["Manager", "Giocatore", "Titolare"], rows=[])
    r = client.post(
        f"/admin/league/{league_id}/lineups/7",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 401


def test_upload_league_not_found(client):
    xlsx = _make_excel(headers=["Manager", "Giocatore", "Titolare"], rows=[])
    r = client.post(
        "/admin/league/99999/lineups/1",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 404


# ── GET lineups ──────────────────────────────────────────────────────────────

def test_get_lineups(client, setup):
    league_id, m1, m2, players = setup
    simone_players = [p for p in players if p["manager_id"] == m1][:11]
    marco_players = [p for p in players if p["manager_id"] == m2][:10]
    xlsx = _lineup_xlsx(simone_players, marco_players)

    client.post(
        f"/admin/league/{league_id}/lineups/8",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    r = client.get(f"/league/{league_id}/lineups/8")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 21  # 11 + 10
    assert all("player_name" in item for item in data)
    assert all("manager_name" in item for item in data)
    assert all("locked_at" in item for item in data)


def test_get_lineups_empty_matchday(client, setup):
    league_id, *_ = setup
    r = client.get(f"/league/{league_id}/lineups/999")
    assert r.status_code == 200
    assert r.json() == []


def test_get_lineups_league_not_found(client):
    r = client.get("/league/99999/lineups/1")
    assert r.status_code == 404
