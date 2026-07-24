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
PAGES = SRC / "pages"
SCSS = ROOT / "scss"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
LLMS_TXT = ROOT / "llms.txt"
BOOTSTRAP = ROOT / "vendor/bootstrap"
GEIST = ROOT / "vendor/geist"
LUCIDE_ICONS = SRC / "icons/lucide-icons.json"
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
        if (STATIC / "images" / category / f"{slug}.{extension}").is_file():
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
            candidate = STATIC / "images" / category / f"{slug}.{extension}"
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
    consumed_sections = {"components", "blocks"}

    remaining_sections: list[dict[str, str]] = []
    for section in sections:
        slug = section.get("slug", "")
        if slug in consumed_sections:
            continue
        if slug in {"introduction", "installation"}:
            pages.append({**section, "kind": "doc"})
        else:
            remaining_sections.append(section)
        if slug == "installation":
            components = section_page("components")
            if components:
                pages.append(components)
            pages.extend(child_pages(catalog, "components", "component"))
            pages.extend(child_pages(utilities, "utils", "utility"))
            blocks_page = section_page("blocks")
            if blocks_page:
                pages.append(blocks_page)
            pages.extend(child_pages(blocks, "blocks", "block"))

    tail_order = {"skills": 0, "changelog": 1, "disclaimer": 2, "license": 3}
    pages.extend(
        {**section, "kind": "doc"}
        for section in sorted(
            remaining_sections,
            key=lambda item: (tail_order.get(item.get("slug", ""), 99),),
        )
    )

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
        loader=FileSystemLoader(SRC),
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


def load_entries(filename: str) -> list[dict[str, str]]:
    source_file = SRC / filename
    if not source_file.exists():
        return []
    return json.loads(source_file.read_text(encoding="utf-8"))


def _fallback_label(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _registry_overrides(filename: str) -> dict[str, dict[str, str]]:
    return {entry["slug"]: entry for entry in load_entries(filename) if entry.get("slug")}


def _load_page_registry(
    pages_dir: Path,
    registry_filename: str,
    *,
    fallback_status: str = "ready",
) -> list[dict[str, str]]:
    overrides = _registry_overrides(registry_filename)
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
    return _load_page_registry(PAGES / "components", "registry/components.json")


def load_utilities() -> list[dict[str, str]]:
    return _load_page_registry(PAGES / "utils", "registry/utilities.json")


def load_blocks() -> list[dict[str, str]]:
    return _load_page_registry(PAGES / "blocks", "registry/blocks.json")


def compile_style(name: str, *, output_style: str = "expanded") -> str:
    include_paths = [str(SCSS), str(BOOTSTRAP / "scss")]
    css = sass.compile(
        filename=str(SCSS / f"{name}.scss"),
        include_paths=include_paths,
        output_style=output_style,
    )
    return css.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def write_compiled_style(
    css_dir: Path,
    source_name: str,
    output_name: str,
    *,
    output_style: str = "expanded",
) -> None:
    css = compile_style(source_name, output_style=output_style)
    (css_dir / output_name).write_text(css, encoding="utf-8")


def compile_styles() -> None:
    css_dir = DIST / "assets/css"
    css_dir.mkdir(parents=True, exist_ok=True)
    write_compiled_style(css_dir, "moo-ui", "moo-ui.css")
    write_compiled_style(css_dir, "moo-ui", "moo-ui.min.css", output_style="compressed")
    write_compiled_style(css_dir, "catalog", "catalog.css")
    write_compiled_style(css_dir, "moo-core", "moo.css")
    write_compiled_style(css_dir, "moo-core", "moo.min.css", output_style="compressed")


def asset_version() -> str:
    digest = hashlib.sha256()
    for relative in (
        "assets/css/moo-ui.css",
        "assets/css/catalog.css",
        "assets/js/bootstrap.bundle.min.js",
        "assets/js/preview.js",
    ):
        path = DIST / relative
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def copy_assets() -> None:
    js_dir = DIST / "assets/js"
    js_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        BOOTSTRAP / "dist/js/bootstrap.bundle.min.js",
        js_dir / "bootstrap.bundle.min.js",
    )
    shutil.copy2(
        BOOTSTRAP / "dist/js/bootstrap.bundle.min.js.map",
        js_dir / "bootstrap.bundle.min.js.map",
    )
    fonts_dir = DIST / "assets/fonts/geist"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        GEIST / "Geist-Variable.woff2",
        fonts_dir / "Geist-Variable.woff2",
    )
    if STATIC.exists():
        shutil.copytree(STATIC, DIST / "assets", dirs_exist_ok=True)


def copy_site_metadata() -> None:
    if LLMS_TXT.exists():
        shutil.copy2(LLMS_TXT, DIST / "llms.txt")


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
    (DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (DIST / "robots.txt").write_text(
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
    sections = load_entries("registry/sections.json")
    utilities = load_utilities()
    blocks = load_blocks()
    site_pages = build_site_pages(sections, catalog, utilities, blocks)
    version = asset_version()
    for page in sorted(PAGES.rglob("*.html.jinja")):
        relative = page.relative_to(PAGES)
        logical_relative = relative.with_suffix("")
        output_relative = pretty_output_path(logical_relative)
        output_file = DIST / output_relative
        output_file.parent.mkdir(parents=True, exist_ok=True)
        depth = len(output_relative.parents) - 1
        root_path = "../" * depth
        current_section = logical_relative.parent.name
        current_slug = logical_relative.stem
        if current_section not in {"components", "utils", "blocks"}:
            current_section = "sections"
        template_name = page.relative_to(SRC).as_posix()
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
        if DIST.exists():
            shutil.rmtree(DIST)
        DIST.mkdir()
        compile_styles()
        copy_assets()
        copy_site_metadata()
        render_pages()
        write_sitemap()


def source_snapshot() -> tuple[tuple[str, int], ...]:
    paths = [ROOT / "build.py"]
    if LLMS_TXT.exists():
        paths.append(LLMS_TXT)
    for folder in (SRC, SCSS, STATIC):
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
    args = parser.parse_args()
    if args.watch:
        watch()
    else:
        build()


if __name__ == "__main__":
    main()
