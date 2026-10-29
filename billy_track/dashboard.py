import json
from copy import deepcopy
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard_template.html"
PLACEHOLDER = "/*__BILLY_DATA__*/ null"
WEEKS_DIR = Path(__file__).resolve().parent.parent / "weeks"


def render_html(weeks, summary):
    # Keep incomplete-slip warnings from the durable records in the generated page.
    weeks = deepcopy(weeks)
    for week in weeks:
        source_path = WEEKS_DIR / f"{week['label']}.json"
        if not source_path.exists():
            continue
        source_bets = json.loads(source_path.read_text())["bets"]
        if len(source_bets) != len(week["bets"]):
            raise ValueError(f"Source/cache bet count differs for {week['label']}")
        for bet, source in zip(week["bets"], source_bets):
            if (bet["odds"], bet["stake"]) != (source["odds"], source["stake"]):
                raise ValueError(f"Source/cache bet order differs for {week['label']}")
            if source.get("transcription_complete") is False:
                bet["expected_leg_count"] = source["expected_leg_count"]
                bet["note"] = source["note"]
    template = TEMPLATE_PATH.read_text()
    data_json = json.dumps({"weeks": weeks, "summary": summary})
    if PLACEHOLDER not in template:
        raise RuntimeError(f"Template is missing the expected placeholder: {PLACEHOLDER!r}")
    return template.replace(PLACEHOLDER, data_json)

