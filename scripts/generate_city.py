import os
import re
from datetime import datetime, timedelta

import requests

USERNAME = os.environ.get("GITHUB_USERNAME", "SayedSheikh")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""

def fetch_contributions():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {"query": GRAPHQL_QUERY, "variables": {"login": USERNAME}}
  try:
    r = requests.post("https://api.github.com/graphql",
              json=payload, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total    = calendar["totalContributions"]
    weeks    = calendar["weeks"]
    return total, weeks
  except Exception:
    return fetch_contributions_public()


def fetch_contributions_public():
  url = f"https://github.com/users/{USERNAME}/contributions"
  r = requests.get(url, timeout=20)
  r.raise_for_status()

  rect_pattern = re.compile(r'data-date="([0-9]{4}-[0-9]{2}-[0-9]{2})"[^>]*data-count="([0-9]+)"')
  days = []
  total = 0
  for match in rect_pattern.finditer(r.text):
    day_date = match.group(1)
    count = int(match.group(2))
    total += count
    days.append({"date": day_date, "contributionCount": count})

  if not days:
    raise RuntimeError("Unable to parse public contribution calendar")

  def sunday_start(date_text):
    day = datetime.strptime(date_text, "%Y-%m-%d").date()
    return day - timedelta(days=(day.weekday() + 1) % 7)

  weeks_map = {}
  for day in days:
    week_start = sunday_start(day["date"])
    weeks_map.setdefault(week_start, []).append(day)

  weeks = []
  for week_start in sorted(weeks_map):
    contribution_days = sorted(weeks_map[week_start], key=lambda item: item["date"])
    weeks.append({"contributionDays": contribution_days})

  return total, weeks


def compute_buildings(weeks):
    """
    For each week: sum all 7 days -> weekly_total
    Normalize weekly_total to building height between MIN_H and MAX_H
    For each day: store count for window brightness
    """
    MIN_H = 18    # px - minimum building height (even 0-commit weeks show a stub)
    MAX_H = 130   # px - maximum building height

    weekly_totals = []
    for week in weeks:
        total = sum(day["contributionCount"] for day in week["contributionDays"])
        weekly_totals.append(total)

    global_max = max(weekly_totals) if max(weekly_totals) > 0 else 1

    buildings = []
    for i, week in enumerate(weeks):
        raw = weekly_totals[i]
        # normalized height: at least MIN_H, scales up to MAX_H
        height = MIN_H + int((raw / global_max) * (MAX_H - MIN_H))
        days   = [d["contributionCount"] for d in week["contributionDays"]]
        # pad to 7 days if week is incomplete
        while len(days) < 7:
            days.append(0)
        buildings.append({"height": height, "days": days, "total": raw})

    return buildings


def compute_streak(weeks):
    """Walk days in reverse, count consecutive days with contributions > 0"""
    all_days = []
    for week in weeks:
        for day in week["contributionDays"]:
            all_days.append(day["contributionCount"])
    streak = 0
    for count in reversed(all_days):
        if count > 0:
            streak += 1
        else:
            break
    return streak


def generate_svg(total_contributions, buildings, streak):

    SVG_W      = 900
    SVG_H      = 220
    GROUND_Y   = 185
    BLDG_GAP   = 2       # px gap between buildings
    NUM_BLDGS  = len(buildings)   # up to 53
    BLDG_W     = max(8, int((SVG_W - (NUM_BLDGS * BLDG_GAP)) / NUM_BLDGS))
    # recalculate actual total width
    TOTAL_W    = NUM_BLDGS * (BLDG_W + BLDG_GAP)
    START_X    = (SVG_W - TOTAL_W) // 2  # center the skyline

    lines = []  # collect SVG lines, then join

    lines.append(f'''<svg xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 {SVG_W} {SVG_H}" width="100%">
<defs>
  <style>
    @keyframes scan {{
      0%   {{ transform: translateX(-20px); opacity: 0; }}
      5%   {{ opacity: 1; }}
      95%  {{ opacity: 1; }}
      100% {{ transform: translateX({SVG_W + 20}px); opacity: 0; }}
    }}
    @keyframes windowPulse {{
      0%,100% {{ opacity: 1; }}
      50%     {{ opacity: 0.55; }}
    }}
    @keyframes statsFade {{
      0%,100% {{ opacity: 0.7; }}
      50%     {{ opacity: 1; }}
    }}
    @keyframes groundGlow {{
      0%,100% {{ opacity: 0.18; }}
      50%     {{ opacity: 0.32; }}
    }}
    .scanner {{ animation: scan {SVG_W / 60:.1f}s linear infinite; }}
    .ground-glow {{ animation: groundGlow 4s ease-in-out infinite; }}
    .stats {{ animation: statsFade 3s ease-in-out infinite; }}
  </style>

  <!-- Sky gradient -->
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="#020710"/>
    <stop offset="60%"  stop-color="#030c1c"/>
    <stop offset="100%" stop-color="#040f22"/>
  </linearGradient>

  <!-- Building gradient: dark base, slightly lit top -->
  <linearGradient id="bldg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="#0d1f3c"/>
    <stop offset="100%" stop-color="#060e1e"/>
  </linearGradient>

  <!-- Reflection fade gradient -->
  <linearGradient id="refFade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stop-color="white" stop-opacity="0.10"/>
    <stop offset="100%" stop-color="white" stop-opacity="0"/>
  </linearGradient>

  <!-- Scanner beam gradient -->
  <linearGradient id="scanGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%"   stop-color="#60a5fa" stop-opacity="0"/>
    <stop offset="50%"  stop-color="#60a5fa" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#60a5fa" stop-opacity="0"/>
  </linearGradient>

  <!-- Clip to SVG bounds -->
  <clipPath id="bounds">
    <rect width="{SVG_W}" height="{SVG_H}"/>
  </clipPath>
</defs>

<!-- Sky -->
<rect width="{SVG_W}" height="{SVG_H}" fill="url(#sky)"/>
''')

    import random
    random.seed(42)   # fixed seed = same stars every render
    star_lines = []
    for _ in range(55):
        sx  = random.randint(0, SVG_W)
        sy  = random.randint(5, GROUND_Y - 30)
        sr  = round(random.uniform(0.4, 1.1), 1)
        sop = round(random.uniform(0.1, 0.35), 2)
        star_lines.append(
            f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="#93c5fd" opacity="{sop}"/>'
        )
    lines.append("\n".join(star_lines))

    for i, b in enumerate(buildings):
        x      = START_X + i * (BLDG_W + BLDG_GAP)
        bh     = b["height"]
        by     = GROUND_Y - bh   # top of building
        days   = b["days"]       # list of 7 ints

        # Building body
        lines.append(
            f'<rect x="{x}" y="{by}" width="{BLDG_W}" height="{bh}" '
            f'fill="url(#bldg)" rx="1"/>'
        )

        # Windows: 7 rows from top of building
        WIN_SIZE   = max(1, BLDG_W - 4)   # window fills most of width
        WIN_MARGIN = 2
        WIN_ROWS   = 7
        row_step   = bh / (WIN_ROWS + 1)

        for row in range(WIN_ROWS):
            count = days[row]
            if count == 0:
                continue   # dark window - no element drawn = pure dark

            # brightness based on count: 1->dim, 5+->bright
            opacity = min(0.9, 0.25 + count * 0.13)
            wy = by + row_step * (row + 1) - WIN_SIZE / 2
            wx = x + WIN_MARGIN

            # pulse speed varies per window for organic feel
            dur = round(2.0 + (i + row) % 5 * 0.4, 1)
            dly = round((i * 0.1 + row * 0.07) % 2.0, 2)

            lines.append(
                f'<rect x="{wx:.1f}" y="{wy:.1f}" '
                f'width="{WIN_SIZE}" height="{max(1, WIN_SIZE * 0.55):.1f}" '
                f'fill="#60a5fa" opacity="{opacity}" rx="0.5" '
                f'style="animation: windowPulse {dur}s ease-in-out {dly}s infinite;"/>'
            )

        # Roof edge line - thin blue line on top of every building
        lines.append(
            f'<line x1="{x}" y1="{by}" x2="{x + BLDG_W}" y2="{by}" '
            f'stroke="#1d4ed8" stroke-width="0.8" opacity="0.6"/>'
        )

    lines.append(
        f'<line x1="0" y1="{GROUND_Y}" x2="{SVG_W}" y2="{GROUND_Y}" '
        f'stroke="#1d4ed8" stroke-width="0.8" opacity="0.5"/>'
    )

    # Reflection: mirror of buildings, clipped, faded
    lines.append(f'<g clip-path="url(#bounds)" class="ground-glow">')
    for i, b in enumerate(buildings):
        x  = START_X + i * (BLDG_W + BLDG_GAP)
        bh = b["height"]
        # reflection height = 30% of building height
        ref_h = int(bh * 0.30)
        lines.append(
            f'<rect x="{x}" y="{GROUND_Y}" width="{BLDG_W}" height="{ref_h}" '
            f'fill="#0d1f3c" opacity="0.6"/>'
        )
    lines.append(
        f'<rect x="0" y="{GROUND_Y}" width="{SVG_W}" height="35" '
        f'fill="url(#refFade)"/>'
    )
    lines.append('</g>')

    lines.append(
        f'<rect x="0" y="0" width="40" height="{GROUND_Y}" '
        f'fill="url(#scanGrad)" class="scanner" clip-path="url(#bounds)"/>'
    )

    lines.append(f'''
<g class="stats">
  <text x="12" y="20"
    font-family="'Courier New', monospace"
    font-size="9" fill="#3b82f6" opacity="0.85"
    letter-spacing="1">
    CONTRIBUTIONS: {total_contributions}
  </text>
  <text x="12" y="33"
    font-family="'Courier New', monospace"
    font-size="9" fill="#60a5fa" opacity="0.7"
    letter-spacing="1">
    STREAK: {streak} DAYS
  </text>
</g>
''')

    lines.append('</svg>')
    return "\n".join(lines)


def main():
    total, weeks     = fetch_contributions()
    buildings        = compute_buildings(weeks)
    streak           = compute_streak(weeks)
    svg_content      = generate_svg(total, buildings, streak)

    os.makedirs("assets", exist_ok=True)
    with open("assets/city.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"Done - {len(buildings)} buildings, {total} total contributions, {streak} day streak")


if __name__ == "__main__":
    main()
