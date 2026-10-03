"""Comment policy for distributed Sass sources and compressed CSS."""

from __future__ import annotations

import re

import tinycss2


def strip_scss_line_comments(source: str) -> str:
    output: list[str] = []
    modes = ["code"]
    index = 0
    while index < len(source):
        mode = modes[-1]
        char = source[index]
        pair = source[index:index + 2]
        if char == "\\":
            output.append(source[index:index + 2])
            index += 2
            continue
        if mode in {"'", '"', "url"}:
            if pair == "#{":
                modes.append("}")
                output.append(pair)
                index += 2
                continue
            if char == mode or (mode == "url" and char == ")"):
                modes.pop()
            elif mode == "url" and char in {"'", '"', "("}:
                modes.append("url" if char == "(" else char)
        elif pair == "/*":
            end = source.find("*/", index + 2)
            if end == -1:
                raise ValueError("Unterminated SCSS block comment")
            output.append(source[index:end + 2])
            index = end + 2
            continue
        elif pair == "//":
            end = source.find("\n", index + 2)
            end = len(source) if end == -1 else end
            line_start = source.rfind("\n", 0, index) + 1
            standalone = not source[line_start:index].strip()
            while output and output[-1] in {" ", "\t"}:
                output.pop()
            index = end + int(standalone and end < len(source))
            continue
        elif char in {"'", '"'}:
            modes.append(char)
        elif mode == "}" and char == "{":
            modes.append("}")
        elif mode == "}" and char == "}":
            modes.pop()
        elif source[index:index + 4].lower() == "url(" and (
            index == 0 or not (
                source[index - 1].isalnum() or source[index - 1] in "_-"
            )
        ):
            value = source[index + 4:].lstrip()
            if value and value[0] not in {'"', "'", "$", "("}:
                modes.append("url")
                output.append(source[index:index + 4])
                index += 4
                continue
        output.append(char)
        index += 1
    if modes != ["code"]:
        raise ValueError("Unterminated SCSS string, interpolation or URL")
    return "".join(output)


def css_comments(source: str):
    """Yield actual comment tokens, including inside functions and blocks."""
    def visit(tokens):
        for token in tokens:
            if token.type == "comment":
                yield token
            yield from visit(getattr(token, "content", ()))
            yield from visit(getattr(token, "arguments", ()))

    yield from visit(tinycss2.parse_component_value_list(source))


def is_license_comment(value: str) -> bool:
    return value.startswith("!") and bool(re.search(
        r"@license\b|SPDX-License-Identifier:|Licensed under\b",
        value,
        re.IGNORECASE,
    ))


def space_css_comment_blocks(source: str) -> str:
    """Keep one blank line before comments that begin their own line."""
    lines = source.splitlines(keepends=True)
    starts = {
        comment.source_line - 1
        for comment in css_comments(source)
        if not lines[comment.source_line - 1][:comment.source_column - 1].strip()
    }
    for index in sorted(starts, reverse=True):
        if index and lines[index - 1].strip():
            lines.insert(index, "\n")
    return "".join(lines)


def strip_css_non_license_comments(source: str) -> str:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    spans = []
    for comment in css_comments(source):
        if not is_license_comment(comment.value):
            start = offsets[comment.source_line - 1] + comment.source_column - 1
            spans.append((start, source.index("*/", start + 2) + 2))
    for start, end in sorted(spans, reverse=True):
        source = source[:start] + " " + source[end:]
    return source
