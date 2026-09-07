"""Look up final scores from ESPN's public scoreboard API and grade bet legs against them."""

import requests

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

SPORT_PATHS = {
    "cfb": "football/college-football",
    "nfl": "football/nfl",
    "nba": "basketball/nba",
    "cbb": "basketball/mens-college-basketball",
    "wcbb": "basketball/womens-college-basketball",
    "mlb": "baseball/mlb",
    "nhl": "hockey/nhl",
}


class GameNotFound(Exception):
    pass


def _team_matches(team, name):
    name = name.lower()
    candidates = [
        team.get("displayName", ""),
        team.get("shortDisplayName", ""),
        team.get("location", ""),
        team.get("name", ""),
        team.get("abbreviation", ""),
    ]
    return any(name in c.lower() or c.lower() in name for c in candidates if c)


def fetch_scoreboard(sport, event_date):
    path = SPORT_PATHS[sport]
    yyyymmdd = event_date.replace("-", "")
    url = f"{ESPN_BASE}/{path}/scoreboard?dates={yyyymmdd}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def game_result(sport, event_date, away, home):
    """Find the game and return completed flag + score/first-half-score for each side."""
    data = fetch_scoreboard(sport, event_date)
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        competitors = comp["competitors"]
        away_c = next((c for c in competitors if _team_matches(c["team"], away)), None)
        home_c = next((c for c in competitors if _team_matches(c["team"], home)), None)
        if away_c is None or home_c is None:
            continue

        completed = ev["status"]["type"]["completed"]
        result = {"completed": completed}
        for key, c in (("away", away_c), ("home", home_c)):
            score = int(c["score"]) if c.get("score") not in (None, "") else None
            linescores = c.get("linescores") or []
            first_half = None
            if linescores:
                first_half = sum(
                    int(float(ls["value"])) for ls in linescores if ls.get("period") in (1, 2)
                )
            result[key] = {"score": score, "first_half_score": first_half}
        return result

    raise GameNotFound(f"No {sport} game found for {away} @ {home} on {event_date}")


def _selection_side(leg):
    sel = leg["selection"].lower()
    if sel in leg["away"].lower() or leg["away"].lower() in sel:
        return "away"
    if sel in leg["home"].lower() or leg["home"].lower() in sel:
        return "home"
    raise ValueError(f"Selection '{leg['selection']}' doesn't match either team in the leg")


def grade_leg(leg):
    """leg is a dict with sport/event_date/away/home/market/period/selection/line.
    Returns (result, away_score, home_score) using whichever score (full game or
    first half) the leg's period calls for."""
    try:
        gr = game_result(leg["sport"], leg["event_date"], leg["away"], leg["home"])
    except GameNotFound:
        return "unknown", None, None

    if not gr["completed"]:
        return "pending", None, None

    score_key = "first_half_score" if leg.get("period", "full") == "1h" else "score"
    away_score = gr["away"][score_key]
    home_score = gr["home"][score_key]

    if away_score is None or home_score is None:
        # e.g. a 1st-half line but linescores weren't reported for this game
        return "unknown", away_score, home_score

    market = leg["market"]

    if market == "moneyline":
        side = _selection_side(leg)
        my_score, opp_score = (away_score, home_score) if side == "away" else (home_score, away_score)
        result = "won" if my_score > opp_score else ("push" if my_score == opp_score else "lost")

    elif market == "spread":
        side = _selection_side(leg)
        my_score, opp_score = (away_score, home_score) if side == "away" else (home_score, away_score)
        cover = (my_score - opp_score) + leg["line"]
        result = "won" if cover > 0 else ("push" if cover == 0 else "lost")

    elif market == "total":
        total = away_score + home_score
        sel = leg["selection"].lower()
        if sel not in ("over", "under"):
            raise ValueError(f"Total selection must be 'over'/'under', got {leg['selection']!r}")
        if total == leg["line"]:
            result = "push"
        else:
            result = "won" if (sel == "over") == (total > leg["line"]) else "lost"

    else:
        raise ValueError(f"Unknown market: {market!r}")

    return result, away_score, home_score


def grade_bet(leg_rows):
    """Given the already-graded result strings for every leg of one bet, decide the
    bet's overall result. A parlay needs every leg to hit; a push leg doesn't sink it
    (this is a simplification - real sportsbooks recompute parlay odds when a leg
    pushes, but we're just tracking win/loss for fun, not settling real payouts)."""
    statuses = [row["result"] for row in leg_rows]
    if "unknown" in statuses:
        return "unknown"
    if "lost" in statuses:
        return "lost"
    if "pending" in statuses:
        return "pending"
    if all(s == "push" for s in statuses):
        return "push"
    return "won"
