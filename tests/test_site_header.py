from __future__ import annotations

import re
from html.parser import HTMLParser

from build import create_environment
from tests.helpers import DIST, CatalogTestCase

ITEMS = (
    '[{"label": "Home", "href": "/", "active": true},'
    ' {"label": "About", "href": "#", "children": ['
    '{"label": "Team", "href": "/team", "active": true}, {"label": "History", "href": "/history"}]},'
    ' {"label": "Donate", "href": "/donate", "drawer_only": true}]'
)
UTILITY = '[{"label": "Press", "href": "/press"}]'
LOGO = '{"src": "/logo.svg", "alt": "Logo name", "width": 32, "height": 32}'


def render(source: str) -> str:
    return create_environment().from_string(source).render()


def header(args: str = "", body: str = "") -> str:
    base = "" if args.startswith("brand=") else 'brand={"label": "School", "href": "/"}'
    call = (
        '{% from "blocks/site_header.html.jinja" import site_header %}'
        '{% call site_header("hdr", "Main navigation", ' + base + ((", " if base else "") + args if args else "") + ") %}"
        + body
        + "{% endcall %}"
    )
    return render(call)


class _Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


VOID = {"img", "input", "br", "hr", "meta", "link"}


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None]) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[Node] = []

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def find(self, predicate):
        if predicate(self):
            return self
        for child in self.children:
            found = child.find(predicate)
            if found is not None:
                return found
        return None


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = Node("root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def dom(html: str) -> Node:
    parser = _Tree()
    parser.feed(html)
    return parser.root


def tags(html: str) -> list[tuple[str, dict[str, str | None]]]:
    parser = _Tags()
    parser.feed(html)
    return parser.tags


def classes(attrs: dict[str, str | None]) -> set[str]:
    return set((attrs.get("class") or "").split())


class SiteHeaderTests(CatalogTestCase):
    def test_single_labelled_nav_with_expand_class_and_toggler_wiring(self) -> None:
        html = header("items=" + ITEMS)
        navs = [a for t, a in tags(html) if t == "nav"]
        self.assertEqual(len(navs), 1)
        self.assertEqual(navs[0]["aria-label"], "Main navigation")
        self.assertIn("navbar-expand-lg", classes(navs[0]))
        drawer = [a for t, a in tags(html) if "offcanvas" in classes(a) and t == "div"][0]
        self.assertIn("offcanvas-end", classes(drawer))
        toggler = [a for t, a in tags(html) if t == "button" and a.get("data-bs-toggle") == "offcanvas"][0]
        self.assertEqual(toggler["data-bs-target"], "#" + drawer["id"])
        self.assertEqual(toggler["aria-controls"], drawer["id"])
        self.assertTrue(toggler.get("aria-label"))
        self.assertIn("d-lg-none", classes(toggler))
        close = [a for t, a in tags(html) if "btn-close" in classes(a)][0]
        self.assertEqual(close["data-bs-dismiss"], "offcanvas")

    def test_xl_breakpoint(self) -> None:
        html = header('breakpoint="xl", items=' + ITEMS + ", utility_items=" + UTILITY)
        self.assertIn("navbar-expand-xl", html)
        self.assertIn("flex-xl-column-reverse", html)
        self.assertIn("d-xl-none", html)
        self.assertNotIn("-lg-", html)

    def test_brand_variants(self) -> None:
        text = tags(header())
        brand = [a for t, a in text if "navbar-brand" in classes(a)]
        self.assertEqual(len(brand), 2)  # bar and drawer header
        self.assertEqual([t for t, _ in text if t == "img"], [])
        self.assertIn("School", header())

        only = tags(header('brand={"label": "School", "href": "/", "logo": ' + LOGO + "}"))
        imgs = [a for t, a in only if t == "img"]
        self.assertTrue(imgs and all(i["alt"] == "Logo name" for i in imgs))

        both_html = header('brand={"label": "School", "href": "/", "show_label": true, "logo": ' + LOGO + "}")
        imgs = [a for t, a in tags(both_html) if t == "img"]
        self.assertTrue(imgs and all(i["alt"] == "" for i in imgs))
        self.assertIn("<span>School</span>", both_html)

    def test_mark_and_subtitle(self) -> None:
        html = header('brand={"label": "Moo UI", "href": "/", "mark": "blocks", "subtitle": "Component system"}')
        root = dom(html)
        brands = []

        def collect(node):
            if "navbar-brand" in node.classes:
                brands.append(node)
            for child in node.children:
                collect(child)

        collect(root)
        self.assertEqual(len(brands), 2)  # bar and drawer header
        for brand in brands:
            self.assertTrue({"d-flex", "align-items-center"} <= brand.classes)
            lockup = brand.children[0]
            self.assertEqual(lockup.tag, "span")
            self.assertTrue({"d-inline-flex", "align-items-center", "gap-2"} <= lockup.classes)
            mark = lockup.children[0]
            self.assertTrue({"sidebar-brand-mark", "sidebar-brand-mark--primary"} <= mark.classes)
            self.assertEqual(brand.find(lambda n: n.tag == "img"), None)
            text = lockup.children[1]
            self.assertTrue({"d-flex", "flex-column", "lh-sm"} <= text.classes)
            self.assertEqual(len(text.children), 2)
            self.assertTrue({"small", "text-body-secondary"} <= text.children[1].classes)
        self.assertIn("Moo UI", html)
        self.assertIn("Component system", html)

    def test_lockup_follows_page_direction_unless_fixed(self) -> None:
        def brand_dirs(html):
            found = []

            def walk(node):
                if "navbar-brand" in node.classes:
                    # The link keeps the page direction; a lockup's dir sits on an inner span.
                    self.assertNotIn("dir", node.attrs)
                    inner = [c.attrs.get("dir") for c in node.children if c.tag == "span" and "d-inline-flex" in c.classes]
                    found.append(inner[0] if inner else None)
                for child in node.children:
                    walk(child)

            walk(dom(html))
            return found

        cases = {
            "mark": 'brand={"label": "A", "mark": "blocks"}',
            "mark and subtitle": 'brand={"label": "A", "mark": "blocks", "subtitle": "S"}',
            "logo and label": 'brand={"label": "A", "show_label": true, "logo": ' + LOGO + "}",
        }
        for name, args in cases.items():
            with self.subTest(case=name):
                self.assertEqual(brand_dirs(header(args)), [None, None])  # bar and drawer follow the page
        for name, args in {
            "text only": 'brand={"label": "A"}',
            "logo only": 'brand={"label": "A", "logo": ' + LOGO + "}",
            "text only with dir": 'brand={"label": "A", "dir": "rtl"}',
        }.items():
            with self.subTest(case=name):
                self.assertEqual(brand_dirs(header(args)), [None, None])
        for value in ("ltr", "rtl", "auto"):
            with self.subTest(override=value):
                html = header('brand={"label": "A", "mark": "blocks", "dir": "%s"}' % value)
                self.assertEqual(brand_dirs(html), [value, value])
        for bad in ("up", "LTR"):
            with self.subTest(bad=bad):
                with self.assertRaises(Exception):
                    header('brand={"label": "A", "mark": "blocks", "dir": "%s"}' % bad)

    def test_mark_without_subtitle_and_subtitle_with_label_logo(self) -> None:
        html = header('brand={"label": "Moo UI", "mark": "blocks"}')
        self.assertIn("sidebar-brand-mark", html)
        self.assertIn("<span>Moo UI</span>", html)
        self.assertNotIn("text-body-secondary", html)
        both = header('brand={"label": "A", "subtitle": "Sub", "show_label": true, "logo": ' + LOGO + "}")
        self.assertIn("Sub", both)
        self.assertNotIn("sidebar-brand-mark", both)
        plain = header('brand={"label": "A", "subtitle": "Sub"}')
        self.assertIn("Sub", plain)

    def test_mark_and_subtitle_rules_fail(self) -> None:
        cases = {
            "mark and logo": 'brand={"label": "A", "mark": "blocks", "logo": ' + LOGO + "}",
            "subtitle with logo only": 'brand={"label": "A", "subtitle": "Sub", "logo": ' + LOGO + "}",
            "mark without label": 'brand={"label": "", "mark": "blocks"}',
        }
        for name, args in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(Exception):
                    header(args)

    def test_logo_alt_defaults_to_label(self) -> None:
        html = header('brand={"label": "School", "logo": {"src": "/l.svg"}}')
        self.assertIn('alt="School"', html)

    def test_active_state_and_dropdown_parent(self) -> None:
        html = header("items=" + ITEMS)
        parsed = tags(html)
        current = [a for t, a in parsed if a.get("aria-current") == "page"]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["href"], "/")
        # The dropdown menu marks its active child with aria-current="true".
        child = [a for t, a in parsed if a.get("aria-current") == "true"]
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0]["href"], "/team")
        self.assertIn("active", classes(child[0]))
        # Exactly the intended elements carry .active: Home, the About trigger, Team.
        active = [a for t, a in parsed if "active" in classes(a)]
        self.assertEqual(len(active), 3)
        toggle = [a for t, a in parsed if "dropdown-toggle" in classes(a)][0]
        self.assertIn("active", classes(toggle))
        inactive = header('items=[{"label": "About", "children": [{"label": "Team", "href": "/t"}]}]')
        parsed = tags(inactive)
        self.assertEqual([a for t, a in parsed if "active" in classes(a)], [])
        self.assertEqual([a for t, a in parsed if a.get("aria-current")], [])

    def test_dropdown_trigger_is_a_native_nav_link_button(self) -> None:
        parsed = tags(header("items=" + ITEMS))
        item = [a for t, a in parsed if t == "li" and "dropdown" in classes(a)][0]
        self.assertIn("nav-item", classes(item))
        trigger = [(t, a) for t, a in parsed if "dropdown-toggle" in classes(a)]
        self.assertEqual(len(trigger), 1)
        tag, attrs = trigger[0]
        self.assertEqual(tag, "button")
        self.assertEqual(attrs["type"], "button")
        self.assertIn("nav-link", classes(attrs))
        self.assertEqual(attrs["data-bs-toggle"], "dropdown")
        self.assertEqual(attrs["aria-expanded"], "false")
        self.assertNotIn("role", attrs)
        self.assertNotIn("btn", classes(attrs))
        disabled = tags(header('items=[{"label": "A", "disabled": true, "children": [{"label": "B"}]}]'))
        self.assertTrue(any("dropdown-toggle" in classes(a) and "disabled" in a for _, a in disabled))

    def test_hrefs_are_validated(self) -> None:
        for good in ("/a", "a/b:c", "#top", "?q=1", "https://example.org/x", "http://example.org", "mailto:a@example.org", "tel:+4930", "HTTPS://example.org"):
            with self.subTest(good=good):
                header('items=[{"label": "A", "href": "' + good + '"}]')
        bad = ("javascript:alert(1)", " JaVaScRiPt:alert(1)", "data:text/html,x", "vbscript:x", "java\tscript:alert(1)")
        for value in bad:
            targets = {
                "item": 'items=[{"label": "A", "href": "%s"}]' % value,
                "child": 'items=[{"label": "A", "children": [{"label": "B", "href": "%s"}]}]' % value,
                "utility": 'utility_items=[{"label": "A", "href": "%s"}]' % value,
                "brand": 'brand={"label": "A", "href": "%s"}' % value,
            }
            for where, args in targets.items():
                with self.subTest(href=value, where=where):
                    with self.assertRaises(Exception):
                        header(args)

    def test_drawer_only_class_sits_on_the_list_item(self) -> None:
        html = header("items=" + ITEMS)
        hidden = [a for t, a in tags(html) if t == "li" and "d-lg-none" in classes(a)]
        self.assertEqual(len(hidden), 1)
        self.assertIn("nav-item", classes(hidden[0]))
        self.assertEqual(html.count("d-lg-none"), 2)  # that li and the toggler

    def test_utility_list_follows_main_list_in_same_nav(self) -> None:
        html = header("items=" + ITEMS + ", utility_items=" + UTILITY)
        self.assertEqual(html.count("<nav"), 1)
        body = html[html.index("offcanvas-body"):]
        self.assertLess(body.index("About"), body.index("Press"))
        self.assertEqual(body.count('class="navbar-nav'), 2)
        body_attrs = [a for t, a in tags(html) if "offcanvas-body" in classes(a)][0]
        self.assertTrue({"d-flex", "flex-column", "flex-lg-column-reverse"} <= classes(body_attrs))
        self.assertLess(html.index("</nav>") - 1, len(html))
        self.assertNotIn("</nav>", html[:html.index("Press")])

    def test_no_utility_list_when_empty(self) -> None:
        html = header("items=" + ITEMS)
        self.assertEqual(html.count('class="navbar-nav'), 1)

    def test_surface(self) -> None:
        default_nav = [a for t, a in tags(header()) if t == "nav"][0]
        self.assertNotIn("moo-ui", classes(default_nav))
        self.assertNotIn("data-bs-theme", default_nav)
        dark_nav = [a for t, a in tags(header('surface="dark"')) if t == "nav"][0]
        self.assertIn("moo-ui", classes(dark_nav))
        self.assertEqual(dark_nav["data-bs-theme"], "dark")

    def test_actions_sit_in_drawer_body_row_after_main_list(self) -> None:
        html = header(
            "items=" + ITEMS + ", utility_items=" + UTILITY,
            body='<a class="btn" id="action-slot" href="/apply">Apply</a>',
        )
        root = dom(html)
        body = root.find(lambda n: "offcanvas-body" in n.classes)
        self.assertIsNotNone(body)
        row = body.children[0]
        self.assertTrue({"d-flex", "flex-column", "flex-lg-row", "align-items-lg-center"} <= row.classes)
        # Row children, in DOM order: the main list, then the actions wrapper.
        self.assertEqual([c.tag for c in row.children], ["ul", "div"])
        self.assertIn("navbar-nav", row.children[0].classes)
        actions = row.children[1]
        self.assertTrue({"d-flex", "align-items-center"} <= actions.classes)
        self.assertIsNotNone(actions.find(lambda n: n.attrs.get("id") == "action-slot"))
        # The utility list follows the row wrapper, still inside the body.
        self.assertEqual([c.tag for c in body.children], ["div", "ul"])
        self.assertIn("small", body.children[1].classes)
        # Nothing of the caller body leaks outside the drawer body.
        self.assertEqual(html.count("action-slot"), 1)

    def test_no_actions_wrapper_without_caller(self) -> None:
        html = render(
            '{% from "blocks/site_header.html.jinja" import site_header %}'
            '{{ site_header("hdr", "Main navigation", {"label": "School"}, items=' + ITEMS + ") }}"
        )
        body = dom(html).find(lambda n: "offcanvas-body" in n.classes)
        row = body.children[0]
        self.assertEqual([c.tag for c in row.children], ["ul"])

    def test_toggler_is_a_direct_container_child_after_the_drawer(self) -> None:
        root = dom(header("items=" + ITEMS))
        nav = root.find(lambda n: n.tag == "nav")
        container = nav.children[0]
        self.assertIn("container", container.classes)
        tags_in_order = [(c.tag, c.attrs.get("data-bs-toggle")) for c in container.children]
        self.assertEqual([t for t, _ in tags_in_order], ["a", "div", "button"])
        drawer, toggler = container.children[1], container.children[2]
        self.assertIn("offcanvas", drawer.classes)
        self.assertEqual(toggler.attrs["data-bs-toggle"], "offcanvas")
        self.assertEqual(toggler.attrs["aria-controls"], drawer.attrs["id"])
        self.assertTrue({"d-lg-none"} <= toggler.classes and "ms-auto" not in toggler.classes)
        xl = dom(header('breakpoint="xl"')).find(lambda n: n.tag == "nav").children[0].children[2]
        self.assertTrue({"d-xl-none"} <= xl.classes and "ms-auto" not in xl.classes)

    def test_extra_class_and_container(self) -> None:
        html = header('extra_class="sticky-top", container="container-xl"')
        nav = [a for t, a in tags(html) if t == "nav"][0]
        self.assertIn("sticky-top", classes(nav))
        self.assertTrue(any("container-xl" in classes(a) for _, a in tags(html)))

    def test_invalid_input_fails(self) -> None:
        cases = {
            "id": '{% call site_header("", "Nav", {"label": "A"}) %}{% endcall %}',
            "id with space": '{% call site_header("a b", "Nav", {"label": "A"}) %}{% endcall %}',
            "aria_label": '{% call site_header("h", " ", {"label": "A"}) %}{% endcall %}',
            "brand label": '{% call site_header("h", "Nav", {"label": ""}) %}{% endcall %}',
            "brand type": '{% call site_header("h", "Nav", "A") %}{% endcall %}',
            "logo src": '{% call site_header("h", "Nav", {"label": "A", "logo": {"src": ""}}) %}{% endcall %}',
            "breakpoint": '{% call site_header("h", "Nav", {"label": "A"}, breakpoint="md") %}{% endcall %}',
            "surface": '{% call site_header("h", "Nav", {"label": "A"}, surface="blue") %}{% endcall %}',
            "item label": '{% call site_header("h", "Nav", {"label": "A"}, items=[{"label": ""}]) %}{% endcall %}',
        }
        for name, call in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(Exception):
                    render('{% from "blocks/site_header.html.jinja" import site_header %}' + call)


class DropdownNavLinkTriggerTests(CatalogTestCase):
    def test_nav_link_trigger_and_unchanged_default(self) -> None:
        env = create_environment()
        head = '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
        html = env.from_string(
            head + '{% call dropdown("More", trigger="nav-link", active=true) %}'
            '{{ dropdown_item("A", href="/a") }}{% endcall %}'
        ).render()
        parsed = tags(html)
        self.assertEqual(parsed[0][0], "li")
        button = [a for t, a in parsed if t == "button"][0]
        self.assertEqual(classes(button), {"nav-link", "dropdown-toggle", "active"})
        self.assertEqual(button["data-bs-toggle"], "dropdown")
        default = env.from_string(
            head + '{% call dropdown("More") %}{{ dropdown_item("A", href="/a") }}{% endcall %}'
        ).render()
        parsed = tags(default)
        self.assertEqual(parsed[0][0], "div")
        self.assertIn("btn", classes([a for t, a in parsed if t == "button"][0]))
        for call in ('trigger="tab"', "active=true"):
            with self.subTest(call=call):
                with self.assertRaises(Exception):
                    env.from_string(head + '{% call dropdown("More", ' + call + ') %}{% endcall %}').render()


class AdditiveMacroParameterTests(CatalogTestCase):
    def test_button_aria_controls(self) -> None:
        env = create_environment()
        with_attr = env.from_string(
            '{% from "components/button.html.jinja" import button %}'
            '{{ button("Go", aria_controls="panel") }}'
        ).render()
        self.assertIn('aria-controls="panel"', with_attr)
        default = env.from_string(
            '{% from "components/button.html.jinja" import button %}{{ button("Go") }}'
        ).render()
        self.assertNotIn("aria-controls", default)
        collapse = env.from_string(
            '{% from "components/button.html.jinja" import button %}'
            '{{ button("Go", collapse_target="c", aria_controls="other") }}'
        ).render()
        self.assertEqual(collapse.count("aria-controls"), 1)
        self.assertIn('aria-controls="c"', collapse)

    def test_nav_item_item_class(self) -> None:
        env = create_environment()
        html = env.from_string(
            '{% from "components/navigation.html.jinja" import nav_item %}'
            '{{ nav_item("A", href="/a", item_class="d-lg-none", extra_class="x") }}'
        ).render()
        li = [a for t, a in tags(html) if t == "li"][0]
        self.assertEqual(classes(li), {"nav-item", "d-lg-none"})
        link = [a for t, a in tags(html) if t == "a"][0]
        self.assertNotIn("d-lg-none", classes(link))
        default = env.from_string(
            '{% from "components/navigation.html.jinja" import nav_item %}{{ nav_item("A") }}'
        ).render()
        self.assertEqual(re.search(r'<li class="([^"]*)"', default).group(1), "nav-item")


def _css_rules(css: str) -> dict[str, list[str]]:
    """Map each selector (whitespace-normalised) to its declaration blocks."""
    flat = " ".join(re.sub(r"/\*.*?\*/", "", css, flags=re.S).split())
    rules: dict[str, list[str]] = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", flat):
        for selector in re.split(r",(?![^()]*\))", selectors):
            rules.setdefault(selector.strip(), []).append(body.strip())
    return rules


class SiteHeaderRtlCssContractTests(CatalogTestCase):
    """The built stylesheet keeps the accepted logical/RTL navbar rules."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.rules = _css_rules((DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8"))

    def declared(self, selector: str, declaration: str) -> bool:
        return any(declaration in body for body in self.rules.get(selector, []))

    def test_brand_end_margin_is_logical(self) -> None:
        self.assertTrue(self.declared(".navbar-brand", "margin-inline-end: var(--bs-navbar-brand-margin-end)"))

    def test_navbar_nav_has_no_inline_start_padding(self) -> None:
        self.assertTrue(self.declared(".navbar-nav", "padding-inline-start: 0"))

    def test_dropdown_caret_gap_follows_inline_direction(self) -> None:
        for selector in (
            ".dropdown-toggle::after",
            ".dropup .dropdown-toggle::after",
            ".dropend .dropdown-toggle::after",
        ):
            with self.subTest(selector=selector):
                self.assertTrue(self.declared(selector, "margin-inline-start: 0.255em"))
        self.assertTrue(self.declared(".dropdown-toggle:empty::after", "margin-inline-start: 0"))

    def test_offcanvas_header_close_button_sits_at_inline_end(self) -> None:
        self.assertTrue(self.declared(".offcanvas-header .btn-close", "margin-inline-start: auto"))
        self.assertTrue(
            self.declared(
                ".offcanvas-header .btn-close",
                "margin-inline-end: calc(-.5 * var(--bs-offcanvas-padding-x))",
            )
        )

    def test_split_button_caret_keeps_zero_gap(self) -> None:
        for selector in (
            ".dropdown-toggle-split::after",
            ".dropup .dropdown-toggle-split::after",
            ".dropend .dropdown-toggle-split::after",
        ):
            with self.subTest(selector=selector):
                self.assertTrue(self.declared(selector, "margin-inline-start: 0"))

    def test_navbar_drawer_flips_to_the_physical_left_in_rtl(self) -> None:
        guard = ":where(.navbar *):where(:dir(rtl)):where(:not(.sheet, .sidebar))"
        border = "solid var(--bs-offcanvas-border-color)"
        for infix in ("", "-lg", "-xl"):
            end = f".offcanvas{infix}.offcanvas-end{guard}"
            start = f".offcanvas{infix}.offcanvas-start{guard}"
            closed = ":not(.showing):not(.show)"
            with self.subTest(infix=infix or "base"):
                self.assertTrue(self.declared(end, "left: 0"))
                self.assertTrue(self.declared(end, "right: auto"))
                self.assertTrue(self.declared(end + closed, "transform: translateX(-100%)"))
                self.assertTrue(self.declared(end + ".hiding", "transform: translateX(-100%)"))
                self.assertTrue(self.declared(start, "right: 0"))
                self.assertTrue(self.declared(start, "left: auto"))
                self.assertTrue(self.declared(start + closed, "transform: translateX(100%)"))
                # The border faces the content: opposite the anchored edge.
                self.assertTrue(self.declared(end, "border-left: 0"))
                self.assertTrue(self.declared(end, "border-right: var(--bs-offcanvas-border-width) " + border))
                self.assertTrue(self.declared(start, "border-right: 0"))
                self.assertTrue(self.declared(start, "border-left: var(--bs-offcanvas-border-width) " + border))

    def test_navbar_drawer_flip_excludes_sheet_and_sidebar_drawers(self) -> None:
        flipped = [s for s in self.rules if ":where(:dir(rtl))" in s and "offcanvas" in s]
        self.assertTrue(flipped)
        for selector in flipped:
            with self.subTest(selector=selector):
                self.assertIn(":where(:not(.sheet, .sidebar))", selector)
