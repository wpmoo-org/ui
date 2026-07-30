#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import shutil
import tempfile
import textwrap
import time
from html import escape
from pathlib import Path

import sass
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX workstation path owns locking.
    fcntl = None


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
SCSS = ROOT / "scss"
SITE = ROOT / "site"
SITE_SCSS = SITE / "scss"
SITE_SRC = SITE / "src"
CORE_REGISTRY = SRC / "registry"
SITE_REGISTRY = SITE_SRC / "registry"
CERTIFICATION = SRC / "certification"
PAGES = SITE_SRC / "pages"
SITE_STATIC = SITE / "static"
PACKAGE_DIST = ROOT / "dist"
SITE_DIST = ROOT / "site-dist"
SITE_PUBLIC = SITE / "public"
LLMS_TXT = SITE_PUBLIC / "llms.txt"
SITE_ROOT_ASSETS = tuple(
    SITE_PUBLIC / name
    for name in (
        "favicon.svg",
        "favicon.ico",
        "apple-touch-icon.png",
        "icon-192.png",
        "icon-512.png",
        "site.webmanifest",
    )
)
BOOTSTRAP = ROOT / "vendor/bootstrap"
GEIST = ROOT / "vendor/geist"
LUCIDE_ICONS = SRC / "icons/lucide-icons.json"
JS_COMPONENTS = SRC / "js/components"
JS_CATALOG = SITE_SRC / "js/catalog"
CORE_CSS_OUTPUTS = ("moo-ui.css", "moo-ui.min.css", "moo.css", "moo.min.css")
CORE_JS_MODULES = ("combobox.js", "sidebar.js")
EVIDENCE_FILES = (
    "pilot-evidence.json",
    "phase-1-evidence.json",
    "phase-2-evidence.json",
)
ACCEPTED_COMPONENT_EVIDENCE_STATUSES = {
    "preview-passed",
    "backfill-passed",
}
BOOTSTRAP_JS_EVIDENCE_FRAGMENT = "js/src/"
# Ownership matrix rules:
# - runtimeOwner is derived from explicit Bootstrap JS evidence or public Moo
#   ESM exports that also exist under src/js/components.
# - markupOwner defaults to Bootstrap/native HTML. Components in this table add
#   Moo-owned public selectors, attributes, or composition contracts on top of
#   Bootstrap/native markup; the source path is the reviewable citation.
MOO_MARKUP_EXTENSION_SOURCES = {
    "alert-dialog": "src/components/alert_dialog.html.jinja",
    "avatar": "src/components/avatar.html.jinja",
    "button": "src/components/button.html.jinja",
    "combobox": "src/components/combobox.html.jinja",
    "form": "src/components/field.html.jinja",
    "menubar": "src/components/menubar.html.jinja",
    "sheet": "src/components/sheet.html.jinja",
    "sidebar": "src/components/sidebar.html.jinja",
    "toast": "src/components/toast.html.jinja",
}
SOURCE_SNAPSHOT_DIRS = (
    SITE_PUBLIC,
    SITE_SRC,
    SITE_SCSS,
    SITE_STATIC,
    SRC / "components",
    JS_COMPONENTS,
    SRC / "icons",
    CORE_REGISTRY,
    SCSS,
)
BUILD_LOCK = (
    Path(tempfile.gettempdir())
    / f"moo-ui-build-{hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]}.lock"
)
SITE_NAME = "Moo UI"
SITE_ORIGIN = "https://ui.wpmoo.org"
DEFAULT_META_DESCRIPTION = (
    "Moo UI is a Bootstrap 5.3-compatible HTML component system with "
    "Bootstrap markup and a shadcn-like product interface feel."
)
HTML_TOKEN = re.compile(
    r"<!--.*?-->|<![^>]*>|</?[A-Za-z][^>]*?>",
    re.DOTALL,
)
HTML_TAG = re.compile(
    r"(?P<open></?)(?P<name>[A-Za-z][\w:-]*)(?P<attributes>.*?)(?P<close>/?>)",
    re.DOTALL,
)
HTML_ATTRIBUTE = re.compile(
    r"(?P<space>\s+)(?P<name>[^\s=/>]+)"
    r"(?:(?P<equals>\s*=\s*)(?P<value>\"[^\"]*\"|'[^']*'|[^\s>]+))?"
)
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
INLINE_CHILD_ELEMENTS = {
    "a",
    "abbr",
    "b",
    "code",
    "del",
    "em",
    "i",
    "kbd",
    "mark",
    "q",
    "s",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
}


class MissingCoreOutputsError(RuntimeError):
    """Raised when the docs build is run before the package build."""


def dedent_html(value: object) -> str:
    dedented = textwrap.dedent(str(value)).strip()
    clean_lines = "\n".join(line.rstrip() for line in dedented.splitlines())
    return re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", clean_lines)


def _inline_element(source: str, match: re.Match[str], tag_name: str, depth: int):
    if tag_name not in {"h1", "h2", "h3", "h4", "h5", "h6", "li", "p"}:
        return None

    closing = re.search(
        rf"</{re.escape(tag_name)}\s*>",
        source[match.end() :],
        re.IGNORECASE,
    )
    if closing is None:
        return None

    body = source[match.end() : match.end() + closing.start()]
    for child in HTML_TOKEN.finditer(body):
        child_match = HTML_TAG.fullmatch(child.group())
        child_name = child_match.group("name").lower() if child_match else ""
        if not child_match or child_name not in INLINE_CHILD_ELEMENTS:
            return None

    if not HTML_TOKEN.search(body):
        return None

    body = re.sub(r"\s+", " ", body).strip()
    close = closing.group()
    rendered = "\n".join(
        (
            f"{'  ' * depth}{match.group()}",
            f"{'  ' * (depth + 1)}{body}",
            f"{'  ' * depth}{close}",
        )
    )
    return rendered, match.end() + closing.end()


def format_html(value: object) -> str:
    source = dedent_html(value)
    source = _compact_lucide_icons(source)
    lines: list[str] = []
    depth = 0
    position = 0
    inline_until = 0

    for match in HTML_TOKEN.finditer(source):
        if match.start() < inline_until:
            continue

        text_content = re.sub(
            r"\s+", " ", source[position : match.start()]
        ).strip()
        if text_content:
            lines.append(f"{'  ' * depth}{text_content}")

        token = textwrap.dedent(match.group()).strip()
        tag_match = HTML_TAG.fullmatch(token)
        is_closing = token.startswith("</")
        tag_name = tag_match.group("name").lower() if tag_match else ""
        is_void = token.endswith("/>") or tag_name in VOID_ELEMENTS
        is_special = token.startswith("<!")

        if is_closing:
            depth = max(0, depth - 1)

        prefix = "  " * depth

        if not is_closing and not is_void and tag_match and "\n" not in token:
            inline_element = _inline_element(source, match, tag_name, depth)
            if inline_element:
                rendered, inline_until = inline_element
                lines.append(rendered)
                position = inline_until
                continue

            inline_close = re.match(
                rf"(?P<text>[^<>]*?)(?P<close></{re.escape(tag_name)}\s*>)",
                source[match.end() :],
                re.IGNORECASE | re.DOTALL,
            )
            if inline_close and inline_close.group("text").strip():
                inline_text = re.sub(
                    r"\s+", " ", inline_close.group("text")
                ).strip()
                lines.append(
                    f"{prefix}{token}{inline_text}{inline_close.group('close')}"
                )
                inline_until = match.end() + inline_close.end()
                position = inline_until
                continue

        lines.extend(f"{prefix}{line}" for line in token.splitlines())

        if not is_closing and not is_void and not is_special:
            depth += 1
        position = match.end()

    text_content = re.sub(r"\s+", " ", source[position:]).strip()
    if text_content:
        lines.append(f"{'  ' * depth}{text_content}")

    return "\n".join(lines)


LUCIDE_SVG = re.compile(
    r"<svg\b(?P<attrs>[^>]*)\bdata-icon=\"(?P<position>[^\"]+)\""
    r"(?P<tail>[^>]*)\bdata-lucide=\"(?P<name>[^\"]+)\""
    r"(?P<rest>[^>]*)>.*?</svg>",
    re.IGNORECASE | re.DOTALL,
)


def _compact_lucide_icons(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        icon_name = match.group("name")
        position = match.group("position")
        return (
            f'<i class="lucide lucide-{icon_name}" '
            f'data-icon="{position}" aria-hidden="true" />'
        )

    return LUCIDE_SVG.sub(replace, source)


def _syntax_token(class_name: str, value: str) -> str:
    return f'<span class="token {class_name}">{value}</span>'


def _highlight_html_attributes(value: str) -> str:
    highlighted: list[str] = []
    position = 0
    for match in HTML_ATTRIBUTE.finditer(value):
        highlighted.append(escape(value[position : match.start()]))
        highlighted.append(match.group("space"))
        highlighted.append(
            _syntax_token("attr-name", escape(match.group("name")))
        )
        if match.group("equals") is not None:
            highlighted.append(
                _syntax_token(
                    "punctuation attr-equals",
                    escape(match.group("equals")),
                )
            )
            highlighted.append(
                _syntax_token("attr-value", escape(match.group("value")))
            )
        position = match.end()
    highlighted.append(escape(value[position:]))
    return "".join(highlighted)


def _highlight_html_token(value: str) -> str:
    if value.startswith("<!--"):
        return _syntax_token("comment", escape(value))
    if value.startswith("<!"):
        return _syntax_token("doctype", escape(value))

    match = HTML_TAG.fullmatch(value)
    if match is None:
        return escape(value)

    opening = _syntax_token("punctuation", escape(match.group("open")))
    name = _syntax_token("tag", escape(match.group("name")))
    attributes = _highlight_html_attributes(match.group("attributes"))
    closing = _syntax_token("punctuation", escape(match.group("close")))
    return _syntax_token("tag", f"{opening}{name}{attributes}{closing}")


def highlight_html(value: object) -> Markup:
    source = str(value)
    highlighted: list[str] = []
    position = 0
    for match in HTML_TOKEN.finditer(source):
        highlighted.append(escape(source[position : match.start()]))
        highlighted.append(_highlight_html_token(match.group()))
        position = match.end()
    highlighted.append(escape(source[position:]))
    return Markup("".join(highlighted))


def line_numbers(value: object) -> Markup:
    count = max(1, len(str(value).splitlines()))
    return Markup("\n".join(str(number) for number in range(1, count + 1)))


def slugify(value: object) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or "section"


def pretty_url(path: object) -> str:
    value = str(path).strip()
    if value in {"", "index.html", "./"}:
        return "./"
    if value.endswith("/index.html"):
        return value[: -len("index.html")]
    if value.endswith(".html"):
        return value[: -len(".html")] + "/"
    return value


def site_href(path: object, root_path: str = "") -> str:
    value = pretty_url(path)
    if value == "./":
        return root_path or "./"
    return f"{root_path}{value}"


def canonical_url(path: object) -> str:
    value = pretty_url(path)
    if value == "./":
        return "https://ui.wpmoo.org/"
    return f"https://ui.wpmoo.org/{value}"


def pretty_output_path(path: Path) -> Path:
    if path.name == "index.html" or path.suffix != ".html":
        return path
    return path.with_suffix("") / "index.html"


def fail(message: str) -> None:
    raise ValueError(message)


def _preview_src(category: str, slug: str, root_path: str) -> str:
    directory = f"assets/images/{category}"
    for extension in ("webp", "png"):
        if (SITE_STATIC / "images" / category / f"{slug}.{extension}").is_file():
            return f"{root_path}{directory}/{slug}.{extension}"
    return f"{root_path}assets/images/placeholder.webp"


def component_preview_src(slug: str, root_path: str) -> str:
    return _preview_src("components", slug, root_path)


def block_preview_src(slug: str, root_path: str) -> str:
    return _preview_src("blocks", slug, root_path)


PAGE_META_SET = re.compile(
    r"\{%\s*set\s+(?P<name>page_(?:title|description|image|image_alt))\s*=\s*"
    r"(?P<quote>['\"])(?P<value>.*?)(?P=quote)\s*%\}",
    re.DOTALL,
)
PAGE_HEADER_CALL = re.compile(
    r"render_page_header\(\s*(?P<title_quote>['\"])(?P<title>.*?)(?P=title_quote)\s*,\s*"
    r"(?P<description_quote>['\"])(?P<description>.*?)(?P=description_quote)",
    re.DOTALL,
)
TITLE_BLOCK = re.compile(
    r"\{%\s*block\s+title\s*%\}(?P<title>.*?)\{%\s*endblock\s*%\}",
    re.DOTALL,
)


def absolute_asset_url(relative_path: str) -> str:
    return f"{SITE_ORIGIN}/{relative_path.lstrip('/')}"


def seo_image_src(category: str | None = None, slug: str | None = None) -> str:
    if category and slug:
        for extension in ("webp", "png"):
            candidate = SITE_STATIC / "images" / category / f"{slug}.{extension}"
            if candidate.is_file():
                return absolute_asset_url(f"assets/images/{category}/{slug}.{extension}")
    return absolute_asset_url("assets/images/readme-hero.webp")


def _clean_meta_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _strip_site_suffix(title: str) -> str:
    return re.sub(r"\s+[—-]\s+Moo UI$", "", title).strip()


def extract_template_metadata(page: Path) -> dict[str, str]:
    source = page.read_text(encoding="utf-8")
    metadata = {
        match.group("name"): _clean_meta_text(match.group("value"))
        for match in PAGE_META_SET.finditer(source)
    }

    header = PAGE_HEADER_CALL.search(source)
    if header:
        metadata.setdefault("page_title", _clean_meta_text(header.group("title")))
        metadata.setdefault(
            "page_description",
            _clean_meta_text(header.group("description")),
        )

    title_block = TITLE_BLOCK.search(source)
    if title_block:
        metadata.setdefault(
            "page_title",
            _strip_site_suffix(_clean_meta_text(title_block.group("title"))),
        )

    return metadata


def _find_entry(entries: list[dict[str, str]], slug: str) -> dict[str, str] | None:
    return next((entry for entry in entries if entry.get("slug") == slug), None)


def _entry_description(entry: dict[str, str] | None) -> str:
    if not entry:
        return DEFAULT_META_DESCRIPTION
    return entry.get("description") or entry.get("summary") or DEFAULT_META_DESCRIPTION


def build_site_pages(
    sections: list[dict[str, str]],
    catalog: list[dict[str, str]],
    utilities: list[dict[str, str]],
    blocks: list[dict[str, str]],
) -> list[dict[str, str]]:
    def section_page(slug: str) -> dict[str, str] | None:
        section = _find_entry(sections, slug)
        if not section:
            return None
        return {**section, "kind": "doc"}

    def child_pages(
        entries: list[dict[str, str]], section: str, kind: str
    ) -> list[dict[str, str]]:
        return [
            {
                "slug": entry["slug"],
                "label": entry["label"],
                "href": f"{section}/{entry['slug']}/",
                "kind": kind,
            }
            for entry in sorted(entries, key=lambda item: item["label"].lower())
        ]

    pages: list[dict[str, str]] = [
        {"slug": "index", "label": "Home", "href": "index.html", "kind": "doc"}
    ]
    for section in sections:
        slug = section.get("slug", "")
        if slug == "components":
            components = section_page("components")
            if components:
                pages.append(components)
            pages.extend(child_pages(catalog, "components", "component"))
            pages.extend(child_pages(utilities, "utils", "utility"))
        elif slug == "blocks":
            blocks_page = section_page("blocks")
            if blocks_page:
                pages.append(blocks_page)
            pages.extend(child_pages(blocks, "blocks", "block"))
        else:
            pages.append({**section, "kind": "doc"})

    return pages


def page_metadata(
    page: Path,
    logical_relative: Path,
    sections: list[dict[str, str]],
    catalog: list[dict[str, str]],
    utilities: list[dict[str, str]],
    blocks: list[dict[str, str]],
) -> dict[str, str]:
    path = logical_relative.as_posix()
    slug = logical_relative.stem
    kind = "doc"
    entry: dict[str, str] | None = None
    image = seo_image_src()

    if path == "index.html":
        slug = "index"
        entry = {"label": "Moo UI", "description": DEFAULT_META_DESCRIPTION}
    elif path.startswith("components/") and path != "components/index.html":
        kind = "component"
        entry = _find_entry(catalog, slug)
        image = seo_image_src("components", slug)
    elif path.startswith("utils/"):
        kind = "utility"
        entry = _find_entry(utilities, slug)
        image = seo_image_src("utilities", slug)
    elif path.startswith("blocks/") and path != "blocks/index.html" and "previews" not in path:
        kind = "block"
        entry = _find_entry(blocks, slug)
        image = seo_image_src("blocks", slug)
    else:
        normalized_path = pretty_url(path)
        entry = next(
            (section for section in sections if pretty_url(section.get("href", "")) == normalized_path),
            None,
        )
        if entry:
            slug = entry.get("slug", slug)

    template_meta = extract_template_metadata(page)
    raw_title = template_meta.get("page_title") or (entry or {}).get("label") or SITE_NAME
    description = template_meta.get("page_description") or _entry_description(entry)
    image = template_meta.get("page_image") or image
    image_alt = template_meta.get("page_image_alt") or f"{raw_title} page preview"
    title = raw_title if raw_title == SITE_NAME or raw_title.endswith("Moo UI") else f"{raw_title} — {SITE_NAME}"

    return {
        "site_name": SITE_NAME,
        "title": title,
        "description": description,
        "url": canonical_url(path),
        "image": image,
        "image_alt": image_alt,
        "type": "website" if kind == "doc" else "article",
        "slug": slug,
        "kind": kind,
    }


def load_lucide_icons() -> dict[str, object]:
    return json.loads(LUCIDE_ICONS.read_text(encoding="utf-8"))


def render_lucide_icon(icon_set: dict[str, object], name: str, position: str) -> Markup:
    icons = icon_set["icons"]
    if not isinstance(icons, dict) or name not in icons:
        raise KeyError(f"Unknown Lucide icon: {name}")

    icon = icons[name]
    if not isinstance(icon, dict):
        raise TypeError(f"Invalid Lucide icon: {name}")

    left = icon.get("left", icon_set.get("left", 0))
    top = icon.get("top", icon_set.get("top", 0))
    width = icon.get("width", icon_set.get("width", 24))
    height = icon.get("height", icon_set.get("height", 24))
    body = icon["body"]
    return Markup(
        "\n".join(
            (
                "<svg",
                f'  data-icon="{escape(position)}"',
                f'  data-lucide="{escape(name)}"',
                f'  viewBox="{left} {top} {width} {height}"',
                '  fill="none"',
                '  stroke="currentColor"',
                '  stroke-width="2"',
                '  stroke-linecap="round"',
                '  stroke-linejoin="round"',
                '  aria-hidden="true"',
                ">",
                f"  {body}",
                "</svg>",
            )
        )
    )


def create_environment(icon_renderer=None) -> Environment:
    environment = Environment(
        loader=FileSystemLoader((str(SITE_SRC), str(SRC))),
        autoescape=select_autoescape(("html", "jinja")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["dedent_html"] = dedent_html
    environment.filters["format_html"] = format_html
    environment.filters["highlight_html"] = highlight_html
    environment.filters["line_numbers"] = line_numbers
    environment.filters["slugify"] = slugify
    environment.globals["pretty_url"] = pretty_url
    environment.globals["site_href"] = site_href
    environment.globals["canonical_url"] = canonical_url
    environment.globals["fail"] = fail
    environment.globals["component_preview_src"] = component_preview_src
    environment.globals["block_preview_src"] = block_preview_src
    icon_set = load_lucide_icons()
    lucide_renderer = lambda name, position: render_lucide_icon(
        icon_set,
        name,
        position,
    )
    if icon_renderer is None:
        icon_renderer = lucide_renderer
    environment.globals["render_icon"] = icon_renderer
    return environment


def load_entries(registry_root: Path, filename: str) -> list[dict[str, str]]:
    source_file = registry_root / filename
    if not source_file.exists():
        return []
    return json.loads(source_file.read_text(encoding="utf-8"))


def _markdown_section(source: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        raise RuntimeError(f"SUPPORT.md is missing section: {heading}")
    return match.group("body").strip()


def _clean_markdown_inline(value: str) -> str:
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    return " ".join(cleaned.split())


def load_support_facts() -> dict[str, object]:
    source = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    browser_policy = [
        _clean_markdown_inline(line.removeprefix("- "))
        for line in _markdown_section(source, "Browser Policy").splitlines()
        if line.startswith("- ")
    ]
    maturity_section = _markdown_section(source, "Component Maturity")
    maturity = {}
    for match in re.finditer(
        r"\d+\.\s+\*\*(?P<label>Ready|Accepted|Certified)\*\* means "
        r"(?P<body>.*?)(?=\n\d+\.|\n\n|\Z)",
        maturity_section,
        re.DOTALL,
    ):
        maturity[match.group("label").lower()] = _clean_markdown_inline(
            match.group("body")
        )
    if sorted(maturity) != ["accepted", "certified", "ready"]:
        raise RuntimeError("SUPPORT.md maturity definitions are incomplete")
    return {
        "browserPolicy": browser_policy,
        "maturity": maturity,
        "url": "https://github.com/wpmoo-org/ui/blob/main/SUPPORT.md",
    }


def load_product_facts() -> dict[str, object]:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    certification = json.loads(
        (ROOT / "certification.json").read_text(encoding="utf-8")
    )
    return {
        "version": package["version"],
        "license": package["license"],
        "bootstrapRange": package["peerDependencies"]["bootstrap"],
        "exports": package["exports"],
        "certification": certification,
        "support": load_support_facts(),
    }


def _component_source_file(slug: str) -> Path:
    source_file = SRC / "components" / f"{slug.replace('-', '_')}.html.jinja"
    if source_file.exists():
        return source_file
    if slug == "form":
        return SRC / "components/field.html.jinja"
    raise RuntimeError(f"Missing component source for ownership derivation: {slug}")


def _load_evidence_index(inventory_path=None, evidence_paths=None) -> dict[str, dict[str, object]]:
    if inventory_path is None:
        inventory_path = CERTIFICATION / "evidence-inventory.json"
    if evidence_paths is None:
        evidence_paths = tuple(CERTIFICATION / filename for filename in EVIDENCE_FILES)

    inventory_path = Path(inventory_path)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    profiles = inventory.get("profiles", {})
    components: dict[str, dict[str, object]] = {}
    for entry in inventory.get("components", []):
        slug = entry["slug"]
        profile = entry["profile"]
        if slug in components:
            raise RuntimeError(f"Duplicate evidence inventory entry for {slug}")
        if profile not in profiles:
            raise RuntimeError(f"Unknown evidence profile for {slug}: {profile}")
        components[slug] = {
            "profile": profile,
            "profileTier": profiles[profile]["tier"],
            "accepted": False,
            "acceptedEvidence": [],
            "latestEvidence": {},
        }

    for evidence_path in evidence_paths:
        evidence_path = Path(evidence_path)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        seen_in_file: set[str] = set()
        for component in evidence.get("components", []):
            slug = component["slug"]
            if slug in seen_in_file:
                raise RuntimeError(
                    f"Duplicate evidence record for {slug} in {evidence_path.name}"
                )
            seen_in_file.add(slug)
            if slug not in components:
                raise RuntimeError(f"Evidence references unknown component: {slug}")
            status = component.get("status", "")
            if status not in ACCEPTED_COMPONENT_EVIDENCE_STATUSES:
                raise RuntimeError(
                    f"Unknown evidence status for {slug} in {evidence_path.name}: "
                    f"{status}"
                )
            expected_tier = components[slug]["profileTier"]
            evidence_tier = component.get("tier")
            if evidence_tier != expected_tier:
                raise RuntimeError(
                    f"Evidence tier conflict for {slug} in {evidence_path.name}: "
                    f"inventory has {expected_tier}, evidence has {evidence_tier}"
                )
            evidence_profile = component.get("profile")
            if evidence_profile is not None and evidence_profile != components[slug]["profile"]:
                raise RuntimeError(
                    f"Evidence profile conflict for {slug} in {evidence_path.name}: "
                    f"inventory has {components[slug]['profile']}, "
                    f"evidence has {evidence_profile}"
                )
            if status in ACCEPTED_COMPONENT_EVIDENCE_STATUSES:
                components[slug]["accepted"] = True
                components[slug]["acceptedEvidence"].append(evidence_path.name)
            components[slug]["latestEvidence"] = component

    missing_latest = [
        slug for slug, component in components.items() if not component["latestEvidence"]
    ]
    if missing_latest:
        raise RuntimeError(
            "Missing latest evidence record for components: "
            + ", ".join(sorted(missing_latest))
        )
    missing_accepted = [
        slug for slug, component in components.items() if not component["accepted"]
    ]
    if missing_accepted:
        raise RuntimeError(
            "Missing accepted evidence record for components: "
            + ", ".join(sorted(missing_accepted))
        )
    return components


def _has_bootstrap_js_evidence(sources: list[str]) -> bool:
    return any(BOOTSTRAP_JS_EVIDENCE_FRAGMENT in source for source in sources)


def _markup_owner_for_component(slug: str, source_file: Path) -> str:
    expected_source = MOO_MARKUP_EXTENSION_SOURCES.get(slug)
    if expected_source is None:
        return "Bootstrap/native HTML"

    relative_source = source_file.relative_to(ROOT).as_posix()
    if relative_source != expected_source:
        raise RuntimeError(
            f"Moo markup ownership for {slug} cites {expected_source}, "
            f"but derivation loaded {relative_source}"
        )
    if not source_file.exists():
        raise RuntimeError(f"Moo markup ownership source missing for {slug}")
    return "Moo documented extension"


def derive_component_ownership(
    catalog: list[dict[str, str]],
    certification: dict[str, object],
) -> dict[str, dict[str, object]]:
    evidence_index = _load_evidence_index()
    exported_moo_modules = {
        module.lstrip("./").removesuffix(".js")
        for module in certification.get("publicEntrypoints", {}).get("esm", [])
    }
    source_moo_modules = {path.stem for path in JS_COMPONENTS.glob("*.js")}
    if exported_moo_modules != source_moo_modules:
        raise RuntimeError(
            "Optional Moo ESM exports do not match src/js/components sources"
        )

    certified = set(certification.get("certifiedComponents", []))
    unknown_certified = certified.difference(entry["slug"] for entry in catalog)
    if unknown_certified:
        raise RuntimeError(
            "certification.json lists unknown components: "
            + ", ".join(sorted(unknown_certified))
        )
    incomplete_certified = [
        slug
        for slug in sorted(certified)
        if slug not in evidence_index
        or not evidence_index[slug]["accepted"]
        or not evidence_index[slug]["latestEvidence"]
    ]
    if incomplete_certified:
        raise RuntimeError(
            "certification.json lists components without complete evidence: "
            + ", ".join(incomplete_certified)
        )

    ownership: dict[str, dict[str, object]] = {}
    for component in catalog:
        slug = component["slug"]
        registry_status = component.get("status")
        if registry_status != "ready":
            raise RuntimeError(f"Unknown registry maturity for {slug}: {registry_status}")
        if slug not in evidence_index:
            raise RuntimeError(f"Missing evidence inventory entry for {slug}")

        evidence = evidence_index[slug]
        latest_evidence = evidence["latestEvidence"]
        bootstrap_sources = latest_evidence.get("bootstrapEvidence", [])
        if not isinstance(bootstrap_sources, list):
            raise RuntimeError(f"bootstrapEvidence must be a list for {slug}")
        has_bootstrap_js = _has_bootstrap_js_evidence(bootstrap_sources)
        runtime_owner = "native HTML/CSS"
        if slug in exported_moo_modules:
            runtime_owner = "optional Moo ESM"
        elif has_bootstrap_js:
            runtime_owner = "Bootstrap plugin"

        source_file = _component_source_file(slug)
        markup_owner = _markup_owner_for_component(slug, source_file)

        maturity = "ready"
        if evidence["accepted"]:
            maturity = "accepted"
        if slug in certified:
            maturity = "certified"

        ownership[slug] = {
            "runtimeOwner": runtime_owner,
            "markupOwner": markup_owner,
            "maturity": maturity,
            "tier": evidence["profileTier"],
            "evidence": sorted(evidence["acceptedEvidence"]),
            "knownLimitations": latest_evidence.get("limitations", [])[:2],
            "source": source_file.relative_to(ROOT).as_posix(),
        }

    return ownership


def _fallback_label(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _registry_overrides(
    registry_root: Path,
    filename: str,
) -> dict[str, dict[str, str]]:
    return {
        entry["slug"]: entry
        for entry in load_entries(registry_root, filename)
        if entry.get("slug")
    }


def _load_page_registry(
    pages_dir: Path,
    registry_root: Path,
    registry_filename: str,
    *,
    fallback_status: str = "ready",
) -> list[dict[str, str]]:
    overrides = _registry_overrides(registry_root, registry_filename)
    entries: list[dict[str, str]] = []
    for page in sorted(pages_dir.glob("*.html.jinja")):
        if page.name == "index.html.jinja":
            continue
        slug = page.with_suffix("").stem
        metadata = extract_template_metadata(page)
        override = overrides.get(slug, {})
        label = metadata.get("page_title") or override.get("label") or _fallback_label(slug)
        description = (
            metadata.get("page_description")
            or override.get("description")
            or override.get("summary")
            or DEFAULT_META_DESCRIPTION
        )
        entries.append(
            {
                **override,
                "slug": slug,
                "label": label,
                "description": description,
                "status": override.get("status", fallback_status),
            }
        )
    return sorted(entries, key=lambda entry: entry["label"].lower())


def load_catalog() -> list[dict[str, str]]:
    return _load_page_registry(
        PAGES / "components",
        CORE_REGISTRY,
        "components.json",
    )


def load_utilities() -> list[dict[str, str]]:
    return _load_page_registry(
        PAGES / "utils",
        SITE_REGISTRY,
        "utilities.json",
    )


def load_blocks() -> list[dict[str, str]]:
    return _load_page_registry(
        PAGES / "blocks",
        SITE_REGISTRY,
        "blocks.json",
    )


def style_include_paths(entrypoint: Path) -> list[str]:
    include_paths = [str(SCSS)]
    if entrypoint.is_relative_to(SITE_SCSS):
        include_paths.append(str(SITE_SCSS))
    include_paths.append(str(BOOTSTRAP / "scss"))
    return include_paths


def compile_style(entrypoint: Path, *, output_style: str = "expanded") -> str:
    css = sass.compile(
        filename=str(entrypoint),
        include_paths=style_include_paths(entrypoint),
        output_style=output_style,
    )
    return css.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def write_compiled_style(
    css_dir: Path,
    entrypoint: Path,
    output_name: str,
    *,
    output_style: str = "expanded",
) -> None:
    css = compile_style(entrypoint, output_style=output_style)
    (css_dir / output_name).write_text(css, encoding="utf-8")


def compile_core_styles() -> None:
    css_dir = PACKAGE_DIST / "assets/css"
    css_dir.mkdir(parents=True, exist_ok=True)
    write_compiled_style(css_dir, SCSS / "moo-ui.scss", "moo-ui.css")
    write_compiled_style(
        css_dir,
        SCSS / "moo-ui.scss",
        "moo-ui.min.css",
        output_style="compressed",
    )
    write_compiled_style(css_dir, SCSS / "moo-core.scss", "moo.css")
    write_compiled_style(
        css_dir,
        SCSS / "moo-core.scss",
        "moo.min.css",
        output_style="compressed",
    )


def compile_catalog_styles() -> None:
    css_dir = SITE_DIST / "assets/css"
    css_dir.mkdir(parents=True, exist_ok=True)
    write_compiled_style(css_dir, SITE_SCSS / "catalog.scss", "catalog.css")


def asset_version() -> str:
    digest = hashlib.sha256()
    paths = [
        SITE_DIST / "assets/css/moo-ui.css",
        SITE_DIST / "assets/css/catalog.css",
        *sorted(
            path
            for path in (SITE_DIST / "assets/js").rglob("*")
            if path.is_file()
        ),
    ]
    for path in paths:
        relative = path.relative_to(SITE_DIST).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def copy_package_js() -> None:
    package_js_dir = PACKAGE_DIST / "js"
    package_js_dir.mkdir(parents=True, exist_ok=True)
    for module_name in CORE_JS_MODULES:
        shutil.copy2(JS_COMPONENTS / module_name, package_js_dir / module_name)


def required_core_outputs() -> tuple[Path, ...]:
    return (
        *(PACKAGE_DIST / "assets/css" / name for name in CORE_CSS_OUTPUTS),
        *(PACKAGE_DIST / "js" / name for name in CORE_JS_MODULES),
    )


def verify_core_outputs() -> None:
    missing = [
        path.relative_to(ROOT).as_posix()
        for path in required_core_outputs()
        if not path.is_file()
    ]
    if missing:
        raise MissingCoreOutputsError(
            "Required Core outputs are missing; run "
            "`.venv/bin/python build.py --core` first: "
            + ", ".join(missing)
        )


def copy_core_outputs_to_site() -> None:
    css_dir = SITE_DIST / "assets/css"
    css_dir.mkdir(parents=True, exist_ok=True)
    for css_name in CORE_CSS_OUTPUTS:
        shutil.copy2(PACKAGE_DIST / "assets/css" / css_name, css_dir / css_name)

    components_dir = SITE_DIST / "assets/js/components"
    legacy_js_dir = SITE_DIST / "js"
    components_dir.mkdir(parents=True, exist_ok=True)
    legacy_js_dir.mkdir(parents=True, exist_ok=True)
    for module_name in CORE_JS_MODULES:
        package_module = PACKAGE_DIST / "js" / module_name
        shutil.copy2(package_module, components_dir / module_name)
        shutil.copy2(package_module, legacy_js_dir / module_name)


def copy_site_assets() -> None:
    js_dir = SITE_DIST / "assets/js"
    js_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        BOOTSTRAP / "dist/js/bootstrap.bundle.min.js",
        js_dir / "bootstrap.bundle.min.js",
    )
    shutil.copy2(
        BOOTSTRAP / "dist/js/bootstrap.bundle.min.js.map",
        js_dir / "bootstrap.bundle.min.js.map",
    )
    if JS_CATALOG.exists():
        shutil.copytree(JS_CATALOG, js_dir / "catalog", dirs_exist_ok=True)
        catalog_index = js_dir / "catalog/index.js"
        catalog_index.write_text(
            catalog_index.read_text(encoding="utf-8").replace(
                "../../../../src/js/components/",
                "../components/",
            ),
            encoding="utf-8",
        )
    fonts_dir = SITE_DIST / "assets/fonts/geist"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        GEIST / "Geist-Variable.woff2",
        fonts_dir / "Geist-Variable.woff2",
    )
    if SITE_STATIC.exists():
        shutil.copytree(SITE_STATIC, SITE_DIST / "assets", dirs_exist_ok=True)


def copy_site_metadata() -> None:
    if LLMS_TXT.exists():
        shutil.copy2(LLMS_TXT, SITE_DIST / "llms.txt")
    for path in SITE_ROOT_ASSETS:
        if path.exists():
            shutil.copy2(path, SITE_DIST / path.name)


def public_page_paths() -> list[str]:
    paths: list[str] = []
    for page in sorted(PAGES.rglob("*.html.jinja")):
        relative = page.relative_to(PAGES)
        if "previews" in relative.parts:
            continue
        logical_relative = relative.with_suffix("")
        paths.append(logical_relative.as_posix())
    return paths


def public_canonical_urls() -> list[str]:
    urls = [canonical_url(path) for path in public_page_paths()]
    if LLMS_TXT.exists():
        urls.append("https://ui.wpmoo.org/llms.txt")
    return urls


def write_sitemap() -> None:
    urls = "\n".join(
        "\n".join(
            (
                "  <url>",
                f"    <loc>{escape(url, quote=True)}</loc>",
                "  </url>",
            )
        )
        for url in public_canonical_urls()
    )
    sitemap = "\n".join(
        (
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            urls,
            "</urlset>",
            "",
        )
    )
    (SITE_DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (SITE_DIST / "robots.txt").write_text(
        "\n".join(
            (
                "User-agent: *",
                "Allow: /",
                "Sitemap: https://ui.wpmoo.org/sitemap.xml",
                "",
            )
        ),
        encoding="utf-8",
    )


def render_pages() -> None:
    environment = create_environment()
    catalog = load_catalog()
    sections = load_entries(SITE_REGISTRY, "sections.json")
    utilities = load_utilities()
    blocks = load_blocks()
    product = load_product_facts()
    component_ownership = derive_component_ownership(
        catalog,
        product["certification"],
    )
    catalog = [
        {
            **component,
            "ownership": component_ownership[component["slug"]],
        }
        for component in catalog
    ]
    site_pages = build_site_pages(sections, catalog, utilities, blocks)
    version = asset_version()
    for page in sorted(PAGES.rglob("*.html.jinja")):
        relative = page.relative_to(PAGES)
        logical_relative = relative.with_suffix("")
        output_relative = pretty_output_path(logical_relative)
        output_file = SITE_DIST / output_relative
        output_file.parent.mkdir(parents=True, exist_ok=True)
        depth = len(output_relative.parents) - 1
        root_path = "../" * depth
        current_section = logical_relative.parent.name
        current_slug = logical_relative.stem
        if current_section not in {"components", "utils", "blocks"}:
            current_section = "sections"
        template_name = page.relative_to(SITE_SRC).as_posix()
        metadata = page_metadata(
            page,
            logical_relative,
            sections,
            catalog,
            utilities,
            blocks,
        )
        rendered = environment.get_template(template_name).render(
            catalog=catalog,
            sections=sections,
            utilities=utilities,
            blocks=blocks,
            product=product,
            component_ownership=component_ownership,
            site_pages=site_pages,
            current_section=current_section,
            current_slug=metadata["slug"],
            current_page_kind=metadata["kind"],
            root_path=root_path,
            page_meta=metadata,
            page_canonical_url=metadata["url"],
            asset_version=version,
        )
        output_file.write_text(rendered, encoding="utf-8")


@contextlib.contextmanager
def build_lock():
    if fcntl is None:
        yield
        return

    BUILD_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with BUILD_LOCK.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def build() -> None:
    with build_lock():
        build_core()
        build_site()


def build_core() -> None:
    if PACKAGE_DIST.exists():
        shutil.rmtree(PACKAGE_DIST)
    PACKAGE_DIST.mkdir()
    compile_core_styles()
    copy_package_js()


def build_site() -> None:
    verify_core_outputs()
    if SITE_DIST.exists():
        shutil.rmtree(SITE_DIST)
    SITE_DIST.mkdir()
    copy_core_outputs_to_site()
    compile_catalog_styles()
    copy_site_assets()
    copy_site_metadata()
    render_pages()
    write_sitemap()


def source_snapshot() -> tuple[tuple[str, int], ...]:
    paths = [ROOT / "build.py"]
    for folder in SOURCE_SNAPSHOT_DIRS:
        if folder.exists():
            paths.extend(path for path in folder.rglob("*") if path.is_file())
    return tuple(
        sorted((str(path), path.stat().st_mtime_ns) for path in paths)
    )


def watch() -> None:
    previous: tuple[tuple[str, int], ...] = ()
    while True:
        current = source_snapshot()
        if current != previous:
            build()
            print("Built Moo UI catalog.", flush=True)
            previous = current
        time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--core", action="store_true")
    mode.add_argument("--site", action="store_true")
    args = parser.parse_args()
    try:
        if args.watch:
            if args.core or args.site:
                parser.error("--watch cannot be combined with --core or --site")
            watch()
        elif args.core:
            with build_lock():
                build_core()
        elif args.site:
            with build_lock():
                build_site()
        else:
            build()
    except MissingCoreOutputsError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
