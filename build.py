#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import textwrap
import time
from html import escape
from pathlib import Path

import sass
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PAGES = SRC / "pages"
SCSS = ROOT / "scss"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
BOOTSTRAP = ROOT / "vendor/bootstrap"
GEIST = ROOT / "vendor/geist"
LUCIDE_ICONS = SRC / "icons/lucide-icons.json"

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


def fail(message: str) -> None:
    raise ValueError(message)


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
    environment.globals["fail"] = fail
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


def load_catalog() -> list[dict[str, str]]:
    return load_entries("catalog.json")


def compile_styles() -> None:
    css_dir = DIST / "assets/css"
    css_dir.mkdir(parents=True, exist_ok=True)
    include_paths = [str(SCSS), str(BOOTSTRAP / "scss")]
    for name in ("moo-ui", "catalog"):
        css = sass.compile(
            filename=str(SCSS / f"{name}.scss"),
            include_paths=include_paths,
            output_style="expanded",
        )
        (css_dir / f"{name}.css").write_text(css, encoding="utf-8")


def copy_assets() -> None:
    js_dir = DIST / "assets/js"
    js_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        BOOTSTRAP / "dist/js/bootstrap.bundle.min.js",
        js_dir / "bootstrap.bundle.min.js",
    )
    fonts_dir = DIST / "assets/fonts/geist"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        GEIST / "Geist-Variable.woff2",
        fonts_dir / "Geist-Variable.woff2",
    )
    if STATIC.exists():
        shutil.copytree(STATIC, DIST / "assets", dirs_exist_ok=True)


def render_pages() -> None:
    environment = create_environment()
    catalog = load_catalog()
    utilities = load_entries("utilities.json")
    blocks = load_entries("blocks.json")
    for page in sorted(PAGES.rglob("*.html.jinja")):
        relative = page.relative_to(PAGES)
        output_relative = relative.with_suffix("")
        output_file = DIST / output_relative
        output_file.parent.mkdir(parents=True, exist_ok=True)
        depth = len(output_relative.parents) - 1
        root_path = "../" * depth
        current_section = output_relative.parent.name
        current_slug = output_relative.stem
        if current_section not in {"components", "utils", "blocks"}:
            current_section = "index"
            current_slug = "index"
        template_name = page.relative_to(SRC).as_posix()
        rendered = environment.get_template(template_name).render(
            catalog=catalog,
            utilities=utilities,
            blocks=blocks,
            current_section=current_section,
            current_slug=current_slug,
            root_path=root_path,
        )
        output_file.write_text(rendered, encoding="utf-8")


def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    compile_styles()
    copy_assets()
    render_pages()


def source_snapshot() -> tuple[tuple[str, int], ...]:
    paths = [ROOT / "build.py"]
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
