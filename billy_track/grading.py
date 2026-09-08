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


def fetch_scoreboard(sport, event_date, groups=None):
    path = SPORT_PATHS[sport]
    yyyymmdd = event_date.replace("-", "")
    params = {"dates": yyyymmdd, "limit": 400}
    if groups:
        params["groups"] = groups
    url = f"{ESPN_BASE}/{path}/scoreboard"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _find_in_scoreboard(data, away, home):
    """Match by the API's own homeAway side, then just confirm the name looks
    right for that side. Matching each query name freely against BOTH
    competitors (the old approach) breaks whenever one team's name is a
    substring of the other's -- e.g. "Michigan" is contained in "Western
    Michigan" -- which can make away_c and home_c resolve to the SAME
    competitor and silently duplicate one team's score onto both sides."""
    for ev in data.get("events", []):
        comp = ev["competitions"][0]
        competitors = comp["competitors"]
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), None)
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), None)
        if away_c is None or home_c is None:
            continue
        if not _team_matches(away_c["team"], away) or not _team_matches(home_c["team"], home):
            continue

        completed = ev["status"]["type"]["completed"]
        result = {"completed": completed}
        for key, c in (("away", away_c), ("home", home_c)):
            score = int(c["score"]) if c.get("score") not in (None, "") else None
            linescores = c.get("linescores") or []
            by_period = {
                int(ls["period"]): int(float(ls["value"])) for ls in linescores if ls.get("period")
            }
            result[key] = {"score": score, "by_period": by_period}
        return result
    return None


def game_result(sport, event_date, away, home):
    """Find the game and return completed flag + score/period-scores for each side.
    ESPN's default scoreboard response is limited to the top-billed games for the
    day (no explicit limit), and college football splits FBS/FCS into separate
    'groups' -- a plain default-params request silently misses plenty of real
    games, so try the full-limit request first, then fall back to FCS (cfb only)
    before giving up."""
    data = fetch_scoreboard(sport, event_date)
    result = _find_in_scoreboard(data, away, home)
    if result is None and sport == "cfb":
        data = fetch_scoreboard(sport, event_date, groups=81)  # FCS
        result = _find_in_scoreboard(data, away, home)
    if result is None:
        raise GameNotFound(f"No {sport} game found for {away} @ {home} on {event_date}")
    return result


def _period_score(side, period):
    """side: {'score': int|None, 'by_period': {1: x, 2: y, ...}}. period: 'full' | '1h' | '1q'."""
    if period == "full":
        return side["score"]
    if period == "1q":
        return side["by_period"].get(1)
    if period == "1h":
        if not side["by_period"]:
            return None
        return side["by_period"].get(1, 0) + side["by_period"].get(2, 0)
    raise ValueError(f"Unknown period: {period!r}")


def _selection_side(leg):
    """Same substring pitfall as _team_matches ("Michigan" is contained in
    "Western Michigan"), so require an exact match first -- true for every
    leg we transcribe, since the selection is always typed to equal one of
    the two team names exactly -- before ever falling back to fuzzy matching."""
    sel = leg["selection"].strip().lower()
    away = leg["away"].strip().lower()
    home = leg["home"].strip().lower()
    if sel == away:
        return "away"
    if sel == home:
        return "home"
    if sel in away.split() or away in sel:
        return "away"
    if sel in home.split() or home in sel:
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

    period = leg.get("period", "full")
    away_score = _period_score(gr["away"], period)
    home_score = _period_score(gr["home"], period)

    if away_score is None or home_score is None:
        # e.g. a 1st-half/1st-quarter line but that period wasn't reported for this game
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
