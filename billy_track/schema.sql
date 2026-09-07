CREATE TABLE IF NOT EXISTS weeks (
    id INTEGER PRIMARY KEY,
    label TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES weeks(id),
    type TEXT NOT NULL,        -- 'straight' | 'parlay'
    tag TEXT,                  -- 'SGP+', 'SGP', or NULL
    odds INTEGER NOT NULL,     -- american odds for the whole bet
    stake REAL NOT NULL,
    payout REAL,               -- potential payout shown on the slip
    result TEXT NOT NULL DEFAULT 'pending'  -- won | lost | push | pending | unknown
);

CREATE TABLE IF NOT EXISTS legs (
    id INTEGER PRIMARY KEY,
    bet_id INTEGER NOT NULL REFERENCES bets(id),
    sport TEXT NOT NULL,
    event_date TEXT NOT NULL,
    away TEXT NOT NULL,
    home TEXT NOT NULL,
    market TEXT NOT NULL,      -- moneyline | spread | total
    period TEXT NOT NULL DEFAULT 'full',  -- full | 1h | 1q
    selection TEXT NOT NULL,   -- team name, or 'over'/'under'
    line REAL,                 -- spread/total number; NULL for moneyline
    result TEXT NOT NULL DEFAULT 'pending',
    away_score INTEGER,
    home_score INTEGER
);
