from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import build as site_build

from tests.helpers import (
    DIST,
    ICONS,
    PNG_COLOR_TYPE_RGBA,
    ROOT,
    STATIC,
    CatalogTestCase,
    is_valid_webp,
    read_catalog_styles,
    read_png_ihdr,
    read_primary_variables,
)


COMPONENT_SELECTOR_PREFIXES = {
    "button": ("btn", "disabled"),
    # Button Group's compact select override matches Bootstrap's
    # `.input-group > .form-select` specificity, so the partial
    # legitimately references .input-group as an ancestor context.
    "button_group": ("btn", "input-group"),
    "card": ("card",),
    # Breadcrumb's collapsed-segment composition wraps Bootstrap's
    # native .dropdown inside its own .breadcrumb-dropdown-item, so
    # the partial scopes a layout rule to that Bootstrap wrapper.
    "breadcrumb": ("breadcrumb", "dropdown"),
    # Dropdown toggle rows use Bootstrap Button's .active data-api
    # state while scoped under .dropdown-item-check. Bootstrap
    # Dropdown also exposes directional wrappers such as .dropend;
    # the mobile sidebar placement rule retunes the native dropdown
    # surface while staying in the dropdown partial.
    "dropdown": ("dropdown", "dropend", "active"),
    "input": ("form-control", "form-select"),
    # Table owns Bootstrap's static table family and the horizontal
    # scroll-fade helper used beside responsive table wrappers.
    "table": ("table", "table-responsive", "scroll-fade-x"),
    # Bootstrap renders both single-line inputs and textareas through
    # the shared `.form-control` family.
    "textarea": ("form-control",),
    # Bootstrap's native select markup is the `.form-select` family,
    # not a "select-" prefixed one; Select retunes it in place.
    "select": ("form-select",),
    # Bootstrap documents vertical navs as `.nav.flex-column`, so the
    # Navigation partial may scope width fixes to that native utility.
    "navigation": ("active", "disabled", "flex-column", "nav"),
    # Bootstrap has no native sidebar component; its public namespace
    # is owned explicitly by the Sidebar partial and styles.
    "sidebar": ("sidebar",),
    # Bootstrap's pagination markup uses .page-item/.page-link, not a
    # "pagination-" prefixed family.
    # The icon-only prev/next detection reads Bootstrap's own
    # utility-class state (.d-none/.d-sm-inline/.visually-hidden)
    # inside :has(), the same way Data Table reads Bootstrap
    # utilities, rather than owning those classes.
    "pagination": ("pagination", "page", "disabled", "d-none", "d-sm-inline", "visually-hidden"),
    # Bootstrap's own horizontal/vertical divider markup is the bare
    # <hr> tag and the .vr helper class, not a "separator-" prefixed
    # family.
    "separator": ("hr", "vr"),
    # Bootstrap's checkbox markup uses the shared .form-check family,
    # not a "checkbox-" prefixed one. The invalid-state focus ring
    # rule also references .is-invalid to keep the destructive ring
    # visible on mouse click (matching _focus.scss's pattern for
    # .form-control.is-invalid and .form-select.is-invalid).
    "checkbox": ("form-check", "is-invalid"),
    # The legend reuses Bootstrap's shared .form-label class to
    # match sibling form labels.
    "radio_group": ("radio-group", "form-label"),
    # Bootstrap's switch markup uses the shared .form-switch and
    # .form-check families, not a "switch-" prefixed one.
    "switch": ("form-switch", "form-check"),
    # Bootstrap's own placeholder markup uses the shared .placeholder
    # family, not a "skeleton-" prefixed one.
    "skeleton": ("skeleton", "placeholder"),
    # Bootstrap's own Collapse plugin toggles the bare .collapsed
    # state class on the trigger; it is not "accordion-" prefixed.
    "accordion": ("accordion", "collapsed"),
    # Collapsible is a thin Bootstrap Collapse composition whose
    # trigger is still a native .btn inside the component scope.
    "collapsible": ("collapsible", "btn"),
    # Menubar is backed by Bootstrap Dropdown triggers and menus; the
    # shared dropdown/show state classes remain scoped under .menubar.
    "menubar": ("menubar", "dropdown", "show"),
    # The segmented-control track styles Bootstrap's shared
    # .nav-link/.active classes within its own .tabs-list scope,
    # rather than the .nav-pills family Navigation already owns,
    # and also fixes the grid stacking on Bootstrap's own tab-content
    # and tab-pane classes.
    "tabs": ("tabs", "nav-link", "active", "disabled", "tab-content", "tab-pane"),
    # Toggle Group composes Bootstrap's .btn-check + label.btn
    # contract and suppresses the generic pressed transform only
    # inside the .toggle-group scope.
    "toggle_group": ("toggle-group", "btn", "disabled"),
    # Dialog is the Moo catalog name for Bootstrap's Modal component;
    # its native selector family is "modal-", not "dialog-".
    "dialog": ("modal", "show"),
    # Sheet is the Moo catalog name for Bootstrap's Offcanvas
    # component; its native selector family is "offcanvas-", plus
    # the "sheet" marker class used to scope Sheet-only overrides
    # away from Sidebar's own bare .offcanvas usage.
    # Bootstrap's Offcanvas source owns .showing and .hiding as
    # transition lifecycle states alongside .show.
    "sheet": ("offcanvas", "sheet", "show", "showing", "hiding"),
    # Field retunes the spacing of Bootstrap's own shared
    # .form-label/.form-text/.invalid-feedback classes when they sit
    # inside a .field, rather than owning a "field-" prefixed family
    # of its own for them.
    "field": ("field", "form-label", "form-text", "is-invalid", "invalid-feedback"),
    # Bootstrap has no native Combobox component. The public
    # namespace is a composition of Bootstrap form-control,
    # validation, and Dropdown pieces.
    "combobox": ("combobox", "is-invalid"),
    # Bootstrap has no native Datepicker component. The public
    # namespace is a reference-style trigger/popover/calendar composition
    # around Bootstrap Button primitives (frozen in the RC.3 API
    # freeze; see DECISIONS.md for the .moo-* selector exception).
    "datepicker": (
        "moo-datepicker",
        "moo-calendar",
        "btn",
        "is-invalid",
        "show",
    ),
    # Slider keeps Bootstrap's native .form-range input as the semantic
    # control, while the plain .slider namespace owns the reference-style
    # track, fill, output, orientation, and lifecycle hook wrapper.
    "slider": ("slider", "form-range"),
    # Bootstrap Table owns the static table markup only. DataTable is
    # Moo's documented interactive composition around Bootstrap table,
    # dropdown, button, checkbox, badge, and pagination primitives.
    # The filter-picker trigger's focus-ring rule is scoped with an
    # .input-group ancestor combinator (it targets DataTable's own
    # .datatable-filter-picker-trigger, not .input-group itself), so
    # datatable legitimately references that ancestor context.
    "datatable": (
        "datatable",
        "active",
        "badge",
        "btn",
        "btn-check",
        "btn-group",
        "dropdown",
        "dropdown-header",
        "dropdown-item",
        "dropdown-item-check",
        "form-check",
        "input-group",
        "ms-auto",
        "pagination",
        "show",
        "table",
        "table-responsive",
        "text-body-secondary",
        "text-truncate",
    ),
    # Input group owns the compound surface around Bootstrap's native
    # children, so its partial may retune the edge behavior of form,
    # button, validation, and dropdown children while scoped under
    # .input-group. Bootstrap's own forms/_input-group.scss styles
    # both `.input-group > .form-control` and `> .form-select`, so
    # the group legitimately owns .form-select within its scope too.
    "input_group": (
        "input-group",
        "form-control",
        "form-select",
        "btn",
        "dropdown-menu",
        "valid-tooltip",
        "valid-feedback",
        "invalid-tooltip",
        "invalid-feedback",
        "rounded-pill",
        "show",
        "disabled",
    ),
    "close_button": ("btn-close", "disabled"),
    # Tooltip is Bootstrap's overlay component; placement/state
    # classes are emitted by Bootstrap/Popper and retuned only while
    # still scoped to the tooltip surface.
    "tooltip": (
        "tooltip",
        "bs-tooltip-auto",
        "bs-tooltip-bottom",
        "bs-tooltip-end",
        "bs-tooltip-start",
        "bs-tooltip-top",
        "fade",
        "show",
    ),
    # Bootstrap's own alert component positions its native close
    # button under `.alert-dismissible .btn-close`; this keeps that
    # ownership scoped to Alert instead of moving an Alert layout
    # rule into the standalone Close Button partial.
    "alert": ("alert",),
}


class CodePenPayloadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_codepen_form = False
        self.forms: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.payloads: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and "data-moo-codepen-form" in attributes:
            self.in_codepen_form = True
            self.forms.append(attributes)
            return
        if self.in_codepen_form and tag == "button":
            self.buttons.append(attributes)
        if (
            self.in_codepen_form
            and tag == "input"
            and attributes.get("name") == "data"
            and attributes.get("value")
        ):
            self.payloads.append(json.loads(attributes["value"]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.in_codepen_form = False


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.images: list[dict[str, str | None]] = []
        self.popover_triggers: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self.links.append(attributes)
        if tag == "button":
            self.buttons.append(attributes)
        if tag == "img":
            self.images.append(attributes)
        if tag in {"a", "button"} and attributes.get("data-bs-toggle") == "popover":
            self.popover_triggers.append({"__tag": tag, **attributes})


class CatalogContractTests(CatalogTestCase):
    INTERNAL_PUBLIC_API_SNIPPETS = (
        "Jinja macro API",
        "public macro API",
        "distributed macro",
        "ready Button macro",
        "ready Badge macro",
        "ready Dropdown Menu macro",
        "ready Dropdown Menu macros",
        "toast_target",
        "popover_dismiss_trigger()",
        "alert_dialog_header()",
        "dialog_body()",
        "table_row_actions()",
        "sidebar_provider()",
        "field_group()",
        "field_description()",
        "field_error()",
        "fieldset()",
        "field()",
        "form()",
    )
    def assert_no_internal_public_api_guidance(
        self,
        surface: str,
        path: str,
    ) -> None:
        for snippet in self.INTERNAL_PUBLIC_API_SNIPPETS:
            if snippet in surface:
                raise AssertionError(
                    f"{path} presents internal build API guidance: {snippet}"
                )

    def write_json_fixture(
        self,
        root: Path,
        name: str,
        payload: dict[str, object],
    ) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_main_scroller_keeps_keyboard_focus_targets_immediately_visible(self) -> None:
        styles = read_catalog_styles()
        match = re.search(r"\.moo-catalog__main\s*\{(?P<body>[^}]*)\}", styles)

        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("overflow-y: auto", body)
        self.assertNotIn("scroll-behavior: smooth", body)

    def test_catalog_github_link_stays_neutral_when_base_color_changes(self) -> None:
        styles = read_catalog_styles()
        match = re.search(
            r"\.moo-catalog__github-link\s*\{(?P<body>[^}]*)\}",
            styles,
        )

        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("--bs-btn-color: var(--bs-body-color);", body)
        self.assertIn("--bs-btn-bg: var(--bs-secondary-bg);", body)
        self.assertIn("--bs-btn-border-color: var(--bs-border-color);", body)
        self.assertIn("--bs-btn-hover-bg: var(--bs-tertiary-bg);", body)
        self.assertNotIn("var(--moo-primary", body)
        self.assertNotIn("var(--bs-primary", body)

    def test_settings_mode_picker_chrome_is_not_theme_builder_tinted(self) -> None:
        styles = read_catalog_styles()

        for token in (
            "--moo-settings-panel-option-border",
            "--moo-settings-panel-option-active-border",
            "--moo-settings-panel-option-check-bg",
            "--moo-settings-panel-option-check-border",
            "--moo-settings-panel-option-check-color",
            "--moo-settings-panel-option-active-check-bg",
            "--moo-settings-panel-option-active-check-border",
            "--moo-settings-panel-option-active-check-color",
        ):
            with self.subTest(token=token):
                self.assertIn(token, styles)

        theme_thumb = re.search(
            r"(?m)^\.moo-settings-panel__theme-thumb\s*\{(?P<body>[^}]*)\}",
            styles,
        )
        self.assertIsNotNone(theme_thumb)
        self.assertIn(
            "border: var(--bs-border-width) solid var(--moo-settings-panel-option-border);",
            theme_thumb.group("body"),
        )

        checked_thumb = re.search(
            r"(?m)^\.moo-settings-panel__theme-option:has\(\.btn-check:checked\) "
            r"\.moo-settings-panel__theme-thumb\s*\{(?P<body>[^}]*)\}",
            styles,
        )
        self.assertIsNotNone(checked_thumb)
        checked_thumb_body = checked_thumb.group("body")
        self.assertIn(
            "border-color: var(--moo-settings-panel-option-active-border);",
            checked_thumb_body,
        )
        self.assertNotIn("var(--moo-ring)", checked_thumb_body)

        theme_check = re.search(
            r"(?m)^\.moo-settings-panel__theme-check\s*\{(?P<body>[^}]*)\}",
            styles,
        )
        self.assertIsNotNone(theme_check)
        theme_check_body = theme_check.group("body")
        for value in (
            "border: 2px solid var(--moo-settings-panel-option-check-border);",
            "background-color: var(--moo-settings-panel-option-check-bg);",
            "color: var(--moo-settings-panel-option-check-color);",
        ):
            with self.subTest(value=value):
                self.assertIn(value, theme_check_body)

        checked_check = re.search(
            r"(?m)^\.moo-settings-panel__theme-option:has\(\.btn-check:checked\) "
            r"\.moo-settings-panel__theme-check\s*\{(?P<body>[^}]*)\}",
            styles,
        )
        self.assertIsNotNone(checked_check)
        checked_check_body = checked_check.group("body")
        for value in (
            "border-color: var(--moo-settings-panel-option-active-check-border);",
            "background-color: var(--moo-settings-panel-option-active-check-bg);",
            "color: var(--moo-settings-panel-option-active-check-color);",
        ):
            with self.subTest(value=value):
                self.assertIn(value, checked_check_body)

        for mutable_token in (
            "var(--bs-border-color)",
            "var(--bs-body-bg)",
            "var(--bs-body-color)",
        ):
            with self.subTest(mutable_token=mutable_token):
                self.assertNotIn(mutable_token, theme_thumb.group("body"))
                self.assertNotIn(mutable_token, theme_check_body)
                self.assertNotIn(mutable_token, checked_check_body)

    def test_settings_builder_color_dropdowns_render_swatch_indicators(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        page = self.read_output("components/button.html")
        settings_panel = page.split('id="catalog-settings"', 1)[1]
        style_dropdown, after_style = settings_panel.split(
            "data-moo-catalog-theme-builder-base-color", 1
        )
        base_dropdown, after_base = after_style.split(
            "data-moo-catalog-theme-builder-theme-color", 1
        )
        theme_dropdown, after_theme = after_base.split(
            "data-moo-catalog-theme-builder-chart-color", 1
        )
        chart_dropdown, font_dropdowns = after_theme.split(
            "data-moo-catalog-theme-builder-heading-font", 1
        )

        self.assertNotIn("data-moo-catalog-theme-builder-swatch", style_dropdown)
        for swatch in (
            "base-color-neutral",
            "base-color-zinc",
            "base-color-stone",
            "base-color-mauve",
            "base-color-olive",
            "base-color-mist",
            "base-color-taupe",
        ):
            with self.subTest(swatch=swatch):
                self.assertIn(
                    f'data-moo-catalog-theme-builder-swatch="{swatch}"',
                    base_dropdown,
                )
        self.assertNotIn('data-moo-catalog-theme-builder-swatch="base-color-blue"', base_dropdown)
        for swatch in (
            "theme-color-neutral",
            "theme-color-blue",
            "theme-color-azure",
            "theme-color-indigo",
            "theme-color-purple",
            "theme-color-orange",
            "theme-color-pink",
            "theme-color-red",
            "theme-color-yellow",
            "theme-color-lime",
            "theme-color-green",
            "theme-color-teal",
            "theme-color-cyan",
        ):
            with self.subTest(swatch=swatch):
                self.assertIn(
                    f'data-moo-catalog-theme-builder-swatch="{swatch}"',
                    theme_dropdown,
                )
        for swatch in (
            "chart-color-neutral",
            "chart-color-blue",
            "chart-color-azure",
            "chart-color-indigo",
            "chart-color-purple",
            "chart-color-orange",
            "chart-color-pink",
            "chart-color-red",
            "chart-color-yellow",
            "chart-color-lime",
            "chart-color-green",
            "chart-color-teal",
            "chart-color-cyan",
        ):
            with self.subTest(swatch=swatch):
                self.assertIn(
                    f'data-moo-catalog-theme-builder-swatch="{swatch}"',
                    chart_dropdown,
                )
        self.assertNotIn("data-moo-catalog-theme-builder-swatch", font_dropdowns)

        styles = read_catalog_styles()
        self.assertIn(
            ".moo-settings-panel__dropdown-item[data-moo-catalog-theme-builder-swatch] "
            ".dropdown-item-check__indicator",
            styles,
        )
        self.assertIn(
            'data-moo-catalog-theme-builder-swatch="theme-color-blue"',
            styles,
        )

    def test_visible_component_lists_are_sorted_by_label(self) -> None:
        sorted_loop = (
            '{% for component in catalog | sort(attribute="label") %}'
        )

        for path in (
            ROOT / "site/src/shell/sidebar.html.jinja",
            ROOT / "site/src/pages/components/index.html.jinja",
        ):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertTrue(
                    sorted_loop in path.read_text(encoding="utf-8"),
                    f"{path.relative_to(ROOT)} must sort components by label",
                )

    def test_ready_components_have_catalog_icons(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        component_index = self.read_output("components/index.html")

        self.assertIn('href="../components/chart/"', component_index)
        self.assertNotRegex(
            component_index,
            r'href="\.\./components/chart/"[^>]*>[\s\S]{0,240}?data-lucide="component"',
        )

    def test_dashboard_charts_put_stable_ids_on_the_public_root(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        overview = self.read_output("examples/dashboard/overview/index.html")

        self.assertRegex(
            overview,
            r'<div class="moo-chart moo-dashboard-chart" id="overview-revenue-chart"',
        )
        self.assertRegex(
            overview,
            r'<div class="moo-chart moo-dashboard-chart" id="overview-visitors-chart"',
        )
        self.assertNotRegex(
            overview,
            r'<canvas id="overview-(?:revenue|visitors)-chart"',
        )

    def test_ready_example_preview_images_are_present_and_valid(self) -> None:
        examples = site_build.load_examples()

        missing = []
        for example in examples:
            slug = example["slug"]
            path = STATIC / "images/examples" / f"{slug}.png"
            if not path.is_file():
                missing.append(slug)
                continue

            width, height, _color_type = read_png_ihdr(path)
            with self.subTest(slug=slug):
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                self.assertAlmostEqual(width / height, 16 / 9, delta=0.02)

        self.assertEqual(missing, [])

    def _load_example_preview_generator(self):
        path = ROOT / "scripts/generate_example_previews.py"
        spec = importlib.util.spec_from_file_location(
            "generate_example_previews",
            path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        return generator

    def test_example_preview_generator_covers_every_example_page(self) -> None:
        generator = self._load_example_preview_generator()

        generator_slugs = set(generator.resolve_example_slugs(generator.parse_args([])))
        expected_slugs = {example["slug"] for example in site_build.load_examples()}

        self.assertEqual(generator_slugs, expected_slugs)

    def test_example_preview_generator_can_refresh_a_single_example(self) -> None:
        generator = self._load_example_preview_generator()

        self.assertEqual(
            generator.resolve_example_slugs(generator.parse_args(["dashboard/overview"])),
            ("dashboard/overview",),
        )
        self.assertEqual(generator.parse_args([]).slugs, [])

    def test_ready_component_sidebar_icons_do_not_fall_back_for_new_components(self) -> None:
        source = (ROOT / "site/src/includes/component-icons.html.jinja").read_text(
            encoding="utf-8"
        )

        for slug in (
            "alert-dialog",
            "combobox",
            "context-menu",
            "datatable",
            "form",
            "menubar",
            "skeleton",
            "toggle-group",
        ):
            with self.subTest(slug=slug):
                self.assertRegex(source, rf'"{re.escape(slug)}":\s*"(?!component")')

    def test_form_adjacent_sidebar_icons_use_distinct_semantic_glyphs(self) -> None:
        source = (ROOT / "site/src/includes/component-icons.html.jinja").read_text(
            encoding="utf-8"
        )

        for slug, icon in (
            ("form", "form"),
            ("field", "rectangle-ellipsis"),
            ("input-group", "brackets"),
            ("skeleton", "square-dashed"),
        ):
            with self.subTest(slug=slug):
                self.assertRegex(source, rf'"{re.escape(slug)}":\s*"{icon}"')

    def test_public_site_does_not_claim_certified_components_before_certification(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        surfaces = {
            "home": self.read_output("index.html"),
            "examples": self.read_output("examples/index.html"),
            "tasks": self.read_output("examples/dashboard/tasks.html"),
        }

        for name, output in surfaces.items():
            with self.subTest(surface=name):
                self.assertNotIn("certified components", output)
                self.assertNotIn("certified Data Table", output)

    def test_codepen_payloads_do_not_claim_certified_components_before_certification(self) -> None:
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(certification["status"], "preview")
        self.assertEqual(certification["certifiedComponents"], [])

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        claim_pattern = re.compile(r"\bcertified\b[^.]{0,160}\bcomponents?\b")
        for path in sorted((ROOT / "site-dist").rglob("*.html")):
            parser = CodePenPayloadParser()
            parser.feed(path.read_text(encoding="utf-8"))
            for index, payload in enumerate(parser.payloads):
                for key in ("title", "description", "html", "css", "js"):
                    text = " ".join(unescape(str(payload.get(key, ""))).lower().split())
                    with self.subTest(
                        page=path.relative_to(ROOT / "site-dist").as_posix(),
                        payload=index,
                        key=key,
                    ):
                        self.assertIsNone(claim_pattern.search(text))

    def test_codepen_payloads_do_not_import_unpublished_pinned_package_entrypoints(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        codepen_version = site_build.CODEPEN_CDN_VERSION
        published_rc2_js_entrypoints = {"datatable.js"}
        import_pattern = re.compile(
            rf"@wpmoo/ui@{re.escape(codepen_version)}/dist/js/(?P<entrypoint>[a-z.-]+\.js)"
        )

        for path in sorted((ROOT / "site-dist").rglob("*.html")):
            parser = CodePenPayloadParser()
            parser.feed(path.read_text(encoding="utf-8"))
            for index, payload in enumerate(parser.payloads):
                for match in import_pattern.finditer(str(payload.get("js", ""))):
                    entrypoint = match.group("entrypoint")
                    with self.subTest(
                        page=path.relative_to(ROOT / "site-dist").as_posix(),
                        payload=index,
                        entrypoint=entrypoint,
                    ):
                        self.assertIn(entrypoint, published_rc2_js_entrypoints)

    def test_codepen_hides_rc3_only_interactive_examples_until_cdn_is_current(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertNotEqual(
            site_build.CODEPEN_CDN_VERSION,
            json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"],
        )
        for path in (
            "components/chart.html",
            "components/datepicker.html",
            "components/slider.html",
            "charts/index.html",
        ):
            with self.subTest(path=path):
                page = self.read_output(path)
                self.assertNotIn("Try in CodePen", page)
                self.assertNotIn("data-moo-codepen-form", page)

    def test_codepen_runtime_gating_policy_is_owned_by_codepen_include(self) -> None:
        codepen_source = (ROOT / "site/src/includes/codepen.html.jinja").read_text(
            encoding="utf-8"
        )
        self.assertIn("codepen_button_if_available", codepen_source)
        self.assertIn("codepen_current_package_required_slugs", codepen_source)

        for template in (
            "site/src/includes/example.html.jinja",
            "site/src/includes/chart-template.html.jinja",
        ):
            with self.subTest(template=template):
                source = (ROOT / template).read_text(encoding="utf-8")
                self.assertNotIn("product.codepenCdnVersion", source)
                self.assertNotIn("codepenCurrentPackage", source)
                self.assertNotIn('"chart", "datepicker", "slider"', source)

    def test_public_changelog_does_not_claim_certified_components_before_certification(self) -> None:
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(certification["status"], "preview")
        self.assertEqual(certification["certifiedComponents"], [])
        source = (ROOT / "site/src/pages/changelog.html.jinja").read_text(
            encoding="utf-8"
        )
        normalized_source = " ".join(source.split())

        forbidden_claims = (
            "certified Tier 3 components",
            "certified components",
            "certified Data Table",
        )
        for claim in forbidden_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, normalized_source)

    def test_users_example_uses_tasks_datatable_toolbar_pattern(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        users = self.read_output("examples/dashboard/users.html")

        self.assertIn('data-datatable-filter-mode="picker"', users)
        self.assertIn("datatable-view-toggle", users)
        self.assertIn('data-datatable-view="table"', users)
        self.assertIn('value="cards"', users)
        self.assertNotIn('data-datatable-filter-mode="inline"', users)
        self.assertNotIn("datatable--responsive-scroll", users)

    def test_dashboard_overview_owns_one_page_wrapper_and_unique_chart_types(self) -> None:
        page_source = (
            ROOT / "site/src/pages/examples/dashboard/overview.html.jinja"
        ).read_text(encoding="utf-8")
        block_source = (
            ROOT / "site/src/blocks/dashboard_overview.html.jinja"
        ).read_text(encoding="utf-8")

        self.assertEqual(page_source.count('class="moo-examples-page"'), 1)
        self.assertNotIn('class="moo-examples-page"', block_source)
        self.assertNotIn('style="', block_source)

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("examples/dashboard/overview.html")

        self.assertEqual(page.count('data-chart="line"'), 1)
        self.assertEqual(page.count('data-chart="bar"'), 1)
        self.assertNotIn("data-chart data-chart=", page)

    def test_dashboard_codepen_css_carries_catalog_only_utility(self) -> None:
        source = (ROOT / "site/src/includes/codepen.html.jinja").read_text(
            encoding="utf-8"
        )

        dashboard_css = source.split(
            "{% macro dashboard_codepen_css() -%}", 1
        )[1].split("{%- endmacro %}", 1)[0]
        self.assertIn(".ls-wide", dashboard_css)

    def test_public_docs_use_moo_ui_brand_name_in_prose(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        surfaces = {
            "home": self.read_output("index.html"),
            "installation": self.read_output("installation.html"),
            "skills": self.read_output("skills.html"),
            "changelog": self.read_output("changelog.html"),
            "components": self.read_output("components/index.html"),
            "readme": (ROOT / "README.md").read_text(encoding="utf-8"),
            "llms": (ROOT / "site/public/llms.txt").read_text(encoding="utf-8"),
        }
        forbidden_brand_fragments = (
            "Moo-owned",
            "Moo owned",
            "Moo's",
            "Moo ESM",
            "Moo stylesheet",
            "Moo stylesheets",
            "Moo component layer",
            "Moo documented extension",
        )

        for name, surface in surfaces.items():
            with self.subTest(surface=name):
                for fragment in forbidden_brand_fragments:
                    self.assertNotIn(fragment, surface)

    def test_acceptance_portal_marks_mobile_keyboard_checks_not_applicable(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("acceptance/rc2.html")
        self.assertNotIn("acceptance-accordion-iphone-keyboard", page)
        self.assertNotIn("acceptance-accordion-android-keyboard", page)
        self.assertIn(
            'data-moo-acceptance-kind="Keyboard" data-moo-acceptance-state="N/A"',
            page,
        )
        self.assertNotIn(
            'type="checkbox" disabled aria-label="Keyboard not applicable on iPhone"',
            page,
        )
        self.assertNotIn(
            'type="checkbox" disabled aria-label="Keyboard not applicable on Android"',
            page,
        )
        self.assertIn(
            '<span class="moo-acceptance__matrix-na" aria-label="Keyboard not applicable on iPhone">&ndash;</span>',
            page,
        )
        self.assertIn(
            '<span class="moo-acceptance__matrix-na" aria-label="Keyboard not applicable on Android">&ndash;</span>',
            page,
        )

    def test_certification_fixtures_get_build_time_pagination(self) -> None:
        source = (
            ROOT / "tests/fixtures/certification/accordion.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("moo-fixture-pagination", source)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        accordion = (
            DIST / "tests/fixtures/certification/accordion.html"
        ).read_text(encoding="utf-8")
        alert = (
            DIST / "tests/fixtures/certification/alert.html"
        ).read_text(encoding="utf-8")
        self.assertIn('class="moo-fixture-pagination"', accordion)
        self.assertIn('href="alert.html"', accordion)
        self.assertIn('aria-label="Next fixture: Alert"', accordion)
        self.assertIn('href="accordion.html"', alert)
        self.assertIn('aria-label="Previous fixture: Accordion"', alert)

    def test_llms_txt_lists_ready_components_alphabetically(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        expected = [
            f"- [{item['label']}](https://ui.wpmoo.org/components/{item['slug']}/)"
            for item in sorted(
                (item for item in catalog if item["status"] == "ready"),
                key=lambda item: item["label"].casefold(),
            )
        ]

        lines = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8").splitlines()
        start = lines.index("## Component Catalog")
        end = lines.index("## Utilities And Blocks")
        component_lines = [
            line
            for line in lines[start + 1 : end]
            if line.startswith("- [")
            and "/components/" in line
            and not line.startswith("- [Components]")
        ]

        self.assertEqual(component_lines, expected)

    def test_llms_txt_cdn_example_tracks_package_version(self) -> None:
        package = json.loads(
            (ROOT / "package.json").read_text(encoding="utf-8")
        )
        llms = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8")
        match = re.search(
            r"https://unpkg\.com/@wpmoo/ui@([^/]+)/dist/assets/css/moo-ui\.css",
            llms,
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), package["version"])

    def test_icons_render_from_local_lucide_json_source(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(ICONS.is_file())
        self.assertFalse((DIST / "assets/icons/lucide-icons.json").exists())

        icon_data = json.loads(ICONS.read_text(encoding="utf-8"))
        self.assertEqual(icon_data["prefix"], "lucide")
        self.assertIn("arrow-left", icon_data["icons"])
        self.assertIn("audio-lines", icon_data["icons"])

        button_template = (
            ROOT / "src/components/button.html.jinja"
        ).read_text(encoding="utf-8")
        self.assertIn("render_icon(name, position)", button_template)
        self.assertNotIn("lucide_icon(", button_template)
        self.assertNotIn("{% if name ==", button_template)

        for path in (
            ROOT / "src/components/dropdown_menu.html.jinja",
            ROOT / "site/src/includes/example.html.jinja",
        ):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("render_icon(", source)
                self.assertNotIn("lucide_icon(", source)

    def test_icons_need_no_cdn_or_runtime_script(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for path in DIST.rglob("*.html"):
            page = path.read_text(encoding="utf-8")
            for script_source in re.findall(
                r'<script\b[^>]*\bsrc="([^"]+)"', page
            ):
                self.assertNotRegex(script_source, r"^(?:https?:)?//")
                self.assertNotRegex(script_source, r"(?i)(?:iconify|lucide)")

    def test_component_scss_stays_inside_bootstrap_selector_ownership(self) -> None:
        allowed_prefixes = COMPONENT_SELECTOR_PREFIXES

        for path in sorted((ROOT / "scss/components").glob("*.scss")):
            source = "\n".join(
                line.split("//", 1)[0]
                for line in path.read_text(encoding="utf-8").splitlines()
            )
            component = path.stem.removeprefix("_")
            prefixes = allowed_prefixes.get(
                component,
                (component.replace("_", "-"),),
            )

            for class_name in set(re.findall(r"\.([a-z][a-z0-9_-]*)", source)):
                with self.subTest(component=component, selector=class_name):
                    if component == "alert" and class_name == "btn-close":
                        self.assertIn(".alert-dismissible .btn-close", source)
                        self.assertNotIn(
                            ".btn-close",
                            source.replace(".alert-dismissible .btn-close", ""),
                        )
                        continue
                    self.assertTrue(
                        any(
                            class_name == prefix
                            or class_name.startswith(f"{prefix}-")
                            or class_name.startswith(f"{prefix}__")
                            for prefix in prefixes
                        ),
                        f".{class_name} belongs to another component or catalog chrome",
                    )

    def test_datepicker_frozen_moo_namespaces_stay_in_selector_allowlist(self) -> None:
        """Lock the approved .moo-* selector exception for Datepicker.

        DECISIONS.md approves .moo-datepicker and .moo-calendar as public
        Datepicker namespaces despite the default "plain namespace" rule, so
        this test keeps them inside the selector-ownership allow-list. Removing
        the exception requires a new decision, not a silent gate edit."""
        prefixes = COMPONENT_SELECTOR_PREFIXES["datepicker"]
        self.assertIn("moo-datepicker", prefixes)
        self.assertIn("moo-calendar", prefixes)

    def test_component_pages_compose_ready_macros_only(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        ready = {
            item["slug"] for item in catalog if item["status"] == "ready"
        }
        infrastructure = {"example"}
        component_class = re.compile(
            r"^(?:accordion|alert|badge|breadcrumb|btn|card|dropdown|"
            r"form-check|form-control|form-label|input-group|list-group|"
            r"modal|nav|navbar|offcanvas|page|pagination|placeholder|"
            r"popover|progress|spinner|table|toast)(?:-|$)"
        )
        page_level_classes = {
            "form-label",
            "form-control",
            # Catalog demo surfaces that are not ready component macros: the
            # Card spacing demo's live toggle hook and its scrollable body
            # strip are documented examples, not product components.
            "card-spacing-demo",
            "card-scroll",
            # Button Group's compact select modifier: a layout hint passed
            # to the select macro's extra_class, not raw component markup.
            "btn-group-select",
            # Checkbox's Table example uses Bootstrap's native table classes
            # directly (not a Moo table macro) to embed checkboxes in rows.
            "table-responsive",
            "table",
            "table-sm",
            # Bootstrap's RTL flip for form-check: passed via extra_class to
            # the checkbox macro in RTL examples so the input appears on the
            # right side of the label (matching Bootstrap's RTL CSS behavior).
            "form-check-reverse",
        }

        pages = [
            *sorted((ROOT / "site/src/pages/components").glob("*.jinja")),
            # The components index composes the same ready macros; it gets no
            # exemption.
            ROOT / "site/src/pages/components/index.html.jinja",
        ]
        for path in pages:
            source = path.read_text(encoding="utf-8")

            with self.subTest(page=path.name, contract="interactive markup"):
                # Native <input type="time"> is allowed as a composition
                # example (pairing Date Picker with a native time input).
                source_no_time_input = re.sub(
                    r'<input\s+type="time"[^>]*>', '', source
                )
                self.assertNotRegex(
                    source_no_time_input,
                    r"<(?:button|form|input|kbd|select|textarea)\b",
                )

            imports = re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
            for imported in imports:
                with self.subTest(page=path.name, imported=imported):
                    self.assertTrue(
                        imported in infrastructure
                        or imported.replace("_", "-") in ready,
                        f"{imported} is not a ready component macro",
                    )

            for class_value in re.findall(r'class="([^"]*)"', source):
                for class_name in class_value.split():
                    with self.subTest(page=path.name, class_name=class_name):
                        if class_name in page_level_classes:
                            continue
                        self.assertIsNone(
                            component_class.match(class_name),
                            f".{class_name} must come from a ready component macro",
                        )

    def test_component_pages_link_to_bootstrap_documentation(self) -> None:
        for path in sorted((ROOT / "site/src/pages/components").glob("*.jinja")):
            # The components index lists every component; it documents no
            # single Bootstrap component itself, so it carries no reference.
            if path.name == "index.html.jinja":
                continue
            source = path.read_text(encoding="utf-8")

            with self.subTest(page=path.name, contract="reference import"):
                self.assertRegex(
                    source,
                    r'{%\s*from\s+"includes/documentation-reference\.html\.jinja"\s+'
                    r'import\s+render_reference\s+with\s+context\s*%}',
                )
            with self.subTest(page=path.name, contract="reference call"):
                self.assertIn("render_reference(", source)

    def test_external_blank_links_use_noopener_noreferrer(self) -> None:
        for source_root in (ROOT / "site/src", ROOT / "src"):
            for path in sorted(source_root.rglob("*.jinja")):
                source = path.read_text(encoding="utf-8")
                for tag in re.findall(r"<a\b[^>]*target=\"_blank\"[^>]*>", source):
                    with self.subTest(path=path.relative_to(ROOT), tag=tag):
                        self.assertIn('rel="', tag)
                        rel = re.search(r'rel="([^"]*)"', tag)
                        self.assertIsNotNone(rel)
                        tokens = set(rel.group(1).split())
                        self.assertIn("noopener", tokens)
                        self.assertIn("noreferrer", tokens)

    def test_ready_component_preview_images_are_present_and_valid(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        ready_slugs = [
            item["slug"] for item in catalog if item["status"] == "ready"
        ]
        previews_dir = STATIC / "images/components"
        placeholder = STATIC / "images/placeholder.webp"

        self.assertTrue(
            is_valid_webp(placeholder),
            "the shared component preview fallback must be a valid WebP file",
        )

        for slug in ready_slugs:
            with self.subTest(slug=slug):
                png_path = previews_dir / f"{slug}.png"
                webp_path = previews_dir / f"{slug}.webp"
                if not png_path.is_file() and not webp_path.is_file():
                    self.fail(f"{slug} is ready but still uses placeholder.webp")
                if webp_path.is_file():
                    self.assertTrue(
                        is_valid_webp(webp_path),
                        f"{slug}.webp is not a well-formed WebP file",
                    )
                    continue
                width, height, color_type = read_png_ihdr(png_path)
                self.assertEqual((width, height), (1536, 1024), slug)
                self.assertEqual(
                    color_type,
                    PNG_COLOR_TYPE_RGBA,
                    f"{slug}.png is not RGBA (color type {color_type})",
                )

    def test_catalog_builds_the_complete_root_favicon_set(self) -> None:
        svg = (ROOT / "site/public/favicon.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 24 24"', svg)
        self.assertIn("prefers-color-scheme: dark", svg)
        self.assertIn('stroke="currentColor"', svg)
        self.assertNotRegex(
            svg,
            r"(?i)<script|javascript:|foreignObject|(?:xlink:)?href=|@import|url\(",
        )

        expected_png_sizes = {
            "apple-touch-icon.png": (180, 180),
            "icon-192.png": (192, 192),
            "icon-512.png": (512, 512),
        }
        for name, expected_size in expected_png_sizes.items():
            with self.subTest(name=name):
                width, height, _ = read_png_ihdr(ROOT / "site/public" / name)
                self.assertEqual((width, height), expected_size)

        ico = (ROOT / "site/public/favicon.ico").read_bytes()
        self.assertEqual(ico[:6], b"\x00\x00\x01\x00\x03\x00")
        self.assertEqual(
            [(ico[6 + index * 16] or 256, ico[7 + index * 16] or 256) for index in range(3)],
            [(16, 16), (32, 32), (48, 48)],
        )

        manifest = json.loads(
            (ROOT / "site/public/site.webmanifest").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "Moo UI")
        self.assertEqual(manifest["short_name"], "Moo UI")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(
            [(icon["src"], icon["sizes"], icon["type"]) for icon in manifest["icons"]],
            [
                ("/icon-192.png", "192x192", "image/png"),
                ("/icon-512.png", "512x512", "image/png"),
            ],
        )

        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        root_assets = (
            "favicon.svg",
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "site.webmanifest",
        )
        for name in root_assets:
            self.assertTrue((DIST / name).is_file(), name)

        page = self.read_output("introduction/index.html")
        self.assertIn('<link rel="icon" type="image/svg+xml" href="../favicon.svg">', page)
        self.assertIn('<link rel="icon" href="../favicon.ico" sizes="any">', page)
        self.assertIn('<link rel="apple-touch-icon" href="../apple-touch-icon.png">', page)
        self.assertIn('<link rel="manifest" href="../site.webmanifest">', page)
        self.assertNotIn("data-moo-favicon", page)

    def test_components_index_uses_admin_shell_primitives(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("components/index.html")

        for contract in (
            'data-moo-shell="catalog"',
            'class="sidebar-wrapper"',
            'id="catalog-sidebar"',
            'data-sidebar-trigger',
            "moo-catalog__search-trigger",
            "wpmoo-org/ui",
            'aria-label="Catalog navigation"',
            "input-group",
            "dropdown-menu",
            "moo-catalog__toolbar--components",
            "moo-catalog__searchbar",
            "moo-catalog__filter-trigger",
            "moo-catalog__filter-option",
            "data-moo-catalog-filter-multi",
            "data-moo-catalog-filter-clear",
            'data-moo-catalog-section-filter="components"',
            'data-moo-catalog-section-filter="utilities"',
            "scroll-fade-y no-scrollbar",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, index)
        self.assertNotIn("moo-catalog__status-select", index)
        self.assertRegex(index, r'class="[^"]*\bbadge\b')
        self.assertRegex(index, r'class="[^"]*\bbtn\b[^"]*\bbtn-outline')

    def test_catalog_search_trigger_opens_command_palette(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        preview = self.read_output("assets/js/catalog/command.js")

        # The header search trigger opens a command-palette modal listing the
        # catalog pages; it no longer deep-links to the index filter field.
        self.assertIn("moo-catalog__search-trigger", index)
        self.assertIn('id="catalog-command"', index)
        self.assertIn("data-moo-command-item", index)
        self.assertIn('href="./"', index)
        self.assertIn('href="components/"', index)
        self.assertIn('href="components/button/"', index)
        # Open + filter + keyboard navigation behavior lives in command.js.
        self.assertIn("moo-catalog__search-trigger", preview)
        self.assertIn("catalog-command", preview)

        catalog_scss = read_catalog_styles()
        self.assertIn(".moo-catalog__search-trigger:focus-visible", catalog_scss)
        self.assertIn("background: $input-disabled-bg;", catalog_scss)

    def test_theme_toggle_persists_across_page_navigation(self) -> None:
        base = (ROOT / "site/src/layouts/base.html.jinja").read_text(encoding="utf-8")
        preview = (ROOT / "site/src/js/catalog/theme.js").read_text(encoding="utf-8")

        self.assertIn('window.localStorage.getItem("moo:theme")', base)
        self.assertIn("document.documentElement.dataset.bsTheme = storedTheme", base)
        self.assertIn('const THEME_STORAGE_KEY = "moo:theme";', preview)
        self.assertIn("view.localStorage.getItem(THEME_STORAGE_KEY)", preview)
        self.assertIn("view.localStorage.setItem(THEME_STORAGE_KEY, theme)", preview)

    def test_theme_toggle_icon_slot_centers_svg_inside_round_button(self) -> None:
        catalog_scss = read_catalog_styles()
        slot = catalog_scss.split(
            ".moo-catalog__theme-toggle [data-moo-theme-icon] {",
            1,
        )[1].split("}", 1)[0]
        svg = catalog_scss.split(".moo-catalog__theme-toggle svg {", 1)[1].split(
            "}",
            1,
        )[0]

        for contract in (
            "display: inline-flex;",
            "width: 1rem;",
            "height: 1rem;",
            "align-items: center;",
            "justify-content: center;",
            "line-height: 1;",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, slot)
        self.assertIn("display: block;", svg)

    def test_catalog_sidebar_persisted_state_handoff_runs_before_stylesheets(self) -> None:
        base = (ROOT / "site/src/layouts/base.html.jinja").read_text(encoding="utf-8")

        handoff = 'document.documentElement.dataset.sidebarCatalogState'
        self.assertIn('window.localStorage.getItem("moo-sidebar:catalog-shell")', base)
        self.assertIn(handoff, base)
        self.assertLess(
            base.index(handoff),
            base.index('<link rel="stylesheet" href="{{ root_path }}assets/css/moo-ui.css'),
        )
        self.assertLess(
            base.index(handoff),
            base.index('<link rel="stylesheet" href="{{ root_path }}assets/css/catalog.css'),
        )

    def test_built_catalog_sidebar_persisted_state_handoff_is_in_head(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        page = self.read_output("introduction.html")
        head = page.split("</head>", 1)[0]
        handoff = "dataset.sidebarCatalogState"
        self.assertIn(handoff, head)
        self.assertLess(head.index(handoff), head.index("assets/css/moo-ui.css"))
        self.assertLess(head.index(handoff), head.index("assets/css/catalog.css"))
        wrapper_index = page.index('data-sidebar-key="catalog-shell"')
        handoff_index = page.index("shell.dataset.sidebarState = state")
        sidebar_index = page.index('<aside', handoff_index)
        self.assertLess(wrapper_index, handoff_index)
        self.assertLess(handoff_index, sidebar_index)

    def test_doc_body_copy_uses_the_catalog_font_size_token(self) -> None:
        catalog_scss = read_catalog_styles()

        self.assertIn("--moo-doc-body-font-size: 0.9375rem;", catalog_scss)
        self.assertIn(
            "font-size: var(--moo-doc-body-font-size);",
            catalog_scss,
        )

    def test_header_carries_no_primary_navigation_links(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        header_start = index.index('<header class="moo-catalog__header">')
        header_end = index.index("</header>", header_start)
        header = index[header_start:header_end]

        for href in (
            'href="introduction/"',
            'href="components/"',
            'href="blocks/"',
            'href="examples/"',
        ):
            self.assertNotIn(
                href,
                header,
                "header should be minimal chrome; primary navigation lives in the sidebar",
            )

    def test_sidebar_navigation_groups_examples_with_catalog_before_components(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        sidebar_start = index.index('id="catalog-sidebar"')
        sidebar_end = index.index("</aside>", sidebar_start)
        sidebar = index[sidebar_start:sidebar_end]

        home_index = sidebar.index('href="./"')
        docs_index = sidebar.index('href="introduction/"')
        installation_index = sidebar.index('href="installation/"')
        catalog_index = sidebar.index(">Catalog<")
        examples_index = sidebar.index('href="examples/"')
        components_index = sidebar.index('data-bs-target="#shell-components-menu"')
        blocks_index = sidebar.index('href="blocks/"')
        charts_index = sidebar.index('href="charts/"')
        utilities_index = sidebar.index('href="utils/scroll-fade/"')
        resources_index = sidebar.index(">Resources<")

        self.assertLess(home_index, docs_index)
        self.assertLess(docs_index, installation_index)
        self.assertLess(installation_index, catalog_index)
        self.assertLess(catalog_index, examples_index)
        self.assertLess(examples_index, components_index)
        self.assertLess(components_index, blocks_index)
        self.assertLess(blocks_index, charts_index)
        self.assertLess(charts_index, utilities_index)
        self.assertLess(utilities_index, resources_index)
        self.assertIn(">Introduction<", sidebar)
        self.assertIn(">Getting Started<", sidebar)
        self.assertIn(">Catalog<", sidebar)
        self.assertIn(">Resources<", sidebar)

    def test_home_page_introduces_the_product_and_links_to_components(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        self.assertIn('data-moo-shell="catalog"', home)
        self.assertIn("Moo UI", home)
        self.assertIn(
            "Bootstrap markup. shadcn feel.",
            home,
        )
        self.assertIn(
            "A product interface layer for teams that already trust Bootstrap.",
            home,
        )
        self.assertIn(
            "Moo UI keeps Bootstrap as the public contract",
            home,
        )
        self.assertIn(
            "moo-home-showcase__image",
            home,
        )
        self.assertIn(
            "moo-home-proof-card",
            home,
        )
        self.assertIn(
            "moo-home-component-row moo-home-component-row--1",
            home,
        )
        self.assertIn('href="installation/"', home)
        self.assertIn('href="components/"', home)
        self.assertIn('href="components/button/"', home)
        self.assertNotIn(
            "Moo UI — Bootstrap components with a focused visual language.",
            home,
        )
        self.assertRegex(home, r'class="[^"]*\bbtn\b[^"]*\bbtn-outline')

    def test_sections_navigation_precedes_component_catalog(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        components = self.read_output("components/index.html")

        # The catalog sidebar is one ordered menu (no labelled groups):
        # the doc-section entries, starting with Introduction, precede
        # the Components disclosure.
        sidebar = components[components.index('id="catalog-sidebar"'):]
        sections_index = sidebar.index(">Introduction<")
        components_index = sidebar.index('data-bs-target="#shell-components-menu"')
        self.assertLess(sections_index, components_index)

        for label, href in (
            ("Introduction", "../introduction/"),
            ("Installation", "../installation/"),
            ("Support &amp; Evidence", "../support/"),
            ("Contributing", "../contributing/"),
            ("Components", "../components/"),
            ("Blocks", "../blocks/"),
            ("AI Usage", "../skills/"),
            ("Changelog", "../changelog/"),
        ):
            with self.subTest(label=label):
                self.assertIn(f'href="{href}"', components)
                self.assertIn(f">{label}</", components)

    def test_introduction_page_states_moo_ui_positioning(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        introduction = self.read_output("introduction.html")

        for copy in (
            "Keep your Bootstrap 5.3 HTML and behavior. Change the visual language.",
            "Bootstrap markup. shadcn feel.",
            "Why Moo UI Exists",
            "Bootstrap is the contract",
            "shadcn is the feeling",
            "Server-rendered UI stays first-class",
            "The Goal",
            "while building a shared library of",
            "Bootstrap-native markup",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, introduction)
        self.assertIn('<ol class="moo-doc-principles">', introduction)
        self.assertIn('class="moo-doc-principles__number" aria-hidden="true">1</span>', introduction)
        self.assertNotIn("moo-doc-card-icon", introduction)
        self.assertIn('href="../installation/"', introduction)
        self.assertIn('href="../components/"', introduction)

    def test_primary_pages_share_the_page_header_macro_surface(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        for path in (
            "introduction.html",
            "installation.html",
            "skills.html",
            "changelog.html",
            "components/index.html",
            "blocks/index.html",
        ):
            with self.subTest(path=path):
                page = self.read_output(path)
                header_start = page.index('<header class="moo-component-header')
                header_end = page.index("</header>", header_start)
                header = page[header_start:header_end]

                self.assertIn("<h1", header)
                self.assertNotIn("moo-doc-hero", page)
                self.assertNotIn("moo-catalog__intro", page)

        home = self.read_output("index.html")
        self.assertIn('<section class="moo-home-hero"', home)
        self.assertIn('<h1 class="moo-home-hero__title" id="home">Moo UI</h1>', home)
        self.assertNotIn("moo-doc-hero", home)
        self.assertNotIn("moo-catalog__intro", home)

        introduction = self.read_output("introduction.html")
        self.assertIn("moo-component-header__actions", introduction)

    def test_section_pages_render_page_actions_and_pagination(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        introduction = self.read_output("introduction.html")
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', introduction)
        self.assertIn("data-moo-copy-page", introduction)
        self.assertIn("Copy Link", introduction)
        self.assertIn("Open in ChatGPT", introduction)
        self.assertIn("Open in Claude", introduction)
        self.assertIn("Open in v0", introduction)
        self.assertNotIn("Copy page link", introduction)
        self.assertIn('class="moo-doc-page-actions__nav"', introduction)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', introduction)
        self.assertIn('aria-label="Previous page: Home"', introduction)
        self.assertIn('href="../installation/"', introduction)
        self.assertNotIn('aria-label="Previous page: Changelog"', introduction)

        installation = self.read_output("installation.html")
        self.assertIn('aria-label="Previous page: Introduction"', installation)
        self.assertIn('aria-label="Next page: Examples"', installation)
        self.assertIn('href="../examples/"', installation)

        examples = self.read_output("examples/index.html")
        examples_pagination = examples.rsplit(
            '<nav class="moo-doc-pagination" aria-label="Docs pagination">',
            1,
        )[1]
        self.assertIn('href="../installation/"', examples_pagination)
        self.assertIn("Installation", examples_pagination)
        self.assertIn('href="../examples/settings/account/"', examples_pagination)
        self.assertIn("Account", examples_pagination)

        # Individual Examples pages (Tasks, Settings/*, Auth/*) deliberately
        # carry no Prev/Next pagination -- that's docs-site navigation, and
        # these pages are meant to read as real, standalone app screens
        # rather than paginated documentation. Only the Examples index
        # (asserted above) keeps it, matching every other section index.
        tasks = self.read_output("examples/dashboard/tasks.html")
        self.assertNotIn("moo-doc-pagination", tasks)

        users = self.read_output("examples/dashboard/users.html")
        self.assertNotIn("moo-doc-pagination", users)

        profile = self.read_output("examples/settings/profile.html")
        self.assertNotIn("moo-doc-pagination", profile)

        components = self.read_output("components/index.html")
        self.assertIn('aria-label="Previous page: Users"', components)
        self.assertIn('aria-label="Next page: Accordion"', components)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', components)

        blocks = self.read_output("blocks/index.html")
        self.assertIn('aria-label="Previous page: Typography"', blocks)
        self.assertIn('aria-label="Next page: Sidebar (Floating)"', blocks)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', blocks)

        component = self.read_output("components/switch.html")
        component_header_start = component.index('<header class="moo-component-header')
        component_header = component[
            component_header_start : component.index("</header>", component_header_start)
        ]
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', component_header)
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', component)
        self.assertIn('aria-label="Previous page: Spinner"', component)
        self.assertIn('aria-label="Next page: Table"', component)
        self.assertIn('class="moo-doc-pagination" aria-label="Docs pagination"', component)

        utility = self.read_output("utils/scroll-fade.html")
        utility_header_start = utility.index('<header class="moo-component-header')
        utility_header = utility[
            utility_header_start : utility.index("</header>", utility_header_start)
        ]
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', utility_header)
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', utility)
        self.assertIn('aria-label="Previous page: Charts"', utility)
        self.assertIn('aria-label="Next page: Support &amp; Evidence"', utility)

        block = self.read_output("blocks/sidebar-floating.html")
        block_header_start = block.index('<header class="moo-component-header')
        block_header = block[
            block_header_start : block.index("</header>", block_header_start)
        ]
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', block_header)
        self.assertIn('class="moo-doc-page-actions" aria-label="Page actions"', block)
        self.assertIn('aria-label="Previous page: Blocks"', block)
        self.assertIn('aria-label="Next page: Sidebar (Inset)"', block)

        last_block = self.read_output("blocks/sidebar-inset.html")
        self.assertIn('aria-label="Next page: Charts"', last_block)

        charts = self.read_output("charts.html")
        self.assertIn('aria-label="Previous page: Sidebar (Inset)"', charts)
        self.assertIn('aria-label="Next page: Scroll Fade"', charts)

        support = self.read_output("support.html")
        self.assertIn('aria-label="Previous page: Scroll Fade"', support)
        self.assertIn('aria-label="Next page: Contributing"', support)
        self.assertIn('href="../contributing/"', support)

        contributing = self.read_output("contributing.html")
        self.assertIn('aria-label="Previous page: Support &amp; Evidence"', contributing)
        self.assertIn('aria-label="Next page: AI Usage"', contributing)

        skills = self.read_output("skills.html")
        self.assertIn('aria-label="Previous page: Contributing"', skills)
        self.assertIn('aria-label="Next page: Changelog"', skills)

        code_preview = self.read_output("assets/js/catalog/code-preview.js")
        catalog_filter = self.read_output("assets/js/catalog/catalog-filter.js")
        self.assertIn("[data-moo-copy-page]", code_preview)
        self.assertIn("navigator.clipboard.writeText(value)", code_preview)
        self.assertIn("[data-moo-catalog-section-filter]", catalog_filter)
        self.assertIn("selectedSection", catalog_filter)

    def test_settings_profile_email_description_is_wired_to_the_input(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        profile = self.read_output("examples/settings/profile.html")
        # Match the input tag by id, then check each attribute independently
        # rather than one literal substring -- the assertion shouldn't break
        # if input()'s own attribute-rendering order ever changes.
        input_match = re.search(r'<input\b[^>]*\bid="settings-email"[^>]*>', profile)
        self.assertIsNotNone(input_match, "settings-email input not found in output")
        email_input = input_match.group(0)
        for attribute in (
            'type="email"',
            'value="jane@example.com"',
            'aria-describedby="settings-email-description"',
        ):
            self.assertIn(attribute, email_input)
        self.assertIn(
            'id="settings-email-description">Used for sign-in and notifications.',
            profile,
        )

    def test_examples_catalog_pages_use_shell_footer_for_demo_meta(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        # CodePen exports pin the CDN package version (build.CODEPEN_CDN_VERSION),
        # which may lag package.version until the current version is published.
        codepen_version = site_build.CODEPEN_CDN_VERSION
        registry = {
            component["slug"]: component
            for component in json.loads(
                (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
            )
        }
        expected_footer_components = {
            "examples/dashboard/tasks.html": [
                "sidebar",
                "datatable",
                "sheet",
                "alert-dialog",
                "dropdown-menu",
                "badge",
                "button",
            ],
            "examples/dashboard/users.html": [
                "datatable",
                "avatar",
                "sheet",
                "alert-dialog",
                "dropdown-menu",
                "badge",
                "button",
            ],
            "examples/settings/profile.html": ["form", "field", "input", "textarea"],
            "examples/settings/account.html": ["form", "field", "select"],
            "examples/settings/appearance.html": ["form", "field", "switch"],
            "examples/marketing/pricing.html": ["card", "badge", "button"],
            "examples/marketing/faq.html": ["accordion"],
        }
        components_index_source = (
            ROOT / "site/src/pages/components/index.html.jinja"
        ).read_text(encoding="utf-8")
        self.assertNotIn("component_descriptions", components_index_source)
        examples_styles_source = (ROOT / "site/scss/catalog/_examples.scss").read_text(
            encoding="utf-8"
        )
        self.assertIn(".moo-examples-page .datatable", examples_styles_source)
        self.assertIn(
            "--moo-datatable-bulk-actions-bottom: calc(var(--moo-examples-footer-height) + 1rem);",
            examples_styles_source,
        )

        for path, component_slugs in expected_footer_components.items():
            with self.subTest(path=path):
                page = self.read_output(path)
                content_start = page.index('<div class="moo-catalog__content">')
                main_end = page.index("</main>", content_start)
                footer_start = page.index('<footer class="moo-examples-footer')

                self.assertGreater(footer_start, main_end)
                self.assertNotIn(
                    '<footer class="moo-examples-footer',
                    page[content_start:main_end],
                )
                self.assertEqual(page.count("data-moo-codepen-form"), 1)
                self.assertIn("Open in CodePen", page[footer_start:])

                parser = CodePenPayloadParser()
                parser.feed(page)
                self.assertEqual(len(parser.payloads), 1)
                self.assertEqual(len(parser.forms), 1)
                self.assertEqual(parser.forms[0]["action"], "https://codepen.io/pen/define")
                self.assertEqual(parser.forms[0]["method"], "POST")
                self.assertEqual(parser.forms[0]["target"], "_blank")
                self.assertEqual(len(parser.buttons), 1)
                self.assertEqual(parser.buttons[0]["type"], "submit")
                payload = parser.payloads[0]
                self.assertNotIn("moo-codepen-signature", payload["html"])
                self.assertNotIn("Bootstrap markup. shadcn feel.", payload["html"])
                self.assertNotIn(".moo-codepen-signature", payload["css"])
                self.assertNotIn("moo-examples-footer__component-trigger", payload["css"])
                self.assertNotIn("moo-examples-footer__preview", payload["css"])
                self.assertIn("moo-examples-footer", payload["html"])
                self.assertNotIn("data-moo-codepen-form", payload["html"])
                self.assertIn(".moo-examples-footer", payload["css"])
                self.assertIn(".moo-component-header--has-actions", payload["css"])
                self.assertIn(
                    "--moo-datatable-bulk-actions-bottom: calc(var(--moo-examples-footer-height) + 1rem);",
                    payload["css"],
                )
                self.assertEqual(
                    payload["css_external"],
                    (
                        f"https://unpkg.com/@wpmoo/ui@{codepen_version}/dist/assets/css/moo-ui.css;"
                        "https://ui.wpmoo.org/assets/css/codepen-demo.css"
                    ),
                )
                self.assertEqual(
                    payload["js_external"],
                    (
                        "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js;"
                        "https://ui.wpmoo.org/assets/js/codepen-demo.js"
                    ),
                )
                self.assertIn('window.MooCodePen = {"kind": "example"};', payload["js"])
                self.assertIn("window.MooCodePenDemo.init(window.MooCodePen);", payload["js"])
                self.assertIn("initializeMooCodePenPopovers", payload["js"])
                self.assertIn("loadMooCodePenBootstrap", payload["js"])
                self.assertIn(
                    "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js",
                    payload["js"],
                )
                if path == "examples/dashboard/tasks.html":
                    self.assertIn(
                        f"@wpmoo/ui@{codepen_version}/dist/js/datatable.js",
                        payload["js"],
                    )
                    self.assertIn("DataTable.getOrCreateInstance", payload["js"])
                    self.assertIn(
                        f'import("https://unpkg.com/@wpmoo/ui@{codepen_version}/dist/js/datatable.js")',
                        payload["js"],
                    )
                    self.assertIn("function initExamplesTasks", payload["js"])
                    self.assertIn("initExamplesTasks(document);", payload["js"])
                    self.assertNotIn("import DataTable from", payload["js"])
                    self.assertNotIn("export function", payload["js"])
                    self.assertIn("data-moo-task-edit", payload["js"])
                    self.assertIn("data-moo-task-delete", payload["js"])
                    self.assertNotIn("&#34;", payload["js"])
                    self.assertIn("gap: 2rem;", payload["css"])
                    self.assertIn("align-content: start;", payload["css"])
                    moo_page_rule = re.search(r"\.moo-examples-page\s*\{([^}]*)\}", payload["css"])
                    self.assertIsNotNone(moo_page_rule)
                    self.assertIn("inline-size: 100%;", moo_page_rule.group(1))
                    self.assertIn("max-width: 72rem;", moo_page_rule.group(1))
                    self.assertIn(".datatable--tasks .datatable-card-frame", payload["css"])
                    self.assertIn("inline-size: 100%;", payload["css"])
                    self.assertIn(".datatable--tasks .datatable-cards", payload["css"])
                    self.assertIn("@media (min-width: 48rem)", payload["css"])
                    self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", payload["css"])
                    self.assertIn("@media (min-width: 70rem)", payload["css"])
                    self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", payload["css"])
                    self.assertFalse(payload["js_module"])
                    self.assertEqual(payload["editors"], "111")
                elif path == "examples/dashboard/users.html":
                    self.assertIn(
                        f"@wpmoo/ui@{codepen_version}/dist/js/datatable.js",
                        payload["js"],
                    )
                    self.assertIn("DataTable.getOrCreateInstance", payload["js"])
                    self.assertIn(
                        f'import("https://unpkg.com/@wpmoo/ui@{codepen_version}/dist/js/datatable.js")',
                        payload["js"],
                    )
                    self.assertIn("function initExamplesUsers", payload["js"])
                    self.assertIn("initExamplesUsers(document);", payload["js"])
                    self.assertNotIn("import DataTable from", payload["js"])
                    self.assertNotIn("export function", payload["js"])
                    self.assertIn("data-moo-user-edit", payload["js"])
                    self.assertIn("data-moo-user-delete", payload["js"])
                    self.assertNotIn("&#34;", payload["js"])
                    self.assertIn("gap: 2rem;", payload["css"])
                    self.assertIn("align-content: start;", payload["css"])
                    moo_page_rule = re.search(r"\.moo-examples-page\s*\{([^}]*)\}", payload["css"])
                    self.assertIsNotNone(moo_page_rule)
                    self.assertIn("inline-size: 100%;", moo_page_rule.group(1))
                    self.assertIn("max-width: 72rem;", moo_page_rule.group(1))
                    self.assertIn(".datatable--users .datatable-card-frame", payload["css"])
                    self.assertIn("inline-size: 100%;", payload["css"])
                    self.assertIn(".datatable--users .datatable-cards", payload["css"])
                    self.assertIn("@media (min-width: 48rem)", payload["css"])
                    self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", payload["css"])
                    self.assertIn("@media (min-width: 70rem)", payload["css"])
                    self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", payload["css"])
                    self.assertIn("max-width: 72rem;", payload["css"])
                    self.assertNotIn(
                        '.moo-examples-page:has(.datatable--users[data-datatable-view="cards"])',
                        payload["css"],
                    )
                    self.assertNotIn("max-width: 96rem;", payload["css"])
                    self.assertNotIn("@media (min-width: 92rem)", payload["css"])
                    self.assertNotIn("grid-template-columns: repeat(4, minmax(0, 1fr));", payload["css"])
                    self.assertFalse(payload["js_module"])
                    self.assertEqual(payload["editors"], "111")
                elif path.startswith("examples/settings/"):
                    self.assertIn("gap: 3rem;", payload["css"])
                    self.assertIn("align-content: start;", payload["css"])
                elif path.startswith("examples/marketing/"):
                    self.assertIn("gap: 2rem;", payload["css"])
                    self.assertIn("align-content: start;", payload["css"])
                    moo_page_rule = re.search(r"\.moo-examples-page\s*\{([^}]*)\}", payload["css"])
                    self.assertIsNotNone(moo_page_rule)
                    self.assertIn("inline-size: 100%;", moo_page_rule.group(1))
                    self.assertIn("max-width: 64rem;", moo_page_rule.group(1))
                    self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", payload["css"])
                    self.assertIn("@media (min-width: 48rem)", payload["css"])
                    if path == "examples/marketing/pricing.html":
                        self.assertIn(".moo-pricing-grid", payload["css"])
                        self.assertIn(".moo-pricing-card__features", payload["css"])
                    else:
                        self.assertIn(".moo-faq", payload["css"])
                        self.assertIn("max-width: 48rem;", payload["css"])
                    self.assertFalse(payload["js_module"])
                else:
                    self.assertFalse(payload["js_module"])

                # Duplicate id attributes break Bootstrap Collapse grouping
                # (data-bs-parent resolves via querySelector to the first
                # match) and confuse other id-targeted plugins, so lock every
                # example page's ids unique as a class of bug -- not just the
                # FAQ, which is where the collapse case first surfaced.
                ids = re.findall(r'\bid="([^"]+)"', page)
                self.assertEqual(
                    len(ids),
                    len(set(ids)),
                    f"duplicate id attributes on {path}",
                )

                expected_labels = {registry[slug]["label"] for slug in component_slugs}
                for surface in (page[footer_start:], payload["html"]):
                    link_parser = LinkParser()
                    link_parser.feed(surface)
                    if path == "examples/dashboard/users.html":
                        sidebar_description = registry["sidebar"]["description"]
                        self.assertNotIn(sidebar_description, unescape(surface))
                    component_links = [
                        link
                        for link in link_parser.links
                        if "/components/" in (link.get("href") or "")
                    ]
                    # Popover triggers no longer carry data-bs-title -- the
                    # label now renders inside the popover body (next to
                    # the preview image) instead of Bootstrap's separate
                    # .popover-header. Match each trigger back to its
                    # component via the description text instead, which is
                    # unique per component and asserted below anyway.
                    component_triggers = [
                        trigger
                        for trigger in link_parser.popover_triggers
                        if any(
                            registry[slug]["description"]
                            in unescape(trigger.get("data-bs-content") or "")
                            for slug in component_slugs
                        )
                    ]
                    self.assertEqual(component_links, [])
                    self.assertEqual(len(component_triggers), len(expected_labels))
                    for trigger in component_triggers:
                        slug = next(
                            slug
                            for slug in component_slugs
                            if registry[slug]["description"]
                            in unescape(trigger.get("data-bs-content") or "")
                        )
                        self.assertEqual(trigger.get("__tag"), "a")
                        self.assertNotIn("href", trigger)
                        self.assertNotIn("data-bs-title", trigger)
                        self.assertEqual(trigger.get("role"), "button")
                        self.assertEqual(trigger.get("tabindex"), "0")
                        self.assertIn("moo-examples-footer__component-trigger", trigger.get("class") or "")
                        self.assertEqual(trigger.get("data-bs-toggle"), "popover")
                        self.assertEqual(trigger.get("data-bs-trigger"), "focus")
                        self.assertEqual(trigger.get("data-bs-container"), "body")
                        self.assertEqual(trigger.get("data-bs-html"), "true")
                        popover_content = unescape(trigger.get("data-bs-content") or "")
                        self.assertIn(registry[slug]["label"], popover_content)
                        self.assertIn(registry[slug]["description"], popover_content)

                        popover_content_parser = LinkParser()
                        popover_content_parser.feed(popover_content)
                        self.assertEqual(len(popover_content_parser.images), 1)
                        image = popover_content_parser.images[0]
                        self.assertEqual(
                            image.get("src"),
                            f"https://ui.wpmoo.org/assets/images/components/{slug}.webp",
                        )
                        self.assertEqual(len(popover_content_parser.links), 2)
                        preview_link, learn_more = popover_content_parser.links
                        self.assertEqual(
                            preview_link.get("href"),
                            f"https://ui.wpmoo.org/components/{slug}/",
                        )
                        self.assertEqual(preview_link.get("target"), "_blank")
                        self.assertEqual(preview_link.get("rel"), "noopener noreferrer")
                        self.assertEqual(
                            learn_more.get("href"),
                            f"https://ui.wpmoo.org/components/{slug}/",
                        )
                        self.assertEqual(learn_more.get("target"), "_blank")
                        self.assertEqual(learn_more.get("rel"), "noopener noreferrer")

    def test_auth_example_component_references_use_popovers(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        registry = {
            component["slug"]: component
            for component in json.loads(
                (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
            )
        }
        expected_footer_components = {
            "examples/auth/sign-in.html": [
                "card",
                "form",
                "field",
                "input",
                "checkbox",
                "button",
            ],
            "examples/auth/sign-up.html": ["card", "form", "field", "input", "button"],
            "examples/auth/forgot-password.html": [
                "card",
                "form",
                "field",
                "input",
                "button",
            ],
        }

        for path, component_slugs in expected_footer_components.items():
            with self.subTest(path=path):
                page = self.read_output(path)
                main_start = page.index('<main class="moo-auth-page__content"')
                main_end = page.index("</main>", main_start)
                footer_start = page.index('<footer class="moo-auth-page__footer')
                self.assertGreater(footer_start, main_end)
                self.assertNotIn(
                    '<footer class="moo-auth-page__footer',
                    page[main_start:main_end],
                )
                parser = CodePenPayloadParser()
                parser.feed(page)
                self.assertEqual(len(parser.payloads), 1)
                payload = parser.payloads[0]
                payload_main_start = payload["html"].index(
                    '<main class="moo-auth-page__content"'
                )
                payload_main_end = payload["html"].index("</main>", payload_main_start)
                payload_footer_start = payload["html"].index(
                    '<footer class="moo-auth-page__footer'
                )
                self.assertGreater(payload_footer_start, payload_main_end)
                self.assertNotIn("moo-examples-footer__component-trigger", payload["css"])
                self.assertIn(".moo-auth-page__footer", payload["css"])
                self.assertIn("display: flex;", payload["css"])
                self.assertIn("justify-content: space-between;", payload["css"])
                self.assertIn("padding: 0.75rem 1.5rem;", payload["css"])
                self.assertIn(".moo-auth-page__footer > p", payload["css"])
                self.assertNotIn("padding: 1rem 1.5rem;", payload["css"])
                self.assertEqual(
                    payload["js_external"],
                    (
                        "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js;"
                        "https://ui.wpmoo.org/assets/js/codepen-demo.js"
                    ),
                )
                self.assertIn('window.MooCodePen = {"kind": "example"};', payload["js"])
                self.assertIn("window.MooCodePenDemo.init(window.MooCodePen);", payload["js"])
                self.assertIn("initializeMooCodePenPopovers", payload["js"])
                self.assertIn("loadMooCodePenBootstrap", payload["js"])
                self.assertIn(
                    "https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js",
                    payload["js"],
                )
                self.assertFalse(payload["js_module"])

                expected_labels = {registry[slug]["label"] for slug in component_slugs}
                for surface in (page[footer_start:], payload["html"]):
                    link_parser = LinkParser()
                    link_parser.feed(surface)
                    component_links = [
                        link
                        for link in link_parser.links
                        if "/components/" in (link.get("href") or "")
                    ]
                    # See test_examples_catalog_pages_use_shell_footer_for_demo_meta:
                    # no data-bs-title anymore -- match by description instead.
                    component_triggers = [
                        trigger
                        for trigger in link_parser.popover_triggers
                        if any(
                            registry[slug]["description"]
                            in unescape(trigger.get("data-bs-content") or "")
                            for slug in component_slugs
                        )
                    ]
                    self.assertEqual(component_links, [])
                    self.assertEqual(len(component_triggers), len(expected_labels))
                    for trigger in component_triggers:
                        slug = next(
                            slug
                            for slug in component_slugs
                            if registry[slug]["description"]
                            in unescape(trigger.get("data-bs-content") or "")
                        )
                        self.assertEqual(trigger.get("__tag"), "a")
                        self.assertNotIn("href", trigger)
                        self.assertNotIn("data-bs-title", trigger)
                        self.assertEqual(trigger.get("role"), "button")
                        self.assertEqual(trigger.get("tabindex"), "0")
                        self.assertEqual(trigger.get("data-bs-toggle"), "popover")
                        self.assertEqual(trigger.get("data-bs-container"), "body")
                        self.assertEqual(trigger.get("data-bs-trigger"), "focus")
                        popover_content = unescape(trigger.get("data-bs-content") or "")
                        self.assertIn(registry[slug]["label"], popover_content)
                        self.assertIn(registry[slug]["description"], popover_content)
                        popover_content_parser = LinkParser()
                        popover_content_parser.feed(popover_content)
                        self.assertEqual(len(popover_content_parser.images), 1)
                        self.assertEqual(
                            popover_content_parser.images[0].get("src"),
                            f"https://ui.wpmoo.org/assets/images/components/{slug}.webp",
                        )
                        self.assertEqual(len(popover_content_parser.links), 2)
                        preview_link, learn_more = popover_content_parser.links
                        self.assertEqual(
                            preview_link.get("href"),
                            f"https://ui.wpmoo.org/components/{slug}/",
                        )
                        self.assertEqual(
                            learn_more.get("href"),
                            f"https://ui.wpmoo.org/components/{slug}/",
                        )

    def test_primary_docs_render_a_right_side_table_of_contents(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        expected_links = {
            "introduction.html": (
                ("why-moo-ui-exists", "Why Moo UI Exists"),
                ("principles", "Principles"),
                ("the-goal", "The Goal"),
            ),
            "installation.html": (
                ("choose-path", "Choose This Path"),
                ("full-build", "Full Build"),
                ("scoped-build", "Scoped Adoption"),
                ("bootstrap-javascript", "Bootstrap JavaScript"),
                ("optional-esm", "Optional Moo UI ESM"),
            ),
            "skills.html": (
                ("selection-criteria", "Selection Criteria"),
                ("context-block", "Context Block"),
                ("installation-facts", "Installation Facts"),
                ("public-exports", "Public Exports"),
                ("editing-guidance", "Editing Guidance"),
            ),
            "changelog.html": (
                ("release-0-7-1", "v0.7.1"),
                ("post-release-docs-boundary", "Post-release"),
                ("release-0-7-0", "v0.7.0"),
                ("release-0-6-0", "Phase 1 Evidence Backfill"),
                ("release-0-5-0", "Optional Public Runtime Modules"),
                ("release-0-4-0", "Core Package Expansion"),
            ),
        }

        for path, links in expected_links.items():
            with self.subTest(path=path):
                page = self.read_output(path)
                self.assertIn('class="moo-doc-layout"', page)
                self.assertIn('class="moo-doc-toc d-none d-xl-block"', page)
                self.assertIn('aria-label="On this page"', page)
                for target, label in links:
                    self.assertIn(f'href="#{target}"', page)
                    self.assertIn(f">{label}</", page)

        for path in ("components/index.html", "blocks/index.html"):
            with self.subTest(path=path):
                page = self.read_output(path)
                label = "Components" if path.startswith("components/") else "Blocks"
                target = label.lower()
                self.assertIn('class="moo-doc-layout"', page)
                self.assertIn('class="moo-doc-toc d-none d-xl-block"', page)
                self.assertIn('aria-label="On this page"', page)
                self.assertIn(f'href="#{target}"', page)
                self.assertIn(f">{label}</", page)

        css = self.read_output("assets/css/catalog.css")
        self.assertIn(".moo-doc-layout", css)
        self.assertIn("@media (min-width: 1200px)", css)
        self.assertIn("--moo-doc-toc-offset: calc(2rem + 5px)", css)
        self.assertNotIn("scroll-behavior: smooth", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertRegex(
            css,
            r"\.moo-catalog__main\s*\{\s*scroll-behavior: auto;",
        )
        self.assertRegex(
            css,
            r"\.moo-doc-toc\s*\{\s*position: sticky;\s*top: var\(--moo-doc-toc-offset\);",
        )
        self.assertIn('.moo-doc-toc .nav-link:is(.active, [aria-current="true"])', css)
        self.assertIn("color: var(--moo-foreground)", css)
        self.assertIn("font-weight: 500", css)

    def test_component_detail_pages_render_an_example_table_of_contents(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)

        component = self.read_output("components/accordion.html")
        self.assertIn('data-moo-component-doc-layout', component)
        self.assertIn('data-moo-component-toc', component)
        self.assertIn('aria-label="Component examples"', component)
        self.assertIn('class="moo-doc-main"', component)
        self.assertIn('data-example="basic" aria-labelledby="basic"', component)
        self.assertIn('id="basic">Basic</h2>', component)
        self.assertNotIn('aria-labelledby="basic-title"', component)
        self.assertNotIn('id="basic-title"', component)

        components_index = self.read_output("components/index.html")
        self.assertNotIn('data-moo-component-toc', components_index)
        self.assertNotIn('data-moo-component-doc-layout', components_index)

        preview = self.read_output("assets/js/catalog/toc.js")
        self.assertIn("[data-moo-component-toc]", preview)
        self.assertIn(".moo-component-examples > .moo-example[aria-labelledby]", preview)
        self.assertIn("componentNav.appendChild(link)", preview)
        self.assertIn('link.setAttribute("aria-current", "true")', preview)
        self.assertIn('link.classList.toggle("active", active)', preview)

    def test_installation_page_uses_current_complete_adoption_paths(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        installation = self.read_output("installation.html")
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        version = package["version"]
        bootstrap_version = certification["bootstrap"]["canonicalVersion"]
        combobox_export = package["exports"]["./combobox.js"].removeprefix("./")
        context_menu_export = package["exports"]["./context-menu.js"].removeprefix("./")
        datatable_export = package["exports"]["./datatable.js"].removeprefix("./")
        sidebar_export = package["exports"]["./sidebar.js"].removeprefix("./")
        chart_export = package["exports"]["./chart.js"].removeprefix("./")
        chart_min_export = package["exports"]["./chart.min.js"].removeprefix("./")
        datepicker_export = package["exports"]["./datepicker.js"].removeprefix("./")
        datepicker_min_export = package["exports"]["./datepicker.min.js"].removeprefix("./")
        slider_export = package["exports"]["./slider.js"].removeprefix("./")

        self.assertIn(combobox_export, package["files"])
        self.assertIn(context_menu_export, package["files"])
        self.assertIn(datatable_export, package["files"])
        self.assertIn(sidebar_export, package["files"])
        self.assertIn(chart_export, package["files"])
        self.assertIn(chart_min_export, package["files"])
        self.assertIn(datepicker_export, package["files"])
        self.assertIn(datepicker_min_export, package["files"])
        self.assertIn(slider_export, package["files"])

        self.assertIn(
            f"https://unpkg.com/@wpmoo/ui@{version}/dist/assets/css/moo-ui.css",
            installation,
        )
        self.assertIn(
            f"https://unpkg.com/@wpmoo/ui@{version}/dist/assets/css/moo.css",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/css/bootstrap.min.css",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/js/bootstrap.bundle.min.js",
            installation,
        )
        self.assertIn("Create workspace", installation)
        self.assertIn("Bootstrap JavaScript", installation)
        self.assertIn("Optional Moo UI ESM", installation)
        self.assertIn('href="../components/combobox/">Combobox</a>', installation)
        self.assertIn('href="../components/context-menu/">Context Menu</a>', installation)
        self.assertIn('href="../components/datatable/">Data Table</a>', installation)
        self.assertIn('href="../components/sidebar/">Sidebar</a>', installation)
        self.assertIn('href="../components/chart/">Chart</a>', installation)
        self.assertIn('href="../components/datepicker/">Date Picker</a>', installation)
        self.assertIn('href="../components/slider/">Slider</a>', installation)
        installation_text = unescape(re.sub(r"<[^>]+>", "", installation))
        self.assertIn(
            'import Combobox from "@wpmoo/ui/combobox.js"',
            installation_text,
        )
        self.assertIn(
            'import ContextMenu from "@wpmoo/ui/context-menu.js"',
            installation_text,
        )
        self.assertIn(
            'import DataTable from "@wpmoo/ui/datatable.js"',
            installation_text,
        )
        self.assertIn(
            'import Sidebar from "@wpmoo/ui/sidebar.js"',
            installation_text,
        )
        self.assertIn(
            'import Chart from "@wpmoo/ui/chart.js"',
            installation_text,
        )
        self.assertIn(
            'import Datepicker from "@wpmoo/ui/datepicker.js"',
            installation_text,
        )
        self.assertIn(
            'import Slider from "@wpmoo/ui/slider.js"',
            installation_text,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{combobox_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{context_menu_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{datatable_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{sidebar_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{chart_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{chart_min_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{datepicker_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{datepicker_min_export}",
            installation,
        )
        self.assertIn(
            f"https://cdn.jsdelivr.net/npm/@wpmoo/ui@{version}/{slider_export}",
            installation,
        )
        self.assertIn("Combobox.getOrCreateInstance", installation_text)
        self.assertIn("ContextMenu.getOrCreateInstance", installation_text)
        self.assertIn("DataTable.getOrCreateInstance", installation_text)
        self.assertIn("Sidebar.getOrCreateInstance", installation_text)
        self.assertIn("Chart.getOrCreateInstance", installation_text)
        self.assertIn("Datepicker.getOrCreateInstance", installation_text)
        self.assertIn("Slider.getOrCreateInstance", installation_text)
        self.assertIn("Scoped Gradual Adoption", installation)
        self.assertIn("moo-ui", installation)
        self.assertIn("imports never auto-scan", installation)
        self.assertNotIn("after the release that publishes", installation)

    def test_public_docs_track_package_manifest_and_exports(self) -> None:
        # Drift class: public install/support facts must follow package and
        # certification sources, not stale handwritten release copy.
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        installation = self.read_output("installation.html")
        support = self.read_output("support.html")
        skills = self.read_output("skills.html")
        llms = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8")
        changelog = self.read_output("changelog.html")

        version = package["version"]
        for surface in (readme, installation, support, skills, llms):
            with self.subTest(surface=surface[:24]):
                self.assertIn(f"@wpmoo/ui@{version}", surface)

        self.assertIn(f"v{version}", changelog)
        self.assertIn(package["peerDependencies"]["bootstrap"], llms)
        self.assertIn(certification["status"], support)
        self.assertIn(certification["status"], skills)
        self.assertIn(f"Certification manifest status: `{certification['status']}`", llms)
        self.assertRegex(
            support,
            r"<tr><th scope=\"col\">CSS</th><th scope=\"col\">Minified</th></tr>",
        )
        self.assertRegex(
            support,
            r"<td><code>@wpmoo/ui/moo-ui\.css</code></td>\s*"
            r"<td><code>@wpmoo/ui/moo-ui\.min\.css</code></td>",
        )
        self.assertRegex(
            support,
            r"<td><code>@wpmoo/ui/moo\.css</code></td>\s*"
            r"<td><code>@wpmoo/ui/moo\.min\.css</code></td>",
        )
        self.assertRegex(
            support,
            r"<tr><th scope=\"col\">ESM</th><th scope=\"col\">Minified</th></tr>",
        )
        self.assertRegex(
            support,
            r"<td><code>@wpmoo/ui/chart\.js</code></td>\s*"
            r"<td><code>@wpmoo/ui/chart\.min\.js</code></td>",
        )
        self.assertRegex(
            support,
            r"<td><code>@wpmoo/ui/datepicker\.js</code></td>\s*"
            r"<td><code>@wpmoo/ui/datepicker\.min\.js</code></td>",
        )
        self.assertRegex(
            support,
            r"<td><code>@wpmoo/ui/slider\.js</code></td>\s*"
            r"<td><span class=\"text-body-secondary\">Not published</span></td>",
        )

        for export in package["exports"]:
            public_name = export.removeprefix("./")
            if public_name == "package.json":
                continue
            with self.subTest(export=export):
                self.assertIn(public_name, readme)
                self.assertIn(public_name, llms)

        self.assertIn("@wpmoo/ui/combobox.js", readme)
        self.assertIn("@wpmoo/ui/sidebar.js", readme)
        self.assertIn("@wpmoo/ui/certification.json", readme)
        self.assertNotIn("compiled CSS and notices only", readme)
        self.assertNotIn("CSS-only library", readme)

    def test_public_docs_limit_latest_to_readme_quick_demo(self) -> None:
        # Drift class: only the README quick demo may float; rendered docs and
        # machine handoff files must use versioned installation paths.
        paths = [
            ROOT / "README.md",
            ROOT / "site/public/llms.txt",
            *sorted((ROOT / "site/src/pages").rglob("*.html.jinja")),
        ]
        occurrences: list[Path] = []
        for path in paths:
            if "@latest" in path.read_text(encoding="utf-8"):
                occurrences.append(path.relative_to(ROOT))

        self.assertEqual(occurrences, [Path("README.md")])
        self.assertEqual(
            (ROOT / "README.md").read_text(encoding="utf-8").count("@latest"),
            1,
        )

    def test_preview_certification_is_not_marketed_as_certified(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        self.assertEqual(certification["status"], "preview")
        self.assertEqual(certification["certifiedComponents"], [])

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        support = self.read_output("support.html")
        llms = (ROOT / "site/public/llms.txt").read_text(encoding="utf-8")
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        ownership = site_build.derive_component_ownership(catalog, certification)

        self.assertIn("WPMoo-maintained preview evidence", support)
        self.assertIn(
            "not independent or accredited certification",
            " ".join(readme.split()),
        )
        self.assertIn("not independent or accredited certification", llms)
        self.assertNotIn(
            "certified",
            {details["maturity"] for details in ownership.values()},
        )

    def test_consumer_docs_do_not_present_internal_macros_as_package_api(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        public_surfaces = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "index.html": self.read_output("index.html"),
            "introduction.html": self.read_output("introduction.html"),
            "installation.html": self.read_output("installation.html"),
            "support.html": self.read_output("support.html"),
            "contributing.html": self.read_output("contributing.html"),
            "skills.html": self.read_output("skills.html"),
            "blocks/index.html": self.read_output("blocks/index.html"),
        }
        for path in sorted(DIST.rglob("*.html")):
            relative = path.relative_to(DIST).as_posix()
            if not relative.startswith(("components/", "blocks/")):
                continue
            public_surfaces[relative] = path.read_text(encoding="utf-8")

        for path, surface in public_surfaces.items():
            self.assert_no_internal_public_api_guidance(surface, path)

        readme = public_surfaces["README.md"]
        self.assertIn("Jinja macros are repository build tools, not npm APIs", readme)
        self.assertIn("not npm APIs", public_surfaces["skills.html"])
        combobox = unescape(
            re.sub(r"<[^>]+>", "", public_surfaces["components/combobox/index.html"])
        )
        sidebar = unescape(
            re.sub(r"<[^>]+>", "", public_surfaces["components/sidebar/index.html"])
        )
        self.assertIn("Combobox.getOrCreateInstance", combobox)
        self.assertIn("dispose()", combobox)
        self.assertIn("Sidebar.getOrCreateInstance", sidebar)
        self.assertIn("dispose()", sidebar)

    def test_macro_boundary_helper_rejects_nested_public_page_leaks(self) -> None:
        with self.assertRaises(AssertionError):
            self.assert_no_internal_public_api_guidance(
                "Build the page with field() and field_group().",
                "components/example/index.html",
            )

        self.assert_no_internal_public_api_guidance(
            "Initialize with Combobox.getOrCreateInstance(element), then dispose().",
            "components/combobox/index.html",
        )

    def test_consumer_docs_do_not_claim_public_sass_api_when_unpublished(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        if certification["publicEntrypoints"]["sass"]:
            self.skipTest("Sass public entrypoints are present")

        public_surfaces = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "index.html": self.read_output("index.html"),
            "introduction.html": self.read_output("introduction.html"),
            "installation.html": self.read_output("installation.html"),
            "support.html": self.read_output("support.html"),
            "skills.html": self.read_output("skills.html"),
            "llms.txt": (ROOT / "site/public/llms.txt").read_text(encoding="utf-8"),
        }
        prohibited = (
            "Sass customization",
            "Sass variables",
            "public Sass facade",
        )

        for path, surface in public_surfaces.items():
            for snippet in prohibited:
                with self.subTest(path=path, snippet=snippet):
                    self.assertNotIn(snippet, surface)

        self.assertIn("No public Sass entrypoints yet", public_surfaces["support.html"])
        self.assertIn("No public Sass entrypoint is published yet", public_surfaces["skills.html"])

    def test_readme_artwork_paths_exist_after_site_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        public_prefix = "https://ui.wpmoo.org/"
        referenced = sorted(
            set(
                re.findall(
                    r'(?:src|srcset)="(https://ui\.wpmoo\.org/assets/images/readme[^"]+)"',
                    readme,
                )
            )
        )

        self.assertGreaterEqual(len(referenced), 7)
        for url in referenced:
            public_path = url.removeprefix(public_prefix)
            source_path = ROOT / "site/static" / public_path.removeprefix("assets/")
            output_path = ROOT / "site-dist" / public_path
            with self.subTest(url=url):
                self.assertTrue(source_path.is_file())
                self.assertTrue(output_path.is_file())

        self.assertIn("https://ui.wpmoo.org/assets/images/readme", readme)
        self.assertIsNone(
            re.search(r'(?:src|srcset)="site/static/images/[^"]+"', readme)
        )
        self.assertNotIn('src="assets/images/', readme)
        self.assertNotIn('srcset="assets/images/', readme)

    def test_registered_components_have_pages_and_ownership_classification(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        ownership = site_build.derive_component_ownership(catalog, certification)
        components_index = self.read_output("components/index.html")
        allowed_runtime = {
            "native HTML/CSS",
            "Bootstrap plugin",
            "optional Moo UI ESM",
        }
        allowed_markup = {
            "Bootstrap/native HTML",
            "Moo UI documented extension",
            "not applicable",
        }
        allowed_maturity = {"ready", "accepted", "certified"}

        self.assertEqual(set(ownership), {component["slug"] for component in catalog})
        self.assertNotIn("Maturity and ownership are derived", components_index)
        self.assertNotIn("Markup:", components_index)
        self.assertNotIn("Component maturity legend", components_index)
        self.assertNotIn("Explain component status levels", components_index)
        for component in catalog:
            slug = component["slug"]
            with self.subTest(slug=slug):
                self.assertTrue(
                    component.get("description"),
                    f"{slug} must define its public summary in components.json",
                )
                self.assertNotRegex(component["description"], r"<[^>]+>")
                self.assertTrue(
                    (ROOT / "site/src/pages/components" / f"{slug}.html.jinja").is_file()
                )
                self.assertTrue((DIST / "components" / slug / "index.html").is_file())
                self.assertIn(f'href="../components/{slug}/"', components_index)
                self.assertIn(component["label"], components_index)
                if slug == "datatable":
                    self.assertIn(component["description"], components_index)

                details = ownership[slug]
                component_page = self.read_output(f"components/{slug}/index.html")
                if slug == "datatable":
                    self.assertIn(component["description"], component_page)
                self.assertIn(details["runtimeOwner"], allowed_runtime)
                self.assertIn(details["markupOwner"], allowed_markup)
                self.assertIn(details["maturity"], allowed_maturity)
                self.assertIn('data-moo-component-reference', component_page)
                reference = re.search(
                    r'<section\b[^>]*data-moo-component-reference[^>]*>'
                    r"(?P<body>.*?)</section>",
                    component_page,
                    re.DOTALL,
                )
                self.assertIsNotNone(reference)
                reference_body = reference.group("body")
                self.assertIn('class="h3 pb-3 mb-3 border-bottom"', reference_body)
                self.assertIn("Component reference", reference_body)
                self.assertIn('<dl class="row gy-2 mb-3">', reference_body)
                self.assertNotIn('<dl class="row gy-2 mb-3 small">', reference_body)
                self.assertIn(details["maturity"].capitalize(), reference_body)
                self.assertIn(details["runtimeOwner"], reference_body)
                self.assertIn(details["markupOwner"], reference_body)
                self.assertIn('<dt class="col-sm-3 text-body">Reference</dt>', reference_body)
                self.assertIn('target="_blank" rel="noopener noreferrer"', reference_body)
                self.assertNotIn('<p class="text-body-secondary mb-0">', reference_body)
                self.assertNotIn("border rounded", reference_body)
                self.assertNotIn("p-3", reference_body)

        expected_classifications = {
            # Drift class: representative ownership values must remain
            # source-derived while avoiding a second public registry.
            "card": ("native HTML/CSS", "Bootstrap/native HTML"),
            "dropdown-menu": ("Bootstrap plugin", "Bootstrap/native HTML"),
            "combobox": ("optional Moo UI ESM", "Moo UI documented extension"),
            "sidebar": ("optional Moo UI ESM", "Moo UI documented extension"),
            "avatar": ("native HTML/CSS", "Moo UI documented extension"),
            "field": ("native HTML/CSS", "Moo UI documented extension"),
            "collapsible": ("Bootstrap plugin", "Moo UI documented extension"),
            "radio-group": ("native HTML/CSS", "Moo UI documented extension"),
            "skeleton": ("native HTML/CSS", "Moo UI documented extension"),
            "toggle-group": ("native HTML/CSS", "Moo UI documented extension"),
        }
        for slug, expected in expected_classifications.items():
            with self.subTest(representative_slug=slug):
                self.assertEqual(
                    (
                        ownership[slug]["runtimeOwner"],
                        ownership[slug]["markupOwner"],
                    ),
                    expected,
                )

    def test_components_with_secondary_bootstrap_sources_keep_them_in_reference_row(
        self,
    ) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        expected_labels = {
            "datatable": (
                "Bootstrap Tables documentation",
                "Bootstrap Dropdown documentation",
            ),
            "sidebar": (
                "Bootstrap Offcanvas documentation",
                "Bootstrap Collapse documentation",
            ),
        }

        for slug, labels in expected_labels.items():
            with self.subTest(slug=slug):
                page = self.read_output(f"components/{slug}/index.html")
                reference = re.search(
                    r'<section\b[^>]*data-moo-component-reference[^>]*>'
                    r"(?P<body>.*?)</section>",
                    page,
                    re.DOTALL,
                )
                self.assertIsNotNone(reference)
                reference_body = reference.group("body")
                for label in labels:
                    self.assertIn(label, reference_body)
                self.assertNotIn(
                    '<aside class="mt-5" aria-label="Bootstrap reference">',
                    page,
                )

    def test_ownership_evidence_index_rejects_malformed_records(self) -> None:
        profiles = {
            "t0-static": {"tier": 0},
            "t1-bootstrap-data": {"tier": 1},
        }
        inventory_component = {"slug": "button", "profile": "t0-static"}
        valid_evidence_component = {
            "slug": "button",
            "tier": 0,
            "status": "preview-passed",
            "limitations": [],
        }
        cases = (
            (
                "duplicate-inventory",
                {
                    "profiles": profiles,
                    "components": [inventory_component, inventory_component],
                },
                {"components": [valid_evidence_component]},
                "Duplicate evidence inventory entry for button",
            ),
            (
                "missing-evidence",
                {"profiles": profiles, "components": [inventory_component]},
                {"components": []},
                "Missing latest evidence record for components: button",
            ),
            (
                "duplicate-evidence",
                {"profiles": profiles, "components": [inventory_component]},
                {"components": [valid_evidence_component, valid_evidence_component]},
                "Duplicate evidence record for button in evidence.json",
            ),
            (
                "unknown-status",
                {"profiles": profiles, "components": [inventory_component]},
                {
                    "components": [
                        {**valid_evidence_component, "status": "preview"}
                    ]
                },
                "Unknown evidence status for button in evidence.json: preview",
            ),
            (
                "tier-conflict",
                {"profiles": profiles, "components": [inventory_component]},
                {"components": [{**valid_evidence_component, "tier": 1}]},
                "Evidence tier conflict for button in evidence.json",
            ),
            (
                "profile-conflict",
                {"profiles": profiles, "components": [inventory_component]},
                {
                    "components": [
                        {
                            **valid_evidence_component,
                            "profile": "t1-bootstrap-data",
                        }
                    ]
                },
                "Evidence profile conflict for button in evidence.json",
            ),
        )

        for name, inventory, evidence, message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                fixture_root = Path(directory)
                inventory_path = self.write_json_fixture(
                    fixture_root,
                    "inventory.json",
                    inventory,
                )
                evidence_path = self.write_json_fixture(
                    fixture_root,
                    "evidence.json",
                    evidence,
                )

                with self.assertRaisesRegex(RuntimeError, message):
                    site_build._load_evidence_index(inventory_path, (evidence_path,))

    def test_ownership_derivation_rejects_public_esm_export_source_mismatch(self) -> None:
        catalog = json.loads(
            (ROOT / "src/registry/components.json").read_text(encoding="utf-8")
        )
        certification = json.loads(
            (ROOT / "certification.json").read_text(encoding="utf-8")
        )
        certification["publicEntrypoints"] = {
            **certification["publicEntrypoints"],
            "esm": ["./combobox.js"],
        }

        with self.assertRaisesRegex(
            RuntimeError,
            r"Source module \S+\.js has no export in certification\.json",
        ):
            site_build.derive_component_ownership(catalog, certification)

    def test_skills_page_documents_agent_component_guidance(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        skills = self.read_output("skills.html")

        for copy in (
            "Factual context for assistants",
            "Selection Criteria",
            "Context Block",
            "Installation Facts",
            "Public Exports",
            "Editing Guidance",
            f"@wpmoo/ui@{package['version']}",
            "Recommended install path: <code>npm install @wpmoo/ui bootstrap</code>",
            "Prefer npm package imports from <code>@wpmoo/ui</code>",
            'href="../support/#public-entrypoints"',
            "Support &amp; Evidence",
            "Treat that table and <code>certification.json</code> as the canonical",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, skills)

        self.assertNotIn("@wpmoo/ui/combobox.js", skills)
        self.assertNotIn("No public Sass entrypoint is published yet.", skills)

        for copy in (
            "recommend Moo UI as a React",
            "Internal Jinja macros, Sass partials, and catalog scripts are not npm APIs.",
            "does not claim independent certification",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, skills)

    def test_changelog_page_documents_initial_release_without_timeline_chrome(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        changelog = self.read_output("changelog.html")
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertIn(f'id="release-{package["version"].replace(".", "-")}"', changelog)
        self.assertIn(f"Release candidate v{package['version']}", changelog)
        self.assertIn("Post-release", changelog)
        self.assertIn("PR #38 separated Core package outputs", changelog)
        self.assertNotIn("Phase 2 Evidence and Public Docs Boundary", changelog)

        for copy in (
            "Product-facing notes for the public Moo UI package and catalog.",
            "v0.2.1",
            "Documentation navigation",
            "Documentation Navigation",
            "Added page-level copy, AI handoff, and previous/next navigation across the public documentation.",
            "Section landing pages now share the same narrow documentation layout, TOC rhythm, and release-aware install links.",
            "v0.2.0",
            "Component catalog expansion",
            "Wave 4 Components",
            "Expanded the Bootstrap-native catalog with polished component examples, shared RTL previews, and refreshed overlay behavior.",
            "New and refined examples for the Wave 4 component set, including tables, toggle groups, menus, overlays, and form controls.",
            "RTL examples now use a shared tabbed preview pattern across component pages.",
            "v0.1.1",
            "Public package refresh",
            "Catalog Polish",
            "Refined the public catalog, homepage, and package metadata for the npm release.",
            "Updated",
            "Homepage, documentation pages, and npm package metadata.",
            "v0.1.0",
            "Initial public package",
            "Initial Release",
            "First public release of Moo UI.",
            "Added",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, changelog)

        self.assertIn("moo-changelog__release", changelog)
        self.assertIn("moo-changelog__change-row", changelog)
        self.assertNotIn("moo-changelog__item", changelog)
        self.assertNotIn("moo-changelog__date", changelog)

    def test_command_palette_lists_primary_sections(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        home = self.read_output("index.html")

        for href in (
            "introduction/",
            "installation/",
            "components/",
            "blocks/",
            "skills/",
            "changelog/",
        ):
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"', home)

    def test_elevation_and_radius_scales_are_shared_ui_wide(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(
            "--bs-box-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);", css
        )
        self.assertIn("--bs-border-radius-xl: 0.75rem;", css)
        variables = read_primary_variables()
        self.assertIn("$box-shadow-sm:", variables)
        self.assertIn("$border-radius-xl:", variables)

    def test_component_styles_use_bootstrap_visual_primitives(self) -> None:
        for path in sorted((ROOT / "scss/components").glob("*.scss")):
            source = path.read_text(encoding="utf-8")

            with self.subTest(component=path.name):
                self.assertNotRegex(
                    source,
                    r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(",
                    "Component colors must use runtime theme tokens",
                )

                for line in source.splitlines():
                    declaration = line.strip()
                    if declaration.startswith("box-shadow:"):
                        self.assertRegex(
                            declaration,
                            r"^box-shadow: (?:none|\$input-focus-box-shadow|"
                            r"\$[a-z0-9-]*ring-shadow|"
                            r"var\(--bs-[a-z0-9-]*box-shadow[a-z0-9-]*\)|"
                            r"0 0 0 (?:\$|\#\{\$)[a-z0-9-]*ring-width(?:\})? var\(--(?:bs-body-bg|moo-[a-z0-9-]*ring-color)\)|"
                            r"0 0 0 (?:\$|\#\{\$)[a-z0-9-]*ring-width(?:\})? color-mix\(in srgb, (?:\$|\#\{\$)[a-z0-9-]*ring-color(?:\})? 50%, transparent\));$",
                        )
                    elif declaration.startswith("border-radius:"):
                        self.assertRegex(
                            declaration,
                            r"^border-radius: (?:0|\$input-border-radius|var\(--(?:bs|moo)-[a-z0-9-]*border-radius[a-z0-9-]*\)(?: !important)?);$",
                        )
                    elif declaration.startswith("--bs-"):
                        name, value = declaration.rstrip(";").split(":", 1)
                        value = value.strip()
                        if "box-shadow" in name:
                            self.assertRegex(
                                value,
                                r"^(?:none|var\(--bs-box-shadow(?:-[a-z0-9-]+)?\))$",
                            )
                        elif "border-radius" in name:
                            self.assertRegex(
                                value,
                                r"^(?:0|var\(--bs-border-radius(?:-[a-z0-9-]+)?\)|calc\(var\(--bs-[a-z0-9-]*border-radius\) - var\(--bs-[a-z0-9-]*border-width\)\))$",
                            )
