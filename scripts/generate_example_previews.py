#!/usr/bin/env python3
"""Generate 16:9 preview screenshots for Examples catalog cards.

Boots a local server over the repo root (same pattern as tests/helpers/
browser_harness.py's serve_repository), loads each built Examples page
from site-dist/, and saves a 1280x720 (exactly 16:9) viewport screenshot
to site/static/images/examples/<slug>.png. build.py's
example_preview_src() picks these up automatically on the next build --
no template or code changes needed after running this.

Run `python3 build.py` first so site-dist/ is current, then:
    python3 scripts/generate_example_previews.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402

from helpers.browser_harness import (  # noqa: E402
    launch_certification_browser,
    serve_repository,
)

SITE_DIST = ROOT / "site-dist"
OUTPUT_DIR = ROOT / "site/static/images/examples"
# Auth/Settings pages center a fixed-width card/panel regardless of
# viewport width, so a narrower (still 16:9) capture makes that content
# fill more of the frame -- at 1280 wide it reads tiny and busy once
# scaled down to a 3-per-row card thumbnail; at 960 it's legibly larger.
VIEWPORT = {"width": 960, "height": 540}  # exactly 16:9

# Auth examples (Sign In/Up, Forgot Password) render full-bleed with no
# site chrome. Settings/Dashboard examples render inside the normal
# catalog layout (docs sidebar + top navbar). Both also end in a small
# "demo only / composed from X, Y, Z" attribution note. None of that is
# part of the example screen itself, so all of it is hidden here to keep
# the crop to just the app UI.
HIDE_CHROME_CSS = """
#catalog-sidebar,
header.moo-catalog__header,
.moo-auth-page__footer,
.moo-examples-footer { display: none !important; }
"""

EXAMPLE_SLUGS = (
    "auth/sign-in",
    "auth/sign-up",
    "auth/forgot-password",
    "settings/profile",
    "settings/account",
    "settings/appearance",
    "dashboard/tasks",
)

# Settings pages' actual content (nav + form) is narrower than the
# capture viewport, leaving empty space on the right at the full VIEWPORT
# width above. .moo-settings-layout itself isn't a usable measure of that
# -- it's a grid item that stretches to fill its row, so its own
# bounding box is the full viewport width regardless of how little of it
# its children use. Measuring the nav and content children directly and
# taking their union gives the actual visual extent instead.
CONTENT_CLIP_SELECTOR = {
    "settings/profile": (".moo-settings-nav", ".moo-settings-layout__content"),
    "settings/account": (".moo-settings-nav", ".moo-settings-layout__content"),
    "settings/appearance": (".moo-settings-nav", ".moo-settings-layout__content"),
}


def main() -> None:
    if not (SITE_DIST / "examples").is_dir():
        raise SystemExit("site-dist/examples not found -- run `python3 build.py` first.")

    with sync_playwright() as playwright, serve_repository() as base_url:
        browser = launch_certification_browser(playwright)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = context.new_page()
        for slug in EXAMPLE_SLUGS:
            url = f"{base_url}/site-dist/examples/{slug}/index.html"
            response = None
            # "networkidle" is flaky by nature (Playwright's own docs warn
            # against relying on it) and reliably reproduced spurious 404s
            # here after a few pages' worth of prior navigations -- "load"
            # is deterministic for these static, no-polling pages. The
            # retry loop stays as a second line of defense.
            for attempt in range(3):
                response = page.goto(url, wait_until="load")
                if response and response.status == 200:
                    break
            if not response or response.status != 200:
                status = response.status if response else "no response"
                raise SystemExit(f"{slug}: giving up after 3 attempts ({status}) on {url}")
            page.add_style_tag(content=HIDE_CHROME_CSS)
            out_path = OUTPUT_DIR / f"{slug}.png"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            clip = None
            selector_pair = CONTENT_CLIP_SELECTOR.get(slug)
            if selector_pair:
                nav_selector, content_selector = selector_pair
                nav_box = page.locator(nav_selector).bounding_box()
                content_box = page.locator(content_selector).bounding_box()
                if nav_box and content_box:
                    left = nav_box["x"]
                    right = content_box["x"] + content_box["width"]
                    width = min(VIEWPORT["width"], (right - left) + 2 * left)
                    clip = {
                        "x": 0,
                        "y": 0,
                        "width": width,
                        "height": width * 9 / 16,
                    }

            page.screenshot(path=str(out_path), clip=clip)
            print(f"wrote {out_path.relative_to(ROOT)}")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
