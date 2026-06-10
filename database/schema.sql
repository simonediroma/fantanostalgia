-- FantaNostalgia Database Schema
-- NON MODIFICARE senza approvazione esplicita (vedi CLAUDE.md)

CREATE TABLE IF NOT EXISTS league (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    season_current TEXT NOT NULL,
    season_historic TEXT NOT NULL,
    budget INTEGER DEFAULT 500,
    buste_aperte INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manager (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    name TEXT NOT NULL,
    team_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_current (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('P', 'D', 'C', 'A')),
    team TEXT NOT NULL,
    quotation INTEGER DEFAULT 1,
    starts_current_season INTEGER DEFAULT 0,
    manager_id INTEGER REFERENCES manager(id)
);

CREATE TABLE IF NOT EXISTS player_historic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('P', 'D', 'C', 'A')),
    team TEXT NOT NULL,
    season TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('archive', 'synthetic'))
);

CREATE TABLE IF NOT EXISTS alter_ego (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    player_current_id INTEGER REFERENCES player_current(id),
    player_historic_id INTEGER REFERENCES player_historic(id),
    is_duplicate INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matchday_draw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    matchday_current INTEGER NOT NULL,
    matchday_historic INTEGER NOT NULL,
    drawn_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historic_rating (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_historic_id INTEGER REFERENCES player_historic(id),
    matchday INTEGER NOT NULL,
    rating REAL,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_scored INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    source TEXT NOT NULL CHECK(source IN ('archive', 'synthetic')),
    UNIQUE(player_historic_id, matchday)
);

CREATE TABLE IF NOT EXISTS lineup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    manager_id INTEGER REFERENCES manager(id),
    matchday INTEGER NOT NULL,
    player_current_id INTEGER REFERENCES player_current(id),
    is_starter INTEGER DEFAULT 1,
    locked_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matchday_score (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    manager_id INTEGER REFERENCES manager(id),
    matchday INTEGER NOT NULL,
    score_normal REAL DEFAULT 0,
    score_nostalgia REAL DEFAULT 0,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league_id, manager_id, matchday)
);

CREATE TABLE IF NOT EXISTS standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES league(id),
    manager_id INTEGER REFERENCES manager(id),
    total_score_normal REAL DEFAULT 0,
    total_score_nostalgia REAL DEFAULT 0,
    rank_normal INTEGER,
    rank_nostalgia INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league_id, manager_id)
);

CREATE INDEX IF NOT EXISTS idx_player_current_league ON player_current(league_id);
CREATE INDEX IF NOT EXISTS idx_player_current_role ON player_current(role);
CREATE INDEX IF NOT EXISTS idx_player_historic_season ON player_historic(season);
CREATE INDEX IF NOT EXISTS idx_historic_rating_player ON historic_rating(player_historic_id);
CREATE INDEX IF NOT EXISTS idx_alter_ego_league ON alter_ego(league_id);
CREATE INDEX IF NOT EXISTS idx_standings_league ON standings(league_id);
