import random
import sqlite3
from dataclasses import dataclass, field

ROLES = ("P", "D", "C", "A")
MIN_COVERAGE = {"P": 1, "D": 4, "C": 4, "A": 3}
POOL_SIZE = {"P": 1, "D": 4, "C": 4, "A": 3}


@dataclass
class MappingResult:
    mapped: int = 0
    duplicates: int = 0
    coverage_by_manager: list[dict] = field(default_factory=list)


def generate_mapping(conn: sqlite3.Connection, league_id: int) -> MappingResult:
    """Assign a historic alter ego to every current player in the league.

    Steps (in order):
    1. Build pool per role from player_historic for the league's season_historic
    2. Sort current players per role by starts_current_season DESC
    3. Assign random from pool without replacement (is_duplicate=0)
    4. Check minimum coverage per manager
    5. Fallback duplicates for uncovered slots
    6. Persist mapping and seed
    """
    league = conn.execute(
        "SELECT season_historic FROM league WHERE id = ?", (league_id,)
    ).fetchone()
    if league is None:
        raise ValueError("Lega non trovata")

    season_historic = league["season_historic"]

    # Step 1 — build pools per role
    pools: dict[str, list[int]] = {}
    for role in ROLES:
        rows = conn.execute(
            "SELECT id FROM player_historic WHERE season = ? AND role = ?",
            (season_historic, role),
        ).fetchall()
        pools[role] = [r["id"] for r in rows]

    # Step 2 — load current players sorted by titolarità DESC
    current_players: dict[str, list[dict]] = {}
    for role in ROLES:
        rows = conn.execute(
            "SELECT id, manager_id FROM player_current"
            " WHERE league_id = ? AND role = ?"
            " ORDER BY starts_current_season DESC",
            (league_id, role),
        ).fetchall()
        current_players[role] = [dict(r) for r in rows]

    seed = str(random.random())
    rng = random.Random(seed)

    assignments: list[tuple] = []  # (league_id, player_current_id, player_historic_id, is_duplicate)

    # Step 3 — assign from pool without replacement
    for role in ROLES:
        available = pools[role][:]
        rng.shuffle(available)
        for player in current_players[role]:
            if available:
                historic_id = available.pop()
                assignments.append((league_id, player["id"], historic_id, 0))
            # players without alter ego are handled in step 5

    # Step 4 — check minimum coverage per manager
    managers = conn.execute(
        "SELECT id FROM manager WHERE league_id = ?", (league_id,)
    ).fetchall()
    manager_ids = [r["id"] for r in managers]

    # Build a map of what's already assigned: manager_id -> role -> count
    assigned_map: dict[int, dict[str, int]] = {
        mid: {role: 0 for role in ROLES} for mid in manager_ids
    }
    # Map player_current_id -> manager_id for quick lookup
    pc_to_manager: dict[int, int | None] = {}
    for role in ROLES:
        for player in current_players[role]:
            pc_to_manager[player["id"]] = player["manager_id"]

    for _, pc_id, _, _ in assignments:
        mgr = pc_to_manager.get(pc_id)
        if mgr is not None:
            role = _player_role(current_players, pc_id)
            if role:
                assigned_map[mgr][role] += 1

    # Step 5 — fallback duplicates for uncovered slots
    assigned_pc_ids = {a[1] for a in assignments}
    unassigned: dict[str, list[dict]] = {}
    for role in ROLES:
        unassigned[role] = [
            p for p in current_players[role] if p["id"] not in assigned_pc_ids
        ]

    for manager_id in manager_ids:
        for role in ROLES:
            deficit = MIN_COVERAGE[role] - assigned_map[manager_id][role]
            if deficit <= 0:
                continue
            # find unassigned players of this role belonging to this manager
            candidates = [
                p for p in unassigned[role] if p["manager_id"] == manager_id
            ]
            full_pool = pools[role]
            if not full_pool:
                continue
            for player in candidates[:deficit]:
                historic_id = rng.choice(full_pool)
                assignments.append((league_id, player["id"], historic_id, 1))
                assigned_map[manager_id][role] += 1
                unassigned[role].remove(player)

    # Persist — single transaction (caller owns the connection)
    conn.execute("DELETE FROM alter_ego WHERE league_id = ?", (league_id,))
    conn.executemany(
        "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id, is_duplicate)"
        " VALUES (?, ?, ?, ?)",
        assignments,
    )
    conn.execute(
        "UPDATE league SET mapping_seed = ? WHERE id = ?", (seed, league_id)
    )

    duplicates = sum(1 for a in assignments if a[3] == 1)

    # Build coverage summary
    coverage: dict[int, dict[str, int]] = {
        mid: {role: 0 for role in ROLES} for mid in manager_ids
    }
    for _, pc_id, _, _ in assignments:
        mgr = pc_to_manager.get(pc_id)
        if mgr is not None:
            role = _player_role(current_players, pc_id)
            if role:
                coverage[mgr][role] += 1

    manager_names = {
        r["id"]: r["name"]
        for r in conn.execute(
            "SELECT id, name FROM manager WHERE league_id = ?", (league_id,)
        ).fetchall()
    }

    coverage_list = [
        {
            "manager_id": mid,
            "manager": manager_names.get(mid, str(mid)),
            **coverage[mid],
        }
        for mid in manager_ids
    ]

    return MappingResult(
        mapped=len(assignments),
        duplicates=duplicates,
        coverage_by_manager=coverage_list,
    )


def _player_role(current_players: dict[str, list[dict]], pc_id: int) -> str | None:
    for role, players in current_players.items():
        for p in players:
            if p["id"] == pc_id:
                return role
    return None


@dataclass
class PoolAssignmentResult:
    assigned_by_manager: list[dict] = field(default_factory=list)


def assign_nostalgia_pools(conn: sqlite3.Connection, league_id: int) -> PoolAssignmentResult:
    """Assign 12 historic nostalgia players (1P+4D+4C+3A) to each manager.

    Each role pool is shared across managers without replacement; if the pool
    runs out, we allow duplicates (same historic player to multiple managers).
    """
    league = conn.execute(
        "SELECT season_historic FROM league WHERE id = ?", (league_id,)
    ).fetchone()
    if league is None:
        raise ValueError("Lega non trovata")

    season_historic = league["season_historic"]

    pools: dict[str, list[int]] = {}
    for role in ROLES:
        rows = conn.execute(
            "SELECT id FROM player_historic WHERE season = ? AND role = ?",
            (season_historic, role),
        ).fetchall()
        pools[role] = [r["id"] for r in rows]

    managers = conn.execute(
        "SELECT id, name FROM manager WHERE league_id = ? ORDER BY id",
        (league_id,),
    ).fetchall()

    seed = str(random.random())
    rng = random.Random(seed)

    for role in ROLES:
        rng.shuffle(pools[role])

    assignments: list[tuple] = []  # (manager_id, league_id, player_historic_id)
    coverage: dict[int, dict[str, int]] = {}
    manager_names: dict[int, str] = {}

    role_cursors: dict[str, int] = {role: 0 for role in ROLES}

    for mgr in managers:
        mid = mgr["id"]
        manager_names[mid] = mgr["name"]
        coverage[mid] = {role: 0 for role in ROLES}
        for role, count in POOL_SIZE.items():
            pool = pools[role]
            if not pool:
                continue
            for _ in range(count):
                idx = role_cursors[role] % len(pool)
                role_cursors[role] += 1
                assignments.append((mid, league_id, pool[idx]))
                coverage[mid][role] += 1

    conn.execute("DELETE FROM manager_nostalgia_pool WHERE league_id = ?", (league_id,))
    conn.executemany(
        "INSERT INTO manager_nostalgia_pool (manager_id, league_id, player_historic_id) VALUES (?, ?, ?)",
        assignments,
    )
    conn.execute(
        "UPDATE league SET mapping_seed = ? WHERE id = ?", (seed, league_id)
    )

    result_list = [
        {"manager_id": mid, "manager": manager_names[mid], **coverage[mid]}
        for mid in [mgr["id"] for mgr in managers]
    ]
    return PoolAssignmentResult(assigned_by_manager=result_list)


def auto_assign_remaining(conn: sqlite3.Connection, league_id: int) -> None:
    """For every manager with assignments_locked=0, auto-assign nostalgia players
    using titularity order (starts_current_season DESC) as fallback, then lock them.
    """
    managers = conn.execute(
        "SELECT id FROM manager WHERE league_id = ? AND (assignments_locked = 0 OR assignments_locked IS NULL)",
        (league_id,),
    ).fetchall()

    for mgr_row in managers:
        mid = mgr_row["id"]

        unassigned = conn.execute(
            """
            SELECT mnp.id AS pool_id, mnp.player_historic_id, ph.role
            FROM manager_nostalgia_pool mnp
            JOIN player_historic ph ON ph.id = mnp.player_historic_id
            WHERE mnp.manager_id = ? AND mnp.assigned_player_current_id IS NULL
            ORDER BY ph.role
            """,
            (mid,),
        ).fetchall()

        already_assigned_pc_ids = {
            r["assigned_player_current_id"]
            for r in conn.execute(
                "SELECT assigned_player_current_id FROM manager_nostalgia_pool WHERE manager_id = ? AND assigned_player_current_id IS NOT NULL",
                (mid,),
            ).fetchall()
        }

        for pool_entry in unassigned:
            role = pool_entry["role"]
            candidates = conn.execute(
                """
                SELECT pc.id FROM player_current pc
                WHERE pc.league_id = ? AND pc.manager_id = ? AND pc.role = ?
                ORDER BY pc.starts_current_season DESC
                """,
                (league_id, mid, role),
            ).fetchall()

            chosen = None
            for cand in candidates:
                if cand["id"] not in already_assigned_pc_ids:
                    chosen = cand["id"]
                    break

            if chosen is None and candidates:
                chosen = candidates[0]["id"]

            if chosen is not None:
                conn.execute(
                    "UPDATE manager_nostalgia_pool SET assigned_player_current_id = ? WHERE id = ?",
                    (chosen, pool_entry["pool_id"]),
                )
                already_assigned_pc_ids.add(chosen)

        _flush_alter_ego_for_manager(conn, league_id, mid)
        conn.execute(
            "UPDATE manager SET assignments_locked = 1 WHERE id = ?", (mid,)
        )

    conn.execute(
        "UPDATE league SET associations_closed = 1, associations_closed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (league_id,),
    )


def _flush_alter_ego_for_manager(conn: sqlite3.Connection, league_id: int, manager_id: int) -> None:
    """Write manager_nostalgia_pool assignments into alter_ego table."""
    pc_ids = [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM player_current WHERE league_id = ? AND manager_id = ?",
            (league_id, manager_id),
        ).fetchall()
    ]
    if pc_ids:
        placeholders = ",".join("?" * len(pc_ids))
        conn.execute(
            f"DELETE FROM alter_ego WHERE league_id = ? AND player_current_id IN ({placeholders})",
            [league_id] + pc_ids,
        )

    rows = conn.execute(
        """
        SELECT assigned_player_current_id, player_historic_id
        FROM manager_nostalgia_pool
        WHERE manager_id = ? AND assigned_player_current_id IS NOT NULL
        """,
        (manager_id,),
    ).fetchall()

    conn.executemany(
        "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id, is_duplicate) VALUES (?, ?, ?, 0)",
        [(league_id, r["assigned_player_current_id"], r["player_historic_id"]) for r in rows],
    )
