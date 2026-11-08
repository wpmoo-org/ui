#!/usr/bin/env python3
"""Record when each public catalog page's content last changed.

site/src/registry/page-dates.json maps every public page route to the date
its content last changed and a hash of that content. The build reads only
this file for sitemap <lastmod> values, the Sitemap page and JSON-LD
dateModified, so builds stay deterministic and dates never move unless a
page's content does.

The hash covers the visible text and media inside <main>, without the
page-outline sidebar, the previous/next pagination, scripts or styles, so a
neighbour added to the catalog or a new asset version does not change it.
The Sitemap page lists the dates themselves and is never dated.

    scripts/record-page-dates.py --check   # exit 1 when a recorded date is stale
    scripts/record-page-dates.py --write   # rebuild, update changed pages, rebuild
    scripts/record-page-dates.py --write --seed-from-git
                                           # date pages new to the registry from
                                           # their template's last commit instead
                                           # of today (one-time backfill)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

REGISTRY = build.PAGE_DATES
UNDATED = {"sitemap.html"}
TIME_ZONE = ZoneInfo("Europe/Berlin")

_MAIN = re.compile(r"<main\b[^>]*>(.*)</main>", re.DOTALL)
_DROP = re.compile(
    r"<(nav|aside|script|style|template)\b[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_MEDIA = re.compile(r"<(?:img|source)\b[^>]*\bsrc=\"([^\"?]*)", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def page_content(html: str) -> str:
    """Normalised visible content of a rendered page's main region."""
    match = _MAIN.search(html)
    body = match.group(1) if match else html
    # Nested navs/asides are removed innermost first.
    previous = None
    while previous != body:
        previous = body
        body = _DROP.sub(" ", body)
    media = " ".join(_MEDIA.findall(body))
    text = unescape(_TAG.sub(" ", body))
    return " ".join(f"{text} {media}".split())


def page_hash(html: str) -> str:
    return "sha256:" + hashlib.sha256(page_content(html).encode("utf-8")).hexdigest()[:16]


def dated_pages() -> list[str]:
    return [path for path in build.public_page_paths() if path not in UNDATED]


def current_hashes() -> dict[str, str]:
    hashes = {}
    for path in dated_pages():
        output = build.SITE_DIST / build.pretty_output_path(Path(path))
        hashes[build.pretty_url(path)] = page_hash(output.read_text(encoding="utf-8"))
    return hashes


def load_registry() -> dict[str, dict[str, str]]:
    if not REGISTRY.exists():
        return {}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def stale_routes(registry: dict[str, dict[str, str]], hashes: dict[str, str]) -> list[str]:
    changed = [route for route, value in hashes.items() if registry.get(route, {}).get("hash") != value]
    removed = [route for route in registry if route not in hashes]
    return sorted(changed + removed)


def git_date(path: str) -> str | None:
    template = build.PAGES / f"{path}.jinja"
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(template.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    return value or None


def run_build() -> None:
    subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT, check=True)


def write(seed_from_git: bool) -> list[str]:
    run_build()
    registry = load_registry()
    hashes = current_hashes()
    today = dt.datetime.now(TIME_ZONE).date().isoformat()
    routes_by_path = {build.pretty_url(path): path for path in dated_pages()}
    updated = []
    next_registry: dict[str, dict[str, str]] = {}
    for route in sorted(hashes):
        entry = registry.get(route)
        if entry and entry.get("hash") == hashes[route]:
            next_registry[route] = entry
            continue
        date = today
        if entry is None and seed_from_git:
            date = git_date(routes_by_path[route]) or today
        next_registry[route] = {"updated": date, "hash": hashes[route]}
        updated.append(route)
    if next_registry != registry:
        REGISTRY.write_text(json.dumps(next_registry, indent=2) + "\n", encoding="utf-8")
        run_build()
    return updated + [route for route in registry if route not in hashes]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--seed-from-git", action="store_true")
    args = parser.parse_args(argv)

    if args.write:
        changed = write(args.seed_from_git)
        print(f"page dates: {len(changed)} updated" + (": " + ", ".join(changed) if changed else ""))
        return 0

    stale = stale_routes(load_registry(), current_hashes())
    if stale:
        print("Page content changed without a recorded date; run scripts/record-page-dates.py --write:")
        for route in stale:
            print(f"  {route}")
        return 1
    print("page dates: up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
