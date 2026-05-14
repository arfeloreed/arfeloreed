"""Generate an animated SVG of the user's GitHub contribution calendar.

Filled cells twinkle (opacity oscillates) at staggered random intervals.
GitHub's profile contribution chart itself cannot be styled; this SVG is
embedded in the README as an animated alternative.
"""

import json
import os
import random
import sys
import urllib.error
import urllib.request


USER = os.environ.get("GH_USER", "arfeloreed")
TOKEN = os.environ.get("GH_TOKEN")

THEMES = {
    "dark": {
        "bg": "transparent",
        "empty": "#161b22",
        "levels": ["#0e4429", "#006d32", "#26a641", "#39d353"],
        "text": "#7d8590",
        "month_label": "#7d8590",
    },
    "light": {
        "bg": "transparent",
        "empty": "#ebedf0",
        "levels": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "text": "#57606a",
        "month_label": "#57606a",
    },
}

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          firstDay
          contributionDays {
            date
            contributionLevel
            weekday
          }
        }
      }
    }
  }
}
"""


def fetch_calendar():
    if not TOKEN:
        raise RuntimeError("GH_TOKEN env var is required")
    payload = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "twinkle-svg-generator",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GraphQL HTTP {exc.code}: {exc.read().decode()}") from exc
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]


def parse_theme():
    theme = "dark"
    for arg in sys.argv[1:]:
        if arg.startswith("--theme="):
            theme = arg.split("=", 1)[1]
    if theme not in THEMES:
        raise ValueError(f"Unknown theme '{theme}'")
    return theme


def build_svg(weeks, palette):
    CELL = 11
    GAP = 3
    PAD_LEFT = 28
    PAD_TOP = 22
    PAD_RIGHT = 10
    PAD_BOTTOM = 10

    grid_w = len(weeks) * (CELL + GAP) - GAP
    grid_h = 7 * (CELL + GAP) - GAP
    width = PAD_LEFT + grid_w + PAD_RIGHT
    height = PAD_TOP + grid_h + PAD_BOTTOM

    rng = random.Random(0xC0FFEE)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="9">',
        f'<rect width="100%" height="100%" fill="{palette["bg"]}"/>',
    ]

    seen_months = set()
    for w_idx, week in enumerate(weeks):
        first = week["firstDay"]
        month = first[:7]
        month_num = int(first[5:7])
        day_num = int(first[8:10])
        if month not in seen_months and day_num <= 7:
            seen_months.add(month)
            label = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month_num - 1]
            lx = PAD_LEFT + w_idx * (CELL + GAP)
            parts.append(
                f'<text x="{lx}" y="{PAD_TOP - 8}" fill="{palette["month_label"]}">{label}</text>'
            )

    for d_idx, label in enumerate(["Mon", "Wed", "Fri"]):
        y = PAD_TOP + (1 + d_idx * 2) * (CELL + GAP) + CELL - 2
        parts.append(
            f'<text x="2" y="{y}" fill="{palette["month_label"]}">{label}</text>'
        )

    for w_idx, week in enumerate(weeks):
        for day in week["contributionDays"]:
            d_idx = day["weekday"]
            level = LEVEL_MAP.get(day["contributionLevel"], 0)
            x = PAD_LEFT + w_idx * (CELL + GAP)
            y = PAD_TOP + d_idx * (CELL + GAP)

            if level == 0:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'rx="2" ry="2" fill="{palette["empty"]}"/>'
                )
                continue

            color = palette["levels"][level - 1]
            begin = round(rng.uniform(0, 18), 2)
            dur = round(rng.uniform(12, 22), 2)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" ry="2" fill="{color}">'
                f'<animate attributeName="opacity" '
                f'values="1;1;0;1;1" keyTimes="0;0.45;0.5;0.55;1" '
                f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
                f'</rect>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    theme = parse_theme()
    weeks = fetch_calendar()
    svg = build_svg(weeks, THEMES[theme])
    sys.stdout.write(svg)


if __name__ == "__main__":
    main()
