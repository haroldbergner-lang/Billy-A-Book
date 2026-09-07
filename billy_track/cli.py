import argparse
import json
import sys

from . import db, grading, report


def cmd_add_week(args):
    with open(args.json_file) as f:
        week_data = json.load(f)
    label = args.label or week_data.get("week_label")
    if not label:
        sys.exit("Provide --label or set 'week_label' in the JSON file")

    conn = db.connect()
    db.insert_week(conn, label, week_data)
    print(f"Added week '{label}' with {len(week_data['bets'])} bet(s).")
    _grade(conn, week_label=label)
    conn.close()


def cmd_grade(args):
    conn = db.connect()
    _grade(conn, week_label=args.week)
    conn.close()


def _grade(conn, week_label=None):
    graded = 0
    for bet in db.pending_bets(conn, week_label):
        leg_rows = db.legs_for_bet(conn, bet["id"])
        results = []
        for leg in leg_rows:
            result, away_score, home_score = grading.grade_leg(dict(leg))
            db.update_leg_result(conn, leg["id"], result, away_score, home_score)
            results.append({"result": result})
        bet_result = grading.grade_bet(results)
        db.update_bet_result(conn, bet["id"], bet_result)
        if bet_result not in ("pending", "unknown"):
            graded += 1
    conn.commit()
    print(f"Graded {graded} bet(s) this run.")


def cmd_report(args):
    conn = db.connect()
    report.print_report(conn, week_label=args.week)
    conn.close()


def main():
    parser = argparse.ArgumentParser(prog="billy_track")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add-week", help="Load a week's bets from a JSON file and grade finished games")
    p_add.add_argument("json_file")
    p_add.add_argument("--label", help="Week label (defaults to 'week_label' in the JSON file)")
    p_add.set_defaults(func=cmd_add_week)

    p_grade = sub.add_parser("grade", help="Re-check any pending/unknown bets against final scores")
    p_grade.add_argument("--week", help="Only re-grade this week's label")
    p_grade.set_defaults(func=cmd_grade)

    p_report = sub.add_parser("report", help="Print win/loss stats")
    p_report.add_argument("--week", help="Only report on this week's label")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
