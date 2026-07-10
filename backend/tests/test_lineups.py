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


def test_upload_blocked_when_gran_premio_resolved(client, setup):
    league_id, m1, m2, players = setup
    simone_players = [p for p in players if p["manager_id"] == m1][:11]
    marco_players = [p for p in players if p["manager_id"] == m2][:10]
    xlsx = _lineup_xlsx(simone_players, marco_players)

    r = client.post(
        f"/admin/league/{league_id}/lineups/5",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200

    from backend.api.db import get_db
    with get_db() as conn:
        hist_id = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('Storico X', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid
        conn.execute(
            "INSERT INTO gran_premio (league_id, matchday, criterion, prize_player_historic_id, status)"
            " VALUES (?, 5, 'best_score', ?, 'resolved')",
            (league_id, hist_id),
        )

    r2 = client.post(
        f"/admin/league/{league_id}/lineups/5",
        files={"file": ("lineups2.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r2.status_code == 400
    assert "Gran Premio" in r2.json()["detail"]

    # Un'altra giornata della stessa lega non è bloccata
    r3 = client.post(
        f"/admin/league/{league_id}/lineups/6",
        files={"file": ("lineups3.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r3.status_code == 200


def test_upload_allowed_when_gran_premio_active(client, setup):
    league_id, m1, m2, players = setup
    simone_players = [p for p in players if p["manager_id"] == m1][:11]
    marco_players = [p for p in players if p["manager_id"] == m2][:10]
    xlsx = _lineup_xlsx(simone_players, marco_players)

    r = client.post(
        f"/admin/league/{league_id}/lineups/7",
        files={"file": ("lineups.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200

    from backend.api.db import get_db
    with get_db() as conn:
        hist_id = conn.execute(
            "INSERT INTO player_historic (name, role, team, season, source)"
            " VALUES ('Storico Y', 'A', 'Milan', '2003/04', 'archive')"
        ).lastrowid
        conn.execute(
            "INSERT INTO gran_premio (league_id, matchday, criterion, prize_player_historic_id, status)"
            " VALUES (?, 7, 'best_score', ?, 'active')",
            (league_id, hist_id),
        )

    r2 = client.post(
        f"/admin/league/{league_id}/lineups/7",
        files={"file": ("lineups2.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r2.status_code == 200


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


# ── Formazioni (real format) ─────────────────────────────────────────────────

def _make_formazioni_excel(
    matches: list[tuple[str, str, str, list[str], list[str], list[str], list[str]]]
) -> bytes:
    """
    Build a Formazioni-format Excel with two matches side by side per block.
    Each match is (team_left, score, team_right, starters_left, bench_left, starters_right, bench_right).
    For simplicity each player name is also the role (P/D/C/A) to keep tests minimal.
    """
    wb = openpyxl.Workbook()
    ws = wb.active

    ws.append(["Formazioni Test", None, None, None, None, None, None, None, None, None, None])
    ws.append([None] * 11)

    for team_l, score, team_r, starters_l, bench_l, starters_r, bench_r in matches:
        ws.append([team_l, None, None, None, None, score, team_r, None, None, None, None])
        ws.append(["343", None, None, None, None, "", "343", None, None, None, None])

        max_starters = max(len(starters_l), len(starters_r))
        for i in range(max_starters):
            pl = starters_l[i] if i < len(starters_l) else None
            pr = starters_r[i] if i < len(starters_r) else None
            ws.append(["A", pl, None, 6.0, 6.0, None, "A", pr, None, 6.0, 6.0])

        ws.append(["Panchina", None, None, None, None, None, "Panchina", None, None, None, None])

        max_bench = max(len(bench_l), len(bench_r))
        for i in range(max_bench):
            pl = bench_l[i] if i < len(bench_l) else None
            pr = bench_r[i] if i < len(bench_r) else None
            ws.append(["A", pl, None, "-", "-", None, "A", pr, None, "-", "-"])

        ws.append(["TOTALE: 65,00", None, None, None, None, None, "TOTALE: 70,00", None, None, None, None])
        ws.append([None] * 11)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def formazioni_setup(client):
    """Lega con due manager e giocatori nelle rose, usando team_name per lookup."""
    client.post("/auth/login", json={"username": "admin", "password": "testpass"})
    r = client.post("/admin/league", json={
        "name": "Lega Formazioni Test",
        "season_current": "2024/25",
        "season_historic": "2003/04",
        "budget": 500,
    })
    league_id = r.json()["id"]

    from backend.api.db import get_db
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, "Simone", "ALPHA"),
        )
        m1 = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, "Marco", "BETA"),
        )
        m2 = cur.lastrowid

        player_names = ["Ronaldo", "Maldini", "Pirlo", "Totti", "Del Piero",
                        "Buffon", "Cannavaro", "Nesta", "Inzaghi", "Sheva", "Baggio"]
        for i, name in enumerate(player_names):
            conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, quotation, manager_id)"
                " VALUES (?, ?, 'A', 'Juve', 10, ?)",
                (league_id, name, m1),
            )

        player_names2 = ["Toldo", "Costacurta", "Albertini", "Vieri", "Weah",
                         "Rossi", "Rivera", "Facchetti", "Mazzola", "Riva", "Altafini"]
        for name in player_names2:
            conn.execute(
                "INSERT INTO player_current (league_id, name, role, team, quotation, manager_id)"
                " VALUES (?, ?, 'A', 'Mil', 10, ?)",
                (league_id, name, m2),
            )

    yield league_id, m1, m2
    client.post("/auth/logout")


def test_upload_formazioni_basic(client, formazioni_setup):
    """Formazioni format: players imported and matched by team_name."""
    league_id, m1, m2 = formazioni_setup

    xlsx = _make_formazioni_excel([
        (
            "ALPHA", "2-1", "BETA",
            ["Ronaldo", "Maldini", "Pirlo"],   # alpha starters
            ["Totti", "Del Piero"],              # alpha bench
            ["Toldo", "Costacurta", "Albertini"],  # beta starters
            ["Vieri", "Weah"],                   # beta bench
        ),
    ])
    r = client.post(
        f"/admin/league/{league_id}/lineups/10",
        files={"file": ("formazioni.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["matchday"] == 10
    assert body["managers_imported"] == 2

    lineups = client.get(f"/league/{league_id}/lineups/10").json()
    starters = [p for p in lineups if p["is_starter"] == 1]
    bench = [p for p in lineups if p["is_starter"] == 0]
    assert len(starters) == 6   # 3 per team
    assert len(bench) == 4      # 2 per team


def test_upload_formazioni_team_name_case_insensitive(client, formazioni_setup):
    """Formazioni format: team name lookup is case-insensitive."""
    league_id, m1, m2 = formazioni_setup

    # Use lowercase team name — should still match manager with team_name='ALPHA'
    xlsx = _make_formazioni_excel([
        (
            "alpha", "1-0", "beta",
            ["Ronaldo"],
            [],
            ["Toldo"],
            [],
        ),
    ])
    r = client.post(
        f"/admin/league/{league_id}/lineups/11",
        files={"file": ("formazioni.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200
    assert r.json()["managers_imported"] == 2


def test_upload_formazioni_panchina_flag(client, formazioni_setup):
    """Formazioni format: is_starter=0 for bench players."""
    league_id, *_ = formazioni_setup

    xlsx = _make_formazioni_excel([
        (
            "ALPHA", "0-0", "BETA",
            ["Ronaldo", "Maldini"],   # starters
            ["Pirlo"],                 # bench
            ["Toldo", "Costacurta"],  # starters
            ["Albertini"],             # bench
        ),
    ])
    client.post(
        f"/admin/league/{league_id}/lineups/12",
        files={"file": ("formazioni.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    lineups = client.get(f"/league/{league_id}/lineups/12").json()
    by_name = {p["player_name"]: p["is_starter"] for p in lineups}
    assert by_name["Ronaldo"] == 1
    assert by_name["Maldini"] == 1
    assert by_name["Pirlo"] == 0
    assert by_name["Toldo"] == 1
    assert by_name["Albertini"] == 0
