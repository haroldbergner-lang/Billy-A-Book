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
    market TEXT NOT NULL,      -- moneyline | spread | total | winning_margin | player_prop
    period TEXT NOT NULL DEFAULT 'full',  -- full | 1h | 1q
    selection TEXT NOT NULL,   -- team name, prop description, or 'over'/'under'
    line REAL,                 -- spread/total number; NULL for moneyline/winning_margin/player_prop
    margin_low INTEGER,        -- winning_margin range; NULL for other markets
    margin_high INTEGER,       -- winning_margin range; NULL for other markets
    player TEXT,                -- player_prop only: exact ESPN box score display name
    stat TEXT,                  -- player_prop only: rush_yds | rec_yds | rush_rec_yds | receptions | pass_yds | pass_tds | anytime_td
    threshold REAL,              -- player_prop only: the line, e.g. 125 for "125+"
    comparison TEXT,             -- player_prop only: gte | gt | lte | lt
    manual_result TEXT,        -- player_prop escape hatch: a researched result ('won'/'lost'/'push') for a prop shape grading.py can't parse yet
    result TEXT NOT NULL DEFAULT 'pending',
    away_score INTEGER,
    home_score INTEGER
);
