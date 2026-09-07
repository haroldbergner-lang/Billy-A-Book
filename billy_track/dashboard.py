import json
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard_template.html"
PLACEHOLDER = "/*__BILLY_DATA__*/ null"


def render_html(weeks, summary):
    template = TEMPLATE_PATH.read_text()
    data_json = json.dumps({"weeks": weeks, "summary": summary})
    if PLACEHOLDER not in template:
        raise RuntimeError(f"Template is missing the expected placeholder: {PLACEHOLDER!r}")
    return template.replace(PLACEHOLDER, data_json)
