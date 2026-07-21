from __future__ import annotations

import re
from typing import Iterable

import tinycss2


MOO_SCOPE = "(.moo-ui)"
GLOBAL_SELECTOR_FORBIDDEN = re.compile(
    r"(^|[,{]\s*)(?::root|html|body)\b|"
    r"\.moo-catalog\b|"
    r"\.(?:container|row|col(?:-\w+)?)\b"
)
ROOT_DARK_OWNER = re.compile(
    r'^:where\(\.\.\.\)\[data-bs-theme=(?:"dark"|dark)\]\s+\.moo-ui'
)
DETACHED_OVERLAY_BACKDROP_OWNER = re.compile(
    r"^body:has\(\.moo-ui \.modal\.show\) > \.modal-backdrop$"
)
URL_PATTERN = re.compile(r"url\((.*?)\)", re.IGNORECASE | re.DOTALL)
REMOTE_PATTERN = re.compile(r"https?://", re.IGNORECASE)
ANIMATION_KEYWORDS = {
    "alternate",
    "alternate-reverse",
    "backwards",
    "both",
    "ease",
    "ease-in",
    "ease-in-out",
    "ease-out",
    "forwards",
    "infinite",
    "inherit",
    "initial",
    "linear",
    "none",
    "normal",
    "paused",
    "reverse",
    "running",
    "step-end",
    "step-start",
    "unset",
}


def parse_stylesheet(css: str) -> list[object]:
    return tinycss2.parse_stylesheet(
        css,
        skip_comments=True,
        skip_whitespace=True,
    )


def _serialized(values: Iterable[object]) -> str:
    return tinycss2.serialize(list(values)).strip()


def _selector_parts(selector: str) -> list[str]:
    # Hide commas inside :where(html, body) before splitting selector lists.
    compact = re.sub(r":where\([^)]*\)", ":where(...)", selector)
    return [part.strip() for part in compact.split(",") if part.strip()]


def _is_allowed_state_selector(selector: str) -> bool:
    if selector.startswith(".moo-ui"):
        return True
    if DETACHED_OVERLAY_BACKDROP_OWNER.match(selector) is not None:
        return True
    return ROOT_DARK_OWNER.match(selector) is not None


def _at_keyword(rule: object) -> str:
    return getattr(rule, "lower_at_keyword", getattr(rule, "at_keyword", "")).lower()


def _scope_rules(css: str) -> list[object]:
    return [
        rule
        for rule in parse_stylesheet(css)
        if getattr(rule, "type", None) == "at-rule"
        and _at_keyword(rule) == "scope"
    ]


def _nested_rules(rule: object) -> list[object]:
    content = getattr(rule, "content", None)
    if content is None:
        return []
    return tinycss2.parse_rule_list(
        content,
        skip_comments=True,
        skip_whitespace=True,
    )


def _declarations(rule: object) -> list[object]:
    content = getattr(rule, "content", None)
    if content is None:
        return []
    return [
        declaration
        for declaration in tinycss2.parse_declaration_list(
            content,
            skip_comments=True,
            skip_whitespace=True,
        )
        if getattr(declaration, "type", None) == "declaration"
    ]


def _walk_rules(rules: Iterable[object]) -> Iterable[object]:
    for rule in rules:
        yield rule
        if getattr(rule, "content", None) is not None:
            yield from _walk_rules(_nested_rules(rule))


def assert_single_moo_scope(test_case, css: str) -> None:
    scopes = _scope_rules(css)
    test_case.assertEqual(len(scopes), 1, "moo.css must emit one @scope")
    prelude = _serialized(scopes[0].prelude).replace(" ", "")
    test_case.assertEqual(prelude, MOO_SCOPE, "@scope must target .moo-ui")


def assert_allowed_global_rules(test_case, css: str) -> None:
    for rule in parse_stylesheet(css):
        rule_type = getattr(rule, "type", None)
        if rule_type == "at-rule":
            keyword = _at_keyword(rule)
            prelude = _serialized(getattr(rule, "prelude", []))
            if keyword == "scope":
                continue
            if keyword == "keyframes":
                test_case.assertTrue(
                    prelude.startswith("moo-"),
                    f"global keyframe must be moo-prefixed: {prelude}",
                )
                continue
            if keyword == "property":
                test_case.assertTrue(
                    prelude.startswith("--moo-"),
                    f"registered property must be --moo-prefixed: {prelude}",
                )
                descriptors = {
                    declaration.name
                    for declaration in _declarations(rule)
                }
                test_case.assertLessEqual(
                    {"syntax", "inherits", "initial-value"},
                    descriptors,
                    f"@property {prelude} is missing required descriptors",
                )
                continue
            test_case.fail(f"unexpected global @{keyword} rule: {prelude}")

        if rule_type == "qualified-rule":
            selector = _serialized(rule.prelude)
            for part in _selector_parts(selector):
                test_case.assertIn(
                    ".moo-ui",
                    part,
                    f"global selector must be scoped to .moo-ui: {part}",
                )
                test_case.assertTrue(
                    _is_allowed_state_selector(part),
                    "global selector must start from .moo-ui or the supported"
                    f" root dark owner: {part}",
                )
                if DETACHED_OVERLAY_BACKDROP_OWNER.match(part) is None:
                    test_case.assertIsNone(
                        GLOBAL_SELECTOR_FORBIDDEN.search(part),
                        f"forbidden global selector emitted: {part}",
                    )
            continue

        test_case.fail(f"unexpected top-level CSS rule: {rule!r}")


def _keyframe_names(css: str) -> set[str]:
    names: set[str] = set()
    for rule in parse_stylesheet(css):
        if getattr(rule, "type", None) == "at-rule" and _at_keyword(rule) == "keyframes":
            names.add(_serialized(rule.prelude))
    return names


def _animation_references(css: str) -> set[str]:
    references: set[str] = set()
    for rule in _walk_rules(parse_stylesheet(css)):
        for declaration in _declarations(rule):
            name = declaration.name.lower()
            if name == "animation-name":
                for token in declaration.value:
                    if getattr(token, "type", None) == "ident":
                        value = token.value
                        if value.lower() != "none":
                            references.add(value)
                continue
            if name != "animation":
                continue
            for token in declaration.value:
                if getattr(token, "type", None) != "ident":
                    continue
                value = token.value
                if value.lower() in ANIMATION_KEYWORDS:
                    continue
                references.add(value)
    return references


def assert_animation_closure(test_case, css: str) -> None:
    keyframes = _keyframe_names(css)
    for name in sorted(keyframes):
        test_case.assertTrue(name.startswith("moo-"), f"unprefixed keyframe: {name}")

    for reference in sorted(_animation_references(css)):
        test_case.assertTrue(
            reference.startswith("moo-"),
            f"animation reference must be moo-prefixed: {reference}",
        )
        test_case.assertIn(
            reference,
            keyframes,
            f"animation reference has no matching keyframe: {reference}",
        )


def assert_safe_assets(test_case, css: str) -> None:
    css_without_embedded_svg = URL_PATTERN.sub(
        lambda match: ""
        if match.group(1).strip().strip("\"'").lower().startswith("data:image/svg+xml")
        else match.group(0),
        css,
    )
    test_case.assertIsNone(
        REMOTE_PATTERN.search(css_without_embedded_svg),
        "remote URL emitted",
    )
    for raw_url in URL_PATTERN.findall(css):
        value = raw_url.strip().strip("\"'")
        if value.lower().startswith("data:image/svg+xml"):
            continue
        test_case.fail(f"forbidden CSS asset URL: {value[:80]}")
