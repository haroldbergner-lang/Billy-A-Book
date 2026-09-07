import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bets.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def insert_week(conn, label, week_data):
    cur = conn.execute(
        "INSERT INTO weeks (label, created_at) VALUES (?, ?)",
        (label, datetime.datetime.utcnow().isoformat()),
    )
    week_id = cur.lastrowid

    for bet in week_data["bets"]:
        cur = conn.execute(
            "INSERT INTO bets (week_id, type, tag, odds, stake, payout, result) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (
                week_id,
                bet["type"],
                bet.get("tag"),
                bet["odds"],
                bet["stake"],
                bet.get("payout"),
            ),
        )
        bet_id = cur.lastrowid
        for leg in bet["legs"]:
            conn.execute(
                "INSERT INTO legs (bet_id, sport, event_date, away, home, market, "
                "period, selection, line, result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                (
                    bet_id,
                    leg["sport"],
                    leg["event_date"],
                    leg["away"],
                    leg["home"],
                    leg["market"],
                    leg.get("period", "full"),
                    leg["selection"],
                    leg.get("line"),
                ),
            )
    conn.commit()
    return week_id


def pending_bets(conn, week_label=None):
    query = "SELECT * FROM bets WHERE result IN ('pending', 'unknown')"
    params = ()
    if week_label:
        query = (
            "SELECT bets.* FROM bets JOIN weeks ON weeks.id = bets.week_id "
            "WHERE weeks.label = ? AND bets.result IN ('pending', 'unknown')"
        )
        params = (week_label,)
    return conn.execute(query, params).fetchall()


def legs_for_bet(conn, bet_id):
    return conn.execute("SELECT * FROM legs WHERE bet_id = ?", (bet_id,)).fetchall()


def update_leg_result(conn, leg_id, result, away_score, home_score):
    conn.execute(
        "UPDATE legs SET result = ?, away_score = ?, home_score = ? WHERE id = ?",
        (result, away_score, home_score, leg_id),
    )


def update_bet_result(conn, bet_id, result):
    conn.execute("UPDATE bets SET result = ? WHERE id = ?", (result, bet_id))


def full_dump(conn):
    """Every week with its bets and legs nested, scores included -- the shape
    a dashboard needs to render actual results, not just aggregate counts."""
    weeks = conn.execute("SELECT * FROM weeks ORDER BY id").fetchall()
    out = []
    for week in weeks:
        bets = conn.execute(
            "SELECT * FROM bets WHERE week_id = ? ORDER BY id", (week["id"],)
        ).fetchall()
        bet_list = []
        for bet in bets:
            legs = conn.execute(
                "SELECT * FROM legs WHERE bet_id = ? ORDER BY id", (bet["id"],)
            ).fetchall()
            bet_list.append({
                "type": bet["type"],
                "tag": bet["tag"],
                "odds": bet["odds"],
                "stake": bet["stake"],
                "payout": bet["payout"],
                "result": bet["result"],
                "legs": [
                    {
                        "sport": leg["sport"],
                        "event_date": leg["event_date"],
                        "away": leg["away"],
                        "home": leg["home"],
                        "market": leg["market"],
                        "period": leg["period"],
                        "selection": leg["selection"],
                        "line": leg["line"],
                        "result": leg["result"],
                        "away_score": leg["away_score"],
                        "home_score": leg["home_score"],
                    }
                    for leg in legs
                ],
            })
        out.append({"label": week["label"], "bets": bet_list})
    return out
