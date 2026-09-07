import json

from . import config


def _profit(bet):
    if bet["result"] == "won":
        return (bet["payout"] or 0) - bet["stake"]
    if bet["result"] == "lost":
        return -bet["stake"]
    return 0.0  # push, pending, unknown


def build_summary(conn, week_label=None):
    if week_label:
        bets = conn.execute(
            "SELECT bets.* FROM bets JOIN weeks ON weeks.id = bets.week_id WHERE weeks.label = ?",
            (week_label,),
        ).fetchall()
    else:
        bets = conn.execute("SELECT * FROM bets").fetchall()

    settled = [b for b in bets if b["result"] in ("won", "lost", "push")]
    wins = sum(1 for b in settled if b["result"] == "won")
    losses = sum(1 for b in settled if b["result"] == "lost")
    pushes = sum(1 for b in settled if b["result"] == "push")
    pending = sum(1 for b in bets if b["result"] in ("pending", "unknown"))

    staked = sum(b["stake"] for b in settled)
    profit = sum(_profit(b) for b in settled)
    decided = wins + losses
    win_rate = (wins / decided * 100) if decided else 0.0
    roi = (profit / staked * 100) if staked else 0.0

    leg_rows = conn.execute(
        "SELECT legs.market, legs.result FROM legs "
        "JOIN bets ON bets.id = legs.bet_id "
        + ("JOIN weeks ON weeks.id = bets.week_id WHERE weeks.label = ?" if week_label else ""),
        (week_label,) if week_label else (),
    ).fetchall()
    by_market = {}
    for row in leg_rows:
        m = by_market.setdefault(row["market"], {"won": 0, "lost": 0, "push": 0, "other": 0})
        m[row["result"] if row["result"] in ("won", "lost", "push") else "other"] += 1
    for counts in by_market.values():
        decided_legs = counts["won"] + counts["lost"]
        counts["hit_rate"] = round(counts["won"] / decided_legs * 100, 1) if decided_legs else 0.0

    weeks = conn.execute("SELECT weeks.label, weeks.id FROM weeks ORDER BY weeks.id").fetchall()
    by_week = []
    for w in weeks:
        if week_label and w["label"] != week_label:
            continue
        wbets = conn.execute(
            "SELECT * FROM bets WHERE week_id = ?", (w["id"],)
        ).fetchall()
        wsettled = [b for b in wbets if b["result"] in ("won", "lost", "push")]
        by_week.append({
            "label": w["label"],
            "wins": sum(1 for b in wsettled if b["result"] == "won"),
            "losses": sum(1 for b in wsettled if b["result"] == "lost"),
            "pushes": sum(1 for b in wsettled if b["result"] == "push"),
            "pending": sum(1 for b in wbets if b["result"] in ("pending", "unknown")),
            "staked": round(sum(b["stake"] for b in wsettled), 2),
            "profit": round(sum(_profit(b) for b in wsettled), 2),
        })

    starting_balance = config.load_config()["starting_balance"]

    return {
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "win_rate": round(win_rate, 1),
        "staked": round(staked, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 1),
        "starting_balance": round(starting_balance, 2),
        "balance": round(starting_balance + profit, 2),
        "by_market": by_market,
        "by_week": by_week,
    }


def print_report(conn, week_label=None, as_json=False):
    summary = build_summary(conn, week_label)

    if as_json:
        print(json.dumps(summary, indent=2))
        return

    title = f"Report for week: {week_label}" if week_label else "All-time report"
    print(f"\n=== {title} ===")
    print(f"Record: {summary['wins']}-{summary['losses']}-{summary['pushes']}  ({summary['pending']} pending/unresolved)")
    print(f"Win rate: {summary['win_rate']}%")
    print(f"Staked: ${summary['staked']:.2f}   Profit: ${summary['profit']:+.2f}   ROI: {summary['roi']}%")
    print(f"Balance: ${summary['balance']:.2f}   (started at ${summary['starting_balance']:.2f})")

    print("\nBy market (leg-level, includes legs inside parlays):")
    for market, counts in sorted(summary["by_market"].items()):
        print(f"  {market:10s} {counts['won']}-{counts['lost']}-{counts['push']}  ({counts['hit_rate']}% hit rate)")

    print()
