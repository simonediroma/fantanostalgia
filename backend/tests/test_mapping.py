import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed_historic(client, season: str = "2003/04"):
    """Insert a set of historic players via direct DB access."""
    from backend.api.db import get_db

    players = [
        ("Buffon G.", "P", "Juventus"),
        ("Toldo F.", "P", "Inter"),
        ("Maldini P.", "D", "Milan"),
        ("Nesta A.", "D", "Milan"),
        ("Cannavaro F.", "D", "Juventus"),
        ("Thuram L.", "D", "Juventus"),
        ("Camoranesi M.", "D", "Juventus"),
        ("Pirlo A.", "C", "Milan"),
        ("Seedorf C.", "C", "Milan"),
        ("Gattuso G.", "C", "Milan"),
        ("Veron J.", "C", "Inter"),
        ("Zanetti J.", "C", "Inter"),
        ("Totti F.", "A", "Roma"),
        ("Shevchenko A.", "A", "Milan"),
        ("Vieri C.", "A", "Inter"),
        ("Del Piero A.", "A", "Juventus"),
    ]
    with get_db() as conn:
        conn.executemany(
            "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, ?, ?, ?, 'archive')",
            [(n, r, t, season) for n, r, t in players],
        )


def _create_league_with_listone(client) -> tuple[int, list[int]]:
    """Create a league, add managers, upload listone. Returns (league_id, [manager_ids])."""
    r = client.post("/admin/league", json={
        "name": "TestMappingLega",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = r.json()["id"]

    from backend.api.db import get_db as _get_db

    mgr_ids = []
    with _get_db() as conn:
        for name in ("Alice", "Bob"):
            cur = conn.execute(
                "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
                (league_id, name, f"{name} FC"),
            )
            mgr_ids.append(cur.lastrowid)

    # Insert current players directly
    from backend.api.db import get_db

    with get_db() as conn:
        for role, names in {
            "P": ["Donnarumma G.", "Szczesny W.", "Maignan M."],
            "D": ["Calabria D.", "Hernandez T.", "Tomori F.", "Kalulu P.", "Kjaer S.", "Florenzi A.", "Dest S.", "Ballo-Toure F."],
            "C": ["Tonali S.", "Bennacer I.", "Krunic R.", "Kessie F.", "Pobega T.", "Bakayoko T.", "Diaz B.", "Maldini D."],
            "A": ["Giroud O.", "Leao R.", "Ibrahimovic Z.", "Rebic A.", "Saelemaekers A.", "Origi D."],
        }.items():
            for i, name in enumerate(names):
                manager_id = mgr_ids[i % len(mgr_ids)]
                conn.execute(
                    "INSERT INTO player_current (league_id, name, role, team, quotation, starts_current_season, manager_id)"
                    " VALUES (?, ?, ?, 'Milan', 10, ?, ?)",
                    (league_id, name, role, 20 - i, manager_id),
                )

    return league_id, mgr_ids


@pytest.fixture(autouse=True)
def login(client):
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    yield
    client.post("/auth/logout")


# ── Generate mapping ─────────────────────────────────────────────────────────

def test_generate_mapping_ok(client):
    _seed_historic(client)
    league_id, _ = _create_league_with_listone(client)

    r = client.post(f"/admin/league/{league_id}/mapping/generate")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mapped"] > 0
    assert "duplicates" in data
    assert isinstance(data["coverage_by_manager"], list)
    assert len(data["coverage_by_manager"]) == 2


def test_generate_mapping_idempotent(client):
    _seed_historic(client)
    league_id, _ = _create_league_with_listone(client)

    r1 = client.post(f"/admin/league/{league_id}/mapping/generate")
    assert r1.status_code == 200
    r2 = client.post(f"/admin/league/{league_id}/mapping/generate")
    assert r2.status_code == 200
    # second call replaces first — mapped count should be the same
    assert r1.json()["mapped"] == r2.json()["mapped"]


def test_generate_mapping_no_listone(client):
    r = client.post("/admin/league", json={
        "name": "EmptyLega",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = r.json()["id"]
    r = client.post(f"/admin/league/{league_id}/mapping/generate")
    assert r.status_code == 400
    assert "listone" in r.json()["detail"].lower()


def test_generate_mapping_no_historic(client):
    r = client.post("/admin/league", json={
        "name": "NoHistoricLega",
        "season_current": "2024/25",
        "season_historic": "9999/00",
        "budget": 500,
    })
    league_id = r.json()["id"]

    from backend.api.db import get_db
    with get_db() as conn:
        conn.execute(
            "INSERT INTO player_current (league_id, name, role, team, quotation) VALUES (?, 'X', 'P', 'Y', 1)",
            (league_id,),
        )

    r = client.post(f"/admin/league/{league_id}/mapping/generate")
    assert r.status_code == 400
    assert "storico" in r.json()["detail"].lower()


def test_generate_mapping_404(client):
    r = client.post("/admin/league/99999/mapping/generate")
    assert r.status_code == 404


def test_generate_requires_auth(client):
    client.post("/auth/logout")
    r = client.post("/admin/league/1/mapping/generate")
    assert r.status_code == 401


# ── GET mapping ──────────────────────────────────────────────────────────────

def test_get_mapping_ok(client):
    _seed_historic(client)
    league_id, _ = _create_league_with_listone(client)

    client.post(f"/admin/league/{league_id}/mapping/generate")

    r = client.get(f"/admin/league/{league_id}/mapping")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "player_current_name" in first
    assert "player_historic_name" in first
    assert "is_duplicate" in first


def test_get_mapping_empty(client):
    r = client.post("/admin/league", json={
        "name": "EmptyMappingLega",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = r.json()["id"]
    r = client.get(f"/admin/league/{league_id}/mapping")
    assert r.status_code == 200
    assert r.json() == []


def test_get_mapping_404(client):
    r = client.get("/admin/league/99999/mapping")
    assert r.status_code == 404


def test_get_mapping_requires_auth(client):
    client.post("/auth/logout")
    r = client.get("/admin/league/1/mapping")
    assert r.status_code == 401


# ── Algorithm correctness ────────────────────────────────────────────────────

def test_mapping_role_consistency(client):
    """Every current player must have a historic alter ego of the same role."""
    _seed_historic(client)
    league_id, _ = _create_league_with_listone(client)
    client.post(f"/admin/league/{league_id}/mapping/generate")

    r = client.get(f"/admin/league/{league_id}/mapping")
    data = r.json()

    from backend.api.db import get_db
    with get_db() as conn:
        historic_roles = {
            row["id"]: row["role"]
            for row in conn.execute("SELECT id, role FROM player_historic").fetchall()
        }

    for entry in data:
        current_role = entry["role"]
        historic_role = historic_roles[entry["player_historic_id"]]
        assert current_role == historic_role, (
            f"{entry['player_current_name']} (role={current_role}) mapped to "
            f"{entry['player_historic_name']} (role={historic_role})"
        )


def test_mapping_seed_saved(client):
    _seed_historic(client)
    league_id, _ = _create_league_with_listone(client)
    client.post(f"/admin/league/{league_id}/mapping/generate")

    from backend.api.db import get_db
    with get_db() as conn:
        row = conn.execute("SELECT mapping_seed FROM league WHERE id = ?", (league_id,)).fetchone()
    assert row["mapping_seed"] is not None
    assert len(row["mapping_seed"]) > 0
