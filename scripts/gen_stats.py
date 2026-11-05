#!/usr/bin/env python3
"""Generate assets/stats.svg for the profile README.

Self-contained: stdlib only, no third-party card services.
Auth: set GITHUB_TOKEN (the workflow provides it).
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "cantwin-ctrl")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "assets" / "stats.svg"

LANG_COLORS = {
    "Java": "#b07219",
    "Shell": "#89e051",
    "Python": "#3572A5",
    "C": "#555555",
    "C++": "#f34b7d",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Lua": "#000080",
    "Kotlin": "#A97BFF",
    "Rust": "#dea584",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Makefile": "#427819",
    "Dockerfile": "#384d54",
    "Objective-C": "#438eff",
    "Go": "#00ADD8",
}
FALLBACK = ["#39d353", "#1f6feb", "#a371f7", "#f0883e", "#db61a2"]

MONO = (
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, '
    '"Liberation Mono", monospace'
)


def api(path: str):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-stats-svg")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def human(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def collect():
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&sort=pushed")
        repos.extend(r for r in batch if not r.get("fork"))
        if len(batch) < 100:
            break
        page += 1

    langs: dict[str, int] = {}
    for repo in repos:
        if repo.get("size", 0) == 0:
            continue
        try:
            for name, size in api(f"/repos/{USER}/{repo['name']}/languages").items():
                langs[name] = langs.get(name, 0) + size
        except Exception:
            continue

    pushed = max(
        (r["pushed_at"] for r in repos if r.get("pushed_at")),
        default=user.get("updated_at", ""),
    )
    last = ""
    if pushed:
        last = datetime.fromisoformat(pushed.replace("Z", "+00:00")).strftime("%d %b %Y")

    return {
        "repos": user.get("public_repos", 0),
        "stars": sum(r.get("stargazers_count", 0) for r in repos),
        "followers": user.get("followers", 0),
        "last_push": last or "—",
        "langs": langs,
    }


def build(data) -> str:
    tiles = [
        ("public repos", human(data["repos"])),
        ("stars earned", human(data["stars"])),
        ("followers", human(data["followers"])),
        ("last push", data["last_push"]),
    ]

    total = sum(data["langs"].values()) or 1
    top = sorted(data["langs"].items(), key=lambda kv: kv[1], reverse=True)[:5]

    parts = []
    # metric tiles
    tile_w, gap, x0 = 254, 16, 24
    for i, (label, value) in enumerate(tiles):
        x = x0 + i * (tile_w + gap)
        small = label == "last push"
        parts.append(
            f'      <g transform="translate({x},72)">\n'
            f'        <rect width="{tile_w}" height="82" rx="10" fill="#111820" '
            f'stroke="#1f2a37"/>\n'
            f'        <text class="mono" x="18" y="34" font-size="12" '
            f'fill="#6e7681" letter-spacing="1.6">{esc(label.upper())}</text>\n'
            f'        <text class="mono" x="18" y="65" font-size="{20 if small else 26}" '
            f'font-weight="600" fill="{"#8b949e" if small else "#e6edf3"}">'
            f'{esc(value)}</text>\n'
            f"      </g>"
        )

    # language bar
    bar_x, bar_y, bar_w, bar_h = 24, 206, 1072, 10
    segs, cx = [], bar_x
    for i, (name, size) in enumerate(top):
        w = max(2.0, bar_w * size / total)
        if i == len(top) - 1:
            w = bar_x + bar_w - cx
        color = LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        segs.append(
            f'      <rect x="{cx:.1f}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" '
            f'fill="{color}"/>'
        )
        cx += w

    legend, lx = [], bar_x
    for i, (name, size) in enumerate(top):
        color = LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        pct = size / total * 100
        legend.append(
            f'      <g transform="translate({lx:.0f},246)">\n'
            f'        <circle cx="4" cy="-5" r="4" fill="{color}"/>\n'
            f'        <text class="mono" x="16" y="0" font-size="13" fill="#c9d1d9">'
            f"{esc(name)} <tspan fill=\"#6e7681\">{pct:.0f}%</tspan></text>\n"
            f"      </g>"
        )
        lx += 205

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 290" width="1120" height="290" role="img" aria-label="cantwin-ctrl github stats">
  <style>
    .mono {{ font-family: {MONO}; }}
    .in {{ animation: rise .6s cubic-bezier(.22,.8,.3,1) both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @media (prefers-reduced-motion: reduce) {{ .in {{ animation: none; opacity: 1; }} }}
  </style>
  <rect x="1" y="1" width="1117" height="287" rx="16" fill="#0d1117" stroke="#243040" stroke-width="1.5"/>
  <g class="in">
    <text class="mono" x="24" y="40" font-size="17" fill="#39d353">$</text>
    <text class="mono" x="46" y="40" font-size="17" fill="#c9d1d9">stats --user {esc(USER)}</text>
  </g>
{chr(10).join(parts)}
  <g class="in" style="animation-delay:.25s">
{chr(10).join(segs)}
  </g>
  <g class="in" style="animation-delay:.4s">
{chr(10).join(legend)}
  </g>
  <text class="mono" x="1096" y="272" text-anchor="end" font-size="11" fill="#30363d">updated {datetime.now(timezone.utc).strftime('%Y-%m-%d')}</text>
</svg>
"""


def main():
    data = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(data), encoding="utf-8")
    print(f"wrote {OUT} — repos={data['repos']} stars={data['stars']} "
          f"langs={list(data['langs'])[:5]}")


if __name__ == "__main__":
    main()
