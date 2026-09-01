from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIST = ROOT / "dist"
SITE_DIST = ROOT / "site-dist"
DIST = SITE_DIST
ICONS = ROOT / "src/icons/lucide-icons.json"
STATIC = ROOT / "site/static"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COLOR_TYPE_RGBA = 6


SCSS_IMPORT = re.compile(
    r'^[ \t]*@import[ \t]+["\']([^"\']+)["\'][ \t]*;',
    re.MULTILINE,
)


def npm_env() -> dict[str, str]:
    env = os.environ.copy()
    cache = env.get("npm_config_cache")
    if not cache or not _npm_cache_is_writable(Path(cache)):
        env["npm_config_cache"] = os.path.join(
            tempfile.gettempdir(),
            "wpmoo-npm-cache",
        )
    return env


def _npm_cache_is_writable(cache: Path) -> bool:
    try:
        probe_dir = cache / "_cacache" / "tmp"
        probe_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=probe_dir):
            pass
    except OSError:
        return False
    return True


def active_scss_imports(source: str) -> list[str]:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = "\n".join(line.split("//", 1)[0] for line in source.splitlines())
    return SCSS_IMPORT.findall(source)


def read_scss_aggregate(
    entrypoint: Path,
    prefix: str,
    *,
    root_imports: set[str] | None = None,
    source_root: Path | None = None,
    include_roots: tuple[Path, ...] | None = None,
) -> str:
    source = entrypoint.read_text(encoding="utf-8")
    if source_root is None:
        source_root = ROOT / "scss"
    if include_roots is None:
        include_roots = (source_root,)
    if root_imports is None:
        root_imports = set()

    def scss_candidates(base: Path, relative: Path) -> list[Path]:
        stem = relative.stem if relative.suffix == ".scss" else relative.name
        filename = (
            relative
            if relative.suffix == ".scss"
            else relative.with_suffix(".scss")
        )
        return [
            base / relative.parent / f"_{stem}.scss",
            base / filename,
        ]

    def resolve_from_roots(relative: Path, roots: tuple[Path, ...]) -> Path | None:
        seen_candidates: set[Path] = set()
        for root in roots:
            for candidate in scss_candidates(root, relative):
                if candidate in seen_candidates:
                    continue
                seen_candidates.add(candidate)
                if candidate.is_file():
                    return candidate
        return None

    def imported_partial(current: Path, target: str) -> Path | None:
        relative = Path(target)

        if target in root_imports:
            return resolve_from_roots(relative, (source_root,) + include_roots) or (
                source_root / f"_{target}.scss"
            )

        if target.startswith(f"{prefix}/"):
            return resolve_from_roots(relative, (source_root,)) or (
                source_root / relative.parent / f"_{relative.name}.scss"
            )

        if target.startswith(("@", "bootstrap/")):
            return None

        candidate = resolve_from_roots(relative, (current.parent,) + include_roots)
        if candidate is not None:
            return candidate

        return scss_candidates(current.parent, relative)[0]

    paths = [entrypoint]
    queue: list[Path] = []
    for target in active_scss_imports(source):
        partial = imported_partial(entrypoint, target)
        if partial is None:
            continue
        if not partial.is_file():
            raise FileNotFoundError(f"Missing imported Sass partial: {partial}")
        paths.append(partial)
        queue.append(partial)
    seen = set(paths)
    # Follow imports nested inside the included partials so their
    # declarations still contribute to the aggregate.
    while queue:
        current = queue.pop(0)
        for target in active_scss_imports(current.read_text(encoding="utf-8")):
            partial = imported_partial(current, target)
            if partial is None:
                continue
            if not partial.is_file():
                raise FileNotFoundError(f"Missing imported Sass partial: {partial}")
            if partial in seen:
                continue
            seen.add(partial)
            paths.append(partial)
            queue.append(partial)
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def read_settings() -> str:
    return read_scss_aggregate(
        ROOT / "scss/_settings.scss",
        "settings",
        root_imports={"config"},
    )


def read_catalog_styles() -> str:
    return read_scss_aggregate(
        ROOT / "site/scss/catalog.scss",
        "catalog",
        source_root=ROOT / "site/scss",
        include_roots=(ROOT / "scss", ROOT / "site/scss"),
    )


def scss_rule_body(source: str, selector: str) -> str:
    marker = f"{selector} {{"
    start = source.find(marker)
    if start < 0:
        raise AssertionError(f"Missing SCSS rule: {selector}")

    body_start = start + len(marker)
    depth = 1
    index = body_start
    quote: str | None = None
    while index < len(source):
        character = source[index]
        next_character = source[index + 1] if index + 1 < len(source) else ""

        if quote:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue

        if character in {'"', "'"}:
            quote = character
            index += 1
            continue

        if character == "/" and next_character == "*":
            comment_end = source.find("*/", index + 2)
            if comment_end < 0:
                raise AssertionError(f"Unclosed SCSS comment while reading {selector}")
            index = comment_end + 2
            continue

        if character == "/" and next_character == "/":
            line_end = source.find("\n", index + 2)
            index = len(source) if line_end < 0 else line_end + 1
            continue

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[body_start:index]
        index += 1

    raise AssertionError(f"Unbalanced SCSS rule: {selector}")


def pretty_output_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.name == "index.html" or path.suffix != ".html":
        return path
    return path.with_suffix("") / "index.html"


class CodePenPayloadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current: list[str] = []
        self._in_payload = False
        self.payloads: list[dict[str, object]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "data":
            value = (attributes.get("value") or "").strip()
            if value:
                self.payloads.append(json.loads(value))
            return

        if tag == "textarea" and attributes.get("name") == "data":
            self._current = []
            self._in_payload = True

    def handle_data(self, data: str) -> None:
        if self._in_payload:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "textarea" and self._in_payload:
            payload = "".join(self._current).strip()
            if payload:
                self.payloads.append(json.loads(payload))
            self._current = []
            self._in_payload = False


def codepen_payloads_from_html(source: str) -> list[dict[str, object]]:
    parser = CodePenPayloadParser()
    parser.feed(source)
    return parser.payloads


def codepen_payloads_from_output(relative_path: str) -> list[dict[str, object]]:
    source = (SITE_DIST / pretty_output_path(relative_path)).read_text(
        encoding="utf-8"
    )
    return codepen_payloads_from_html(source)


def codepen_payload_from_output(
    relative_path: str,
    title: str,
) -> dict[str, object]:
    for payload in codepen_payloads_from_output(relative_path):
        if payload.get("title") == title:
            return payload
    raise AssertionError(f"CodePen payload not found: {title}")


def lucide_body(name: str) -> str:
    return json.loads(ICONS.read_text(encoding="utf-8"))["icons"][name]["body"]


def read_png_ihdr(path: Path) -> tuple[int, int, int]:
    """Return (width, height, color_type) parsed from a PNG's IHDR chunk."""
    data = path.read_bytes()
    if data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file")
    width, height, _bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type


def is_valid_webp(path: Path) -> bool:
    """Check a file has a well-formed RIFF/WEBP header (any codec chunk)."""
    header = path.read_bytes()[:12]
    return header[:4] == b"RIFF" and header[8:12] == b"WEBP"


class CatalogTestCase(unittest.TestCase):
    def run_build(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def read_output(self, relative_path: str) -> str:
        return (DIST / pretty_output_path(relative_path)).read_text(
            encoding="utf-8"
        )
