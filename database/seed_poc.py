#!/usr/bin/env python3
"""
Seed POC — popola il database con dati di test per la pipeline FantaNostalgia.
Eseguire: python database/seed_poc.py
Idempotente: cancella e ricrea tutto ad ogni esecuzione.
"""
import random
import sqlite3
from pathlib import Path

random.seed(42)

DB_PATH = Path(__file__).parent / "fantanostalgia.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

MANAGER_NAMES = ["Simone", "Marco", "Luca", "Andrea", "Paolo", "Matteo", "Giorgio", "Filippo"]

SQUADRE = [
    "Milano FC", "Roma United", "Torino Sport", "Napoli Calcio", "Juventus Bianca",
    "Lazio Azzurra", "Fiorentina Viola", "Atalanta Nerazzurra", "Bologna FC", "Sampdoria Blu",
    "Genoa Rossoblu", "Cagliari Isolano", "Verona FC", "Udinese Bianconero", "Sassuolo Verde",
    "Empoli Azzurro", "Lecce Giallorosso", "Monza Biancorossa", "Frosinone Gialloblu", "Venezia FC",
]

SQUADRE_STORICHE = [
    "Inter Milano 02", "Juventus 02", "Roma 02", "Lazio 02", "Milan 02",
    "Parma 02", "Bologna 02", "Udinese 02", "Chievo 02", "Atalanta 02",
    "Brescia 02", "Torino 02", "Empoli 02", "Modena 02", "Piacenza 02",
    "Perugia 02", "Como 02", "Reggina 02", "Siena 02", "Lecce 02",
]

COGNOMI = [
    "Rossi", "Bianchi", "Ferrari", "Esposito", "Romano", "Colombo", "Ricci", "Marino",
    "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini", "Costa", "Giordano",
    "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana", "Santoro", "Mariani", "Rinaldi",
    "Caruso", "Ferrara", "Galli", "Martini", "Leone", "Longo", "Gentile", "Serra",
    "Conte", "Guerra", "Vitale", "Villa", "Castelli", "Amato", "Russo", "Bruno",
]

COGNOMI_STORICI = [
    "Del Vecchio", "Ferretti", "Montanari", "Castellucci", "Paolini", "Trentini",
    "Zampieri", "Cacciatori", "Bellotti", "Damiani", "Marchetti", "Furlani",
    "Basile", "Capello", "D'Amico", "Pellegrini", "Vitali", "Morano",
    "Castagna", "Profumo", "Cannavaro", "Albertini", "Vieri", "Totti",
    "Nedved", "Zanetti", "Buffon", "Nesta", "Maldini", "Pirlo",
    "Del Piero", "Crespo", "Recoba", "Seedorf", "Nakata", "Batistuta",
    "Zidane", "Ronaldo", "Bergkamp", "Rivaldo",
]

INIZIALI = list("ABCDEFGHILMNOPRSTV")

MATCHDAY_DRAWS = [(1, 12), (2, 7), (3, 28), (4, 3), (5, 19)]

# Distribuzione ruoli
ROLE_COUNTS_CURRENT = [("P", 12), ("D", 40), ("C", 40), ("A", 28)]
ROLE_COUNTS_HISTORIC = [("P", 10), ("D", 32), ("C", 32), ("A", 26)]

QUOTAZIONE_RANGE = {"P": (1, 20), "D": (1, 25), "C": (1, 30), "A": (1, 40)}
GOL_PROB = {"A": 0.15, "C": 0.07, "D": 0.03, "P": 0.005}
GOL_BONUS = {"A": 3.0, "C": 3.5, "D": 4.0, "P": 3.0}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())


def reset(conn: sqlite3.Connection) -> None:
    tables = [
        "standings", "matchday_score", "lineup", "historic_rating",
        "alter_ego", "matchday_draw", "player_historic", "player_current",
        "manager", "league",
    ]
    for t in tables:
        conn.execute(f"DELETE FROM {t}")
    try:
        for t in tables:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (t,))
    except sqlite3.OperationalError:
        pass
    conn.commit()


def make_name(pool: list, idx: int) -> str:
    return f"{pool[idx % len(pool)]} {INIZIALI[idx % len(INIZIALI)]}."


def calc_fantasy(rating, role, goals, assists, yellows, reds, own_goals,
                 pen_missed, pen_saved, goals_conceded) -> float:
    if rating is None:
        return 0.0
    score = float(rating)
    score += GOL_BONUS[role] * goals
    score += 1.0 * assists
    score -= 0.5 * yellows
    score -= 1.0 * reds
    score -= 1.0 * own_goals
    score -= 3.0 * pen_missed
    if role == "P":
        score += 1.0 * pen_saved
        score -= 1.0 * (goals_conceded // 2)
    return round(score, 1)


def seed_historic_rating(conn, pid, role, matchday):
    """Genera un voto storico per un giocatore in una giornata. Restituisce la tupla dati."""
    if random.random() >= 0.80:
        conn.execute(
            "INSERT INTO historic_rating "
            "(player_historic_id, matchday, rating, goals, assists, yellow_cards, red_cards, "
            "own_goals, penalties_scored, penalties_missed, goals_conceded, source) "
            "VALUES (?, ?, NULL, 0, 0, 0, 0, 0, 0, 0, 0, 'synthetic')",
            (pid, matchday),
        )
        return (None, 0, 0, 0, 0, 0, 0, 0, 0)

    rating = round(random.uniform(4.5, 8.5), 1)
    goals = 1 if random.random() < GOL_PROB[role] else 0
    assists = 1 if random.random() < 0.15 else 0
    yellows = 1 if random.random() < 0.10 else 0
    reds = 1 if (random.random() < 0.02 and not yellows) else 0
    own_goals = 1 if random.random() < 0.01 else 0
    pen_missed = 1 if random.random() < 0.01 else 0
    pen_saved = (1 if random.random() < 0.05 else 0) if role == "P" else 0
    goals_conceded = (
        random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0] if role == "P" else 0
    )

    conn.execute(
        "INSERT INTO historic_rating "
        "(player_historic_id, matchday, rating, goals, assists, yellow_cards, red_cards, "
        "own_goals, penalties_scored, penalties_missed, goals_conceded, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synthetic')",
        (pid, matchday, rating, goals, assists, yellows, reds, own_goals, pen_saved, pen_missed, goals_conceded),
    )
    return (rating, goals, assists, yellows, reds, own_goals, pen_missed, pen_saved, goals_conceded)


def main():
    conn = get_conn()
    init_schema(conn)
    reset(conn)

    # 1. Lega
    cur = conn.execute(
        "INSERT INTO league (name, season_current, season_historic, budget) VALUES (?, ?, ?, ?)",
        ("Lega Test 2024/25", "2024/25", "2002/03", 500),
    )
    league_id = cur.lastrowid

    # 2. Manager
    manager_ids = []
    for name in MANAGER_NAMES:
        cur = conn.execute(
            "INSERT INTO manager (league_id, name, team_name) VALUES (?, ?, ?)",
            (league_id, name, f"{name} FC"),
        )
        manager_ids.append(cur.lastrowid)

    # 3. Giocatori attuali (120 totali, ~15 per manager)
    # player_current_id -> (role, manager_id, starts)
    current_players: dict[int, tuple] = {}

    name_idx = 0
    for role, count in ROLE_COUNTS_CURRENT:
        q_min, q_max = QUOTAZIONE_RANGE[role]
        for i in range(count):
            mgr_id = manager_ids[i % 8]
            name = make_name(COGNOMI, name_idx)
            squadra = SQUADRE[name_idx % len(SQUADRE)]
            quotazione = random.randint(q_min, q_max)
            # Titolari tendenziali nei primi 60% per ruolo
            starts = random.randint(18, 30) if i < int(count * 0.6) else random.randint(0, 10)
            cur = conn.execute(
                "INSERT INTO player_current "
                "(league_id, name, role, team, quotation, starts_current_season, manager_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (league_id, name, role, squadra, quotazione, starts, mgr_id),
            )
            current_players[cur.lastrowid] = (role, mgr_id, starts)
            name_idx += 1

    # 4. Giocatori storici (100 totali)
    # player_historic_id -> role
    historic_players: dict[int, str] = {}

    hist_idx = 0
    for role, count in ROLE_COUNTS_HISTORIC:
        for i in range(count):
            name = make_name(COGNOMI_STORICI, hist_idx)
            squadra = SQUADRE_STORICHE[hist_idx % len(SQUADRE_STORICHE)]
            cur = conn.execute(
                "INSERT INTO player_historic (name, role, team, season, source) VALUES (?, ?, ?, ?, ?)",
                (name, role, squadra, "2002/03", "synthetic"),
            )
            historic_players[cur.lastrowid] = role
            hist_idx += 1

    # 5. Voti storici (34 giornate per ogni giocatore storico)
    # (pid, matchday) -> (rating, goals, assists, yellows, reds, own_goals, pen_missed, pen_saved, goals_conceded)
    historic_ratings: dict[tuple, tuple] = {}

    for pid, role in historic_players.items():
        for matchday in range(1, 35):
            historic_ratings[(pid, matchday)] = seed_historic_rating(conn, pid, role, matchday)

    # 6. Mapping alter ego
    # Per ruolo: ordina current per starts DESC, assegna random da pool storico, duplicati come fallback
    historic_by_role: dict[str, list] = {}
    for pid, role in historic_players.items():
        historic_by_role.setdefault(role, []).append(pid)

    alter_ego_map: dict[int, tuple] = {}  # current_pid -> (historic_pid, is_duplicate)

    for role in ["P", "D", "C", "A"]:
        current_of_role = sorted(
            [(pid, data[2]) for pid, data in current_players.items() if data[0] == role],
            key=lambda x: x[1],
            reverse=True,
        )
        pool = list(historic_by_role.get(role, []))
        random.shuffle(pool)
        pool_idx = 0

        for pid, _ in current_of_role:
            if pool_idx < len(pool):
                hist_pid = pool[pool_idx]
                pool_idx += 1
                is_dup = 0
            else:
                hist_pid = random.choice(pool)
                is_dup = 1
            alter_ego_map[pid] = (hist_pid, is_dup)
            conn.execute(
                "INSERT INTO alter_ego (league_id, player_current_id, player_historic_id, is_duplicate) "
                "VALUES (?, ?, ?, ?)",
                (league_id, pid, hist_pid, is_dup),
            )

    # 7. Sorteggi giornate
    for md_current, md_historic in MATCHDAY_DRAWS:
        conn.execute(
            "INSERT INTO matchday_draw (league_id, matchday_current, matchday_historic) VALUES (?, ?, ?)",
            (league_id, md_current, md_historic),
        )

    # 8. Formazioni: per ogni manager, top-11 per starts come titolari, resto riserve
    players_by_manager: dict[int, list] = {}
    for pid, (role, mgr_id, starts) in current_players.items():
        players_by_manager.setdefault(mgr_id, []).append((pid, role, starts))

    for mgr_id, players in players_by_manager.items():
        sorted_players = sorted(players, key=lambda x: x[2], reverse=True)
        starters = sorted_players[:11]
        subs = sorted_players[11:]
        for md_current, _ in MATCHDAY_DRAWS:
            for pid, _, _ in starters:
                conn.execute(
                    "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter) "
                    "VALUES (?, ?, ?, ?, 1)",
                    (league_id, mgr_id, md_current, pid),
                )
            for pid, _, _ in subs:
                conn.execute(
                    "INSERT INTO lineup (league_id, manager_id, matchday, player_current_id, is_starter) "
                    "VALUES (?, ?, ?, ?, 0)",
                    (league_id, mgr_id, md_current, pid),
                )

    # 9. Punteggi e classifica
    total_normal: dict[int, float] = {mid: 0.0 for mid in manager_ids}
    total_nostalgia: dict[int, float] = {mid: 0.0 for mid in manager_ids}

    for md_current, md_historic in MATCHDAY_DRAWS:
        for mgr_id, players in players_by_manager.items():
            starters = sorted(players, key=lambda x: x[2], reverse=True)[:11]

            score_normal = 0.0
            score_nostalgia = 0.0

            for pid, role, _ in starters:
                # Punteggio normale: voti correnti simulati
                if random.random() < 0.80:
                    nr = round(random.uniform(4.5, 8.5), 1)
                    ng = 1 if random.random() < GOL_PROB[role] else 0
                    na = 1 if random.random() < 0.15 else 0
                    ny = 1 if random.random() < 0.10 else 0
                    nrd = 1 if (random.random() < 0.02 and not ny) else 0
                    score_normal += calc_fantasy(nr, role, ng, na, ny, nrd, 0, 0, 0, 0)

                # Punteggio nostalgia: alter ego nella giornata storica sorteggiata
                if pid in alter_ego_map:
                    hist_pid, _ = alter_ego_map[pid]
                    hr = historic_ratings.get((hist_pid, md_historic),
                                              (None, 0, 0, 0, 0, 0, 0, 0, 0))
                    score_nostalgia += calc_fantasy(hr[0], role, hr[1], hr[2], hr[3], hr[4],
                                                    hr[5], hr[6], hr[7], hr[8])

            conn.execute(
                "INSERT INTO matchday_score "
                "(league_id, manager_id, matchday, score_normal, score_nostalgia) "
                "VALUES (?, ?, ?, ?, ?)",
                (league_id, mgr_id, md_current, round(score_normal, 1), round(score_nostalgia, 1)),
            )
            total_normal[mgr_id] += score_normal
            total_nostalgia[mgr_id] += score_nostalgia

    # Standings
    rank_n = {mid: r + 1 for r, (mid, _) in
              enumerate(sorted(total_normal.items(), key=lambda x: x[1], reverse=True))}
    rank_nos = {mid: r + 1 for r, (mid, _) in
                enumerate(sorted(total_nostalgia.items(), key=lambda x: x[1], reverse=True))}

    for mgr_id in manager_ids:
        conn.execute(
            "INSERT INTO standings "
            "(league_id, manager_id, total_score_normal, total_score_nostalgia, rank_normal, rank_nostalgia) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (league_id, mgr_id,
             round(total_normal[mgr_id], 1), round(total_nostalgia[mgr_id], 1),
             rank_n[mgr_id], rank_nos[mgr_id]),
        )

    conn.commit()
    conn.close()
    print_summary()


def print_summary() -> None:
    conn = get_conn()

    n_current = conn.execute("SELECT COUNT(*) FROM player_current").fetchone()[0]
    n_historic = conn.execute("SELECT COUNT(*) FROM player_historic").fetchone()[0]
    n_alter_ego = conn.execute("SELECT COUNT(*) FROM alter_ego").fetchone()[0]
    n_duplicates = conn.execute("SELECT COUNT(*) FROM alter_ego WHERE is_duplicate = 1").fetchone()[0]
    n_ratings = conn.execute("SELECT COUNT(*) FROM historic_rating WHERE rating IS NOT NULL").fetchone()[0]

    print("\n=== Seed POC completato ===")
    print(f"Giocatori attuali:   {n_current}")
    print(f"Giocatori storici:   {n_historic}")
    print(f"Alter ego totali:    {n_alter_ego}")
    print(f"Alter ego duplicati: {n_duplicates}")
    print(f"Voti storici:        {n_ratings}/3400")

    print("\n--- Classifica Normale ---")
    rows = conn.execute("""
        SELECT m.name, s.total_score_normal, s.rank_normal
        FROM standings s JOIN manager m ON m.id = s.manager_id
        ORDER BY s.rank_normal
    """).fetchall()
    for r in rows:
        print(f"  {r['rank_normal']}. {r['name']:<12} {r['total_score_normal']:.1f}")

    print("\n--- Classifica FantaNostalgia ---")
    rows = conn.execute("""
        SELECT m.name, s.total_score_nostalgia, s.rank_nostalgia
        FROM standings s JOIN manager m ON m.id = s.manager_id
        ORDER BY s.rank_nostalgia
    """).fetchall()
    for r in rows:
        print(f"  {r['rank_nostalgia']}. {r['name']:<12} {r['total_score_nostalgia']:.1f}")

    conn.close()


if __name__ == "__main__":
    main()
