import os
import sys
import threading
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

from playwright.sync_api import Browser, BrowserContext, Page, Playwright


ROOT = Path(__file__).resolve().parents[2]
SITE_PUBLIC = ROOT / "site/public"
SITE_PUBLIC_FILES = frozenset(
    {
        "favicon.svg",
        "favicon.ico",
        "apple-touch-icon.png",
        "icon-192.png",
        "icon-512.png",
        "site.webmanifest",
        "llms.txt",
    }
)
AXE_PATH = ROOT / "node_modules/axe-core/axe.min.js"
SCREENSHOT_NORMALIZATION_CSS = """
*, *::before, *::after {
  animation-delay: 0s !important;
  animation-duration: 0s !important;
  caret-color: transparent !important;
  scroll-behavior: auto !important;
  transition-delay: 0s !important;
  transition-duration: 0s !important;
}
"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def translate_path(self, path: str) -> str:
        public_path = urlsplit(path).path.lstrip("/")
        if public_path.startswith("assets/"):
            local_asset = Path(self.directory) / public_path
            if local_asset.exists():
                return str(local_asset)
            return str(ROOT / "site-dist" / public_path)
        if public_path in SITE_PUBLIC_FILES:
            return str(SITE_PUBLIC / public_path)
        return super().translate_path(path)


@dataclass(frozen=True)
class BootstrapLane:
    name: str
    version: str
    bundle_path: str

    def bundle_url(self, base_url: str) -> str:
        return f"{base_url}/{self.bundle_path.lstrip('/')}"


CANONICAL_BOOTSTRAP = BootstrapLane(
    name="canonical",
    version="5.3.3",
    bundle_path="vendor/bootstrap/dist/js/bootstrap.bundle.min.js",
)
CERTIFICATION_BOOTSTRAP_LANES = (CANONICAL_BOOTSTRAP,)


@dataclass(frozen=True)
class BrowserCase:
    name: str
    viewport: dict[str, int]
    color_scheme: str
    direction: str
    is_mobile: bool = False
    has_touch: bool = False


CERTIFICATION_CASES = (
    BrowserCase(
        name="desktop-light-ltr",
        viewport={"width": 1040, "height": 844},
        color_scheme="light",
        direction="ltr",
    ),
    BrowserCase(
        name="mobile-dark-rtl",
        viewport={"width": 390, "height": 844},
        color_scheme="dark",
        direction="rtl",
        is_mobile=True,
        has_touch=True,
    ),
)


class BrowserEvidence:
    def __init__(self, page: Page) -> None:
        self.console_errors: list[str] = []
        self.page_errors: list[str] = []
        page.on(
            "console",
            lambda message: self.console_errors.append(message.text)
            if message.type in {"error", "warning"}
            else None,
        )
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))

    def assert_clean(self) -> None:
        if self.console_errors or self.page_errors:
            details = [
                *(f"console: {message}" for message in self.console_errors),
                *(f"page: {message}" for message in self.page_errors),
            ]
            raise AssertionError("Browser evidence is not clean:\n" + "\n".join(details))


def launch_certification_browser(playwright: Playwright) -> Browser:
    engine = os.environ.get("MOO_UI_BROWSER_ENGINE", "chromium").lower()
    if engine not in {"chromium", "firefox", "webkit"}:
        raise AssertionError(f"Unsupported browser engine: {engine!r}")
    if engine != "chromium":
        return getattr(playwright, engine).launch()
    configured_channel = os.environ.get("MOO_UI_BROWSER_CHANNEL")
    if configured_channel:
        if configured_channel in {"bundled", "playwright"}:
            return playwright.chromium.launch()
        return playwright.chromium.launch(channel=configured_channel)
    return playwright.chromium.launch()


def skip_if_browser_launch_is_sandboxed() -> None:
    if sys.platform == "darwin" and os.environ.get("CODEX_SANDBOX") == "seatbelt":
        raise unittest.SkipTest(
            "Codex macOS seatbelt sandbox blocks Playwright browser launches"
        )


def new_case_context(browser: Browser, case: BrowserCase) -> BrowserContext:
    options: dict[str, object] = {
        "viewport": case.viewport,
        "color_scheme": case.color_scheme,
        "reduced_motion": "reduce",
        "locale": "en-US",
    }
    # Firefox rejects the mobile/touch emulation options ("options.isMobile
    # is not supported in Firefox"); Chromium and WebKit accept them. On
    # Firefox the mobile case still runs with its viewport, theme, and
    # direction, just without isMobile/hasTouch emulation.
    if browser.browser_type.name != "firefox":
        options["is_mobile"] = case.is_mobile
        options["has_touch"] = case.has_touch
    return browser.new_context(**options)


def prepare_page(
    page: Page,
    case: BrowserCase,
    *,
    normalize_screenshot: bool = False,
) -> None:
    page.locator("html").evaluate(
        """
        (element, values) => {
          element.setAttribute("dir", values.direction);
          element.setAttribute("data-bs-theme", values.colorScheme);
        }
        """,
        {"direction": case.direction, "colorScheme": case.color_scheme},
    )
    if normalize_screenshot:
        page.add_style_tag(content=SCREENSHOT_NORMALIZATION_CSS)


def run_axe(page: Page) -> list[dict[str, object]]:
    if not AXE_PATH.is_file():
        raise AssertionError(f"Pinned axe-core asset is missing: {AXE_PATH}")
    page.add_script_tag(path=AXE_PATH)
    result = page.evaluate(
        """
        async () => axe.run(document, {
          runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
          resultTypes: ["violations"],
        })
        """
    )
    return result["violations"]


@contextmanager
def serve_directory(directory: Path) -> Iterator[str]:
    handler = partial(_QuietHandler, directory=str(directory))
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def serve_repository() -> Iterator[str]:
    with serve_directory(ROOT) as base_url:
        yield base_url
