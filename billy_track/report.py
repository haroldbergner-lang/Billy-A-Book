def _profit(bet):
    if bet["result"] == "won":
        return (bet["payout"] or 0) - bet["stake"]
    if bet["result"] == "lost":
        return -bet["stake"]
    return 0.0  # push, pending, unknown


def print_report(conn, week_label=None):
    if week_label:
        bets = conn.execute(
            "SELECT bets.* FROM bets JOIN weeks ON weeks.id = bets.week_id WHERE weeks.label = ?",
            (week_label,),
        ).fetchall()
        title = f"Report for week: {week_label}"
    else:
        bets = conn.execute("SELECT * FROM bets").fetchall()
        title = "All-time report"

    print(f"\n=== {title} ===")

    settled = [b for b in bets if b["result"] in ("won", "lost", "push")]
    wins = sum(1 for b in settled if b["result"] == "won")
    losses = sum(1 for b in settled if b["result"] == "lost")
    pushes = sum(1 for b in settled if b["result"] == "push")
    pending = sum(1 for b in bets if b["result"] in ("pending", "unknown"))

    staked = sum(b["stake"] for b in settled)
    profit = sum(_profit(b) for b in settled)
    decided = wins + losses
    win_rate = (wins / decided * 100) if decided else 0.0

    print(f"Record: {wins}-{losses}-{pushes}  ({pending} pending/unresolved)")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Staked: ${staked:.2f}   Profit: ${profit:+.2f}   ROI: {(profit / staked * 100) if staked else 0:.1f}%")

    print("\nBy market (leg-level, includes legs inside parlays):")
    leg_rows = conn.execute(
        "SELECT legs.market, legs.result FROM legs "
        "JOIN bets ON bets.id = legs.bet_id "
        + ("JOIN weeks ON weeks.id = bets.week_id WHERE weeks.label = ?" if week_label else "")
        , (week_label,) if week_label else (),
    ).fetchall()
    by_market = {}
    for row in leg_rows:
        m = by_market.setdefault(row["market"], {"won": 0, "lost": 0, "push": 0, "other": 0})
        m[row["result"] if row["result"] in ("won", "lost", "push") else "other"] += 1
    for market, counts in sorted(by_market.items()):
        decided_legs = counts["won"] + counts["lost"]
        rate = (counts["won"] / decided_legs * 100) if decided_legs else 0.0
        print(f"  {market:10s} {counts['won']}-{counts['lost']}-{counts['push']}  ({rate:.0f}% hit rate)")

    print()
