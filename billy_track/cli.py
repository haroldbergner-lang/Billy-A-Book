import argparse
import json
import sys
from pathlib import Path

from . import db, grading, report

WEEKS_DIR = Path(__file__).resolve().parent.parent / "weeks"


def _load_week_file(path, label_override=None):
    with open(path) as f:
        week_data = json.load(f)
    label = label_override or week_data.get("week_label")
    if not label:
        sys.exit(f"{path}: provide --label or set 'week_label' in the JSON file")
    return label, week_data


def cmd_add_week(args):
    label, week_data = _load_week_file(args.json_file, args.label)
    conn = db.connect()
    db.insert_week(conn, label, week_data)
    print(f"Added week '{label}' with {len(week_data['bets'])} bet(s).")
    _grade(conn, week_label=label)
    conn.close()


def cmd_rebuild(args):
    """Wipe the local database and replay it from every JSON file in weeks/.
    The weeks/ directory (committed to git) is the durable source of truth --
    this session's database file is not, so run this after a fresh clone."""
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()

    files = sorted(WEEKS_DIR.glob("*.json"))
    if not files:
        sys.exit(f"No week files found in {WEEKS_DIR}")

    conn = db.connect()
    for path in files:
        label, week_data = _load_week_file(path)
        db.insert_week(conn, label, week_data)
        print(f"Loaded week '{label}' from {path.name} with {len(week_data['bets'])} bet(s).")
    _grade(conn)
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
    report.print_report(conn, week_label=args.week, as_json=args.json)
    conn.close()


def cmd_dump(args):
    conn = db.connect()
    print(json.dumps(db.full_dump(conn), indent=2))
    conn.close()


def main():
    parser = argparse.ArgumentParser(prog="billy_track")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add-week", help="Load a week's bets from a JSON file and grade finished games")
    p_add.add_argument("json_file")
    p_add.add_argument("--label", help="Week label (defaults to 'week_label' in the JSON file)")
    p_add.set_defaults(func=cmd_add_week)

    p_rebuild = sub.add_parser(
        "rebuild", help="Wipe the local DB and replay every committed file in weeks/"
    )
    p_rebuild.set_defaults(func=cmd_rebuild)

    p_grade = sub.add_parser("grade", help="Re-check any pending/unknown bets against final scores")
    p_grade.add_argument("--week", help="Only re-grade this week's label")
    p_grade.set_defaults(func=cmd_grade)

    p_report = sub.add_parser("report", help="Print win/loss stats")
    p_report.add_argument("--week", help="Only report on this week's label")
    p_report.add_argument("--json", action="store_true", help="Print machine-readable JSON instead")
    p_report.set_defaults(func=cmd_report)

    p_dump = sub.add_parser("dump", help="Print every week/bet/leg with scores, for pushing to the dashboard")
    p_dump.set_defaults(func=cmd_dump)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
