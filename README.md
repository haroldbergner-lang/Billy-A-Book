# Billy-A-Book — bet slip tracker

A personal, for-fun tracker for a family friend's BetMGM bets. No money changes
hands between you and him — this just scores his real bet slips against final
scores so you can see his record, hit rate by market type, and profit/loss
over time.

## How it works

1. Once a week he texts you screenshots of his bet slips.
2. You (or Claude, reading the screenshots) transcribe each slip into a JSON
   file matching the schema in `sample_week.json` — one entry per bet, with
   its legs (game, market, selection, line).
3. Run `add-week`, which loads the week into the database and immediately
   tries to grade every leg against final scores pulled from ESPN's public
   scoreboard API (no API key needed).
4. Run `report` any time to see his stats.

Games that haven't finished yet come back as `pending`; run `grade` again
later (e.g. next weekly batch) to pick up final scores for those.

## Setup

```
pip install -r requirements.txt
```

## Usage

```
python -m billy_track add-week sample_week.json
python -m billy_track report
python -m billy_track grade              # re-check any still-pending bets
python -m billy_track report --week 2026-09-07
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
