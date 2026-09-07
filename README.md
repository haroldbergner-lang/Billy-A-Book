# Billy-A-Book — bet slip tracker

**Live dashboard:** https://claude.ai/code/artifact/6bb16501-613e-444e-bffd-e4b7f3aff071
(bookmark this — it updates whenever a new week is pushed, no need to reopen a session to check his record)

**Standalone dashboard:** `dashboard.html` in this repo. Same page, but with the
data baked in at generation time instead of fetched live — open it directly in
a browser (`file://`), no claude.ai account needed. It won't auto-update; run
`python -m billy_track render-html` and commit the result after each week.
This is also what you'd host on GitHub Pages if you want a plain shareable URL
instead of the claude.ai link (e.g. to send to him directly).

A personal, for-fun tracker for a family friend's BetMGM bets. No money changes
hands between you and him — this just scores his real bet slips against final
scores so you can see his record, running balance, and hit rate by market type
over time. The dashboard shows record/balance/ROI; `report` on the command line
also breaks it down by market (moneyline/spread/total).

Starting balance lives in `config.json` (`{"starting_balance": 270.74}`) — the
dashboard's Balance figure is that number plus/minus every settled bet since.
Edit it if he tells you his actual starting bankroll changed.

## How it works

1. Once a week he texts you screenshots of his bet slips.
2. Open a Claude Code session on this repo/branch (this can be a brand new
   session each time -- it doesn't need to be the same one as last week) and
   paste the screenshots in.
3. Claude transcribes each slip into a JSON file at `weeks/<date>.json`,
   matching the schema below, and runs `add-week` to grade it against final
   scores pulled from ESPN's public scoreboard API (no API key needed).
4. Claude commits `weeks/<date>.json` and pushes it. **This is the important
   part**: the `weeks/*.json` files are the permanent record. The SQLite
   database (`data/bets.db`) is a throwaway local cache -- it is gitignored
   and is rebuilt from `weeks/*.json` any time (e.g. after this session's
   container gets recycled, or in a brand new session).
5. Claude runs `report --json` and `dump`, and pushes the results into the
   dashboard artifact's database (see link above) so it's up to date without
   you needing to open a session just to check his record.

Games that haven't finished yet come back as `pending`; run `grade` again
later (e.g. next weekly batch) to pick up final scores for those.

## Setup

```
pip install -r requirements.txt
python -m billy_track rebuild    # (re)builds data/bets.db from weeks/*.json
```

## Usage

```
python -m billy_track rebuild                    # rebuild the DB from every file in weeks/
python -m billy_track add-week weeks/2026-09-07.json   # add one new week and grade it
python -m billy_track grade                      # re-check any still-pending bets
python -m billy_track report                     # all-time stats
python -m billy_track report --week 2026-09-07   # one week's stats
python -m billy_track report --json              # machine-readable, for pushing to the live dashboard
python -m billy_track dump                       # full week/bet/leg detail with scores, same purpose
python -m billy_track render-html                # writes dashboard.html with current data baked in
```

## Bet JSON schema

```jsonc
{
  "week_label": "2026-09-07",
  "bets": [
    {
      "type": "straight" | "parlay",
      "tag": "SGP+" | "SGP" | null,
      "odds": 477,          // american odds for the whole bet, as shown on the slip
      "stake": 20.00,
      "payout": 115.56,     // potential payout shown on the slip
      "legs": [
        {
          "sport": "cfb",   // cfb | nfl | nba | cbb | wcbb | mlb | nhl
          "event_date": "2026-09-03",   // date of the game, YYYY-MM-DD
          "away": "Colorado",
          "home": "Georgia Tech",
          "market": "moneyline" | "spread" | "total",
          "period": "full" | "1h",      // omit for full game
          "selection": "Georgia Tech",  // team name, or "over"/"under" for totals
          "line": -20.5                 // spread/total number; omit for moneyline
        }
      ]
    }
  ]
}
```

A `"straight"` bet has exactly one leg. A `"parlay"` needs every leg to win —
if any leg loses, the whole bet is graded `lost`, matching how sportsbooks
actually settle parlays. (One simplification: a pushed leg inside a parlay
doesn't sink it here, but we don't recompute the reduced odds the way a real
book would — this is for tracking his record, not settling real payouts.)

## Grading notes

Game results come from ESPN's public scoreboard endpoint, matched by team
name and date. If a game can't be found (bad date, unusual team name) the
leg is graded `unknown` — check the JSON for typos and re-run `grade`.
