from __future__ import annotations

import re

from tests.helpers import DIST, ROOT, CatalogTestCase, read_settings
from tests.helpers.css_contract import (
    assert_allowed_global_rules,
    assert_animation_closure,
    assert_owner_scoped_token_bridges,
    assert_safe_assets,
    assert_single_moo_scope,
)
from tests.test_design_gates import active_component_imports


CORE_CSS = DIST / "assets/css/moo.css"
FULL_CSS = DIST / "assets/css/moo-ui.css"
SCSS = ROOT / "scss"
COMPONENTS_SCSS = SCSS / "components"
OVERLAY_BACKDROP_SCSS = SCSS / "foundations/_backdrop.scss"
UTILITIES_SCSS = SCSS / "utilities"

REQUIRED_BOOTSTRAP_IMPORTS = [
    "tables",
    "forms/labels",
    "forms/form-text",
    "forms/form-control",
    "forms/form-select",
    "forms/form-check",
    "forms/input-group",
    "forms/validation",
    "buttons",
    "dropdown",
    "button-group",
    "nav",
    "card",
    "accordion",
    "breadcrumb",
    "pagination",
    "badge",
    "alert",
    "close",
    "toasts",
    "modal",
    "tooltip",
    "popover",
    "offcanvas",
    "helpers/color-bg",
]
FORBIDDEN_BOOTSTRAP_IMPORTS = {
    "forms",
    "progress",
    "placeholders",
    "transitions",
    "root",
    "reboot",
    "type",
    "helpers",
    "utilities/api",
}
FORBIDDEN_TOPOLOGY_FRAGMENTS = (
    ".btn-check:checked + .moo-ui",
    ".dropup .moo-ui",
    ".moo-ui [data-bs-theme=",
    ".moo-ui [dir=",
    ".moo-ui:valid",
    ".moo-ui:invalid",
    ".moo-ui.is-valid",
    ".moo-ui.is-invalid",
)
REQUIRED_TOPOLOGY_FRAGMENTS = (
    ".btn-check:checked + .btn",
    ".btn-group > .btn-check:checked + .btn",
    ".dropup .dropdown-toggle::after",
    ".is-invalid ~ .invalid-feedback",
    ".moo-ui[data-bs-theme]",
    '.moo-ui[data-bs-theme="light"]',
    '.moo-ui[data-bs-theme="dark"]',
    '.moo-ui[data-bs-theme][dir="rtl"]',
)


def active_scss_imports(source: str) -> list[str]:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    active_source = "\n".join(
        line.split("//", 1)[0] for line in source.splitlines()
    )
    return re.findall(
        r'^\s*@import\s+["\']([^"\']+)["\']\s*;',
        active_source,
        re.MULTILINE,
    )


class MooCoreTests(CatalogTestCase):
    def _build_and_read_core(self) -> str:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            CORE_CSS.is_file(),
            "build.py must emit dist/assets/css/moo.css",
        )
        return CORE_CSS.read_text(encoding="utf-8")

    def test_build_emits_moo_css(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(CORE_CSS.is_file())

    def test_core_css_uses_one_native_moo_scope(self) -> None:
        assert_single_moo_scope(self, self._build_and_read_core())

    def test_core_css_allows_only_explicit_global_rules(self) -> None:
        assert_allowed_global_rules(self, self._build_and_read_core())

    def test_artifacts_use_resolved_owners_instead_of_document_theme_bridges(self) -> None:
        core_css = self._build_and_read_core()
        full_css = self.read_output("assets/css/moo-ui.css")

        assert_owner_scoped_token_bridges(self, core_css, scoped=True)
        assert_owner_scoped_token_bridges(self, full_css, scoped=False)

        state_layer = (SCSS / "themes/_forms.scss").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(":where(html, body)", state_layer)
        self.assertNotIn("body[data-bs-theme]", state_layer)
        self.assertIn(':scope[data-bs-theme="light"]', state_layer)
        self.assertIn(':scope[data-bs-theme="dark"]', state_layer)

    def test_core_css_closes_animation_references(self) -> None:
        assert_animation_closure(self, self._build_and_read_core())

    def test_core_css_contains_only_safe_assets(self) -> None:
        assert_safe_assets(self, self._build_and_read_core())

    def test_core_selector_topology_preserves_bootstrap_relationships(self) -> None:
        css = self._build_and_read_core()

        for fragment in FORBIDDEN_TOPOLOGY_FRAGMENTS:
            self.assertNotIn(fragment, css)
        for fragment in REQUIRED_TOPOLOGY_FRAGMENTS:
            self.assertIn(fragment, css)

    def test_components_aggregate_keeps_bootstrap_and_moo_layers_explicit(self) -> None:
        layer = SCSS / "_components.scss"

        self.assertTrue(layer.is_file(), "missing Moo components aggregate")
        source = layer.read_text(encoding="utf-8")
        imports = active_scss_imports(source)
        bootstrap_imports = [
            item.removeprefix("../vendor/bootstrap/scss/")
            .removeprefix("bootstrap/scss/")
            for item in imports
            if not item.startswith("components/")
            and not item.startswith("foundations/")
            and not item.startswith("utilities/")
        ]
        self.assertEqual(bootstrap_imports, REQUIRED_BOOTSTRAP_IMPORTS)
        self.assertEqual(len(bootstrap_imports), len(set(bootstrap_imports)))
        self.assertFalse(FORBIDDEN_BOOTSTRAP_IMPORTS.intersection(bootstrap_imports))
        self.assertNotIn("@import \"bootstrap_component_layer\";", source)
        self.assertNotIn("@import \"component_layer\";", source)
        self.assertNotIn('@import "foundations/focus";', source)
        self.assertNotIn('@import "utilities/scroll_fade";', source)
        self.assertNotIn('@import "layouts/app";', source)

        scope = (SCSS / "foundations/_scope.scss").read_text(encoding="utf-8")
        self.assertIn('@import "../foundations/focus";', scope)
        self.assertIn('@import "../utilities/scroll_fade";', scope)
        self.assertIn('@import "../layouts/app";', scope)

    def test_components_aggregate_imports_every_moo_partial_once(self) -> None:
        layer = SCSS / "_components.scss"

        self.assertTrue(layer.is_file(), "missing Moo components aggregate")
        source = layer.read_text(encoding="utf-8")
        imported_components = active_component_imports(source)
        expected_components = {
            path.stem.removeprefix("_")
            for path in COMPONENTS_SCSS.glob("_*.scss")
        }
        self.assertEqual(imported_components, expected_components)
        self.assertEqual(
            source.count('@import "utilities/scroll_fade"'),
            0,
            "Scroll Fade selector partial must not be owned by the components aggregate",
        )

    def test_search_trigger_is_a_shared_core_composition(self) -> None:
        layer = SCSS / "_components.scss"
        source = layer.read_text(encoding="utf-8")

        self.assertIn('@import "components/search_trigger";', source)
        self.assertEqual(
            source.count('@import "components/search_trigger";'),
            1,
        )

        core_css = self._build_and_read_core()
        full_css = self.read_output("assets/css/moo-ui.css")
        for css in (core_css, full_css):
            with self.subTest(output="core" if css is core_css else "full"):
                self.assertIn(".search-trigger", css)
                self.assertIn(".search-trigger__label", css)
                self.assertIn(".search-trigger__shortcut", css)
                self.assertIn("height: 2rem;", css)
                self.assertIn("width: 10rem;", css)
                self.assertIn(
                    "background: color-mix(in srgb, var(--bs-secondary-bg) 55%, var(--bs-body-bg));",
                    css,
                )
                self.assertIn(
                    "border: var(--bs-border-width) solid transparent;",
                    css,
                )

    def test_moo_component_and_utility_scss_do_not_reference_assets(self) -> None:
        offenders: list[str] = []
        for directory in (COMPONENTS_SCSS, UTILITIES_SCSS):
            for path in sorted(directory.glob("_*.scss")):
                source = path.read_text(encoding="utf-8")
                # Inline SVG data URIs (e.g. Lucide icon overrides) are
                # intentional component-level replacements, not asset refs.
                if "url(" in source.lower():
                    non_svg_urls = [
                        line for line in source.splitlines()
                        if "url(" in line.lower() and not line.strip().startswith("//")
                        and "data:image/svg+xml" not in line.lower()
                    ]
                    if non_svg_urls:
                        offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_overlay_backdrop_uses_bootstrap_native_modal_and_offcanvas_tokens(self) -> None:
        overlay_layer = OVERLAY_BACKDROP_SCSS.read_text(encoding="utf-8")
        settings = read_settings()
        tokens_root = (SCSS / "themes/_root.scss").read_text(
            encoding="utf-8"
        )
        core_theme = (SCSS / "themes/_theme.scss").read_text(
            encoding="utf-8"
        )

        for knob in (
            "$moo-overlay-motion-duration: .3s !default;",
            "$moo-overlay-backdrop-opacity: 1 !default;",
            "$moo-overlay-backdrop-bg: color-mix(in srgb, #0a0a0a 10%, transparent) !default;",
            "$moo-overlay-backdrop-filter: blur(6px) !default;",
        ):
            self.assertIn(knob, settings)

        for token in (
            "--moo-overlay-motion-duration: #{$moo-overlay-motion-duration}",
            "--moo-overlay-backdrop-opacity: #{$moo-overlay-backdrop-opacity}",
            "--moo-overlay-backdrop-bg: #{$moo-overlay-backdrop-bg}",
            "--moo-overlay-backdrop-filter: #{$moo-overlay-backdrop-filter}",
        ):
            self.assertIn(token, core_theme)

        self.assertIn("@include moo-core-shared;", tokens_root)

        self.assertIn(".modal-backdrop", overlay_layer)
        self.assertIn(".offcanvas-backdrop", overlay_layer)
        self.assertIn("@mixin moo-overlay-backdrop-appearance", overlay_layer)
        self.assertIn("--#{$prefix}backdrop-opacity: var(", overlay_layer)
        self.assertIn("--moo-overlay-backdrop-opacity", overlay_layer)
        self.assertIn("color: transparent;", overlay_layer)
        self.assertIn("background-color: transparent;", overlay_layer)
        self.assertIn("--moo-overlay-backdrop-bg", overlay_layer)
        self.assertIn("&::before", overlay_layer)
        self.assertIn("-webkit-backdrop-filter: blur(0);", overlay_layer)
        self.assertIn("backdrop-filter: blur(0);", overlay_layer)
        self.assertIn("--moo-overlay-backdrop-filter", overlay_layer)
        self.assertIn(".modal-backdrop.show", overlay_layer)
        self.assertIn(".offcanvas-backdrop.show", overlay_layer)
        self.assertIn("transition: none;", overlay_layer)
        self.assertIn(
            "transition: color var(--moo-overlay-motion-duration",
            overlay_layer,
        )
        self.assertIn("animation: moo-overlay-backdrop-enter var(", overlay_layer)
        self.assertIn("animation: moo-overlay-backdrop-exit var(", overlay_layer)
        self.assertIn("@keyframes moo-overlay-backdrop-enter", overlay_layer)
        self.assertIn("@keyframes moo-overlay-backdrop-exit", overlay_layer)
        self.assertIn("opacity: var(--moo-overlay-backdrop-opacity", overlay_layer)
        self.assertIn("@mixin moo-overlay-backdrop-reduced-motion", overlay_layer)
        self.assertNotIn("body:has(.modal.show)", overlay_layer)
        self.assertNotIn("offcanvas.sheet.show", overlay_layer)

        state_layer = (SCSS / "themes/_forms.scss").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(".modal-backdrop", state_layer)
        self.assertNotIn(".offcanvas-backdrop", state_layer)
        self.assertNotIn("backdrop-filter", state_layer)

        core_css = self._build_and_read_core()
        self.assertIn(".modal-backdrop", core_css)
        self.assertIn(".offcanvas-backdrop", core_css)
        self.assertIn("--moo-overlay-motion-duration: 0.3s", core_css)
        self.assertIn("--moo-overlay-backdrop-filter: blur(6px)", core_css)
        self.assertIn(
            "--bs-backdrop-opacity: var(--moo-overlay-backdrop-opacity, 1)",
            core_css,
        )
        self.assertIn(
            "background-color: transparent;",
            core_css,
        )
        self.assertNotIn(
            "background-color: var(--moo-overlay-backdrop-bg, color-mix(in srgb, var(--bs-black)",
            core_css,
        )
        self.assertIn(
            "backdrop-filter: var(--moo-overlay-backdrop-filter, blur(6px))",
            core_css,
        )
        self.assertIn(".modal-backdrop::before", core_css)
        self.assertIn(".offcanvas-backdrop::before", core_css)
        self.assertIn(".modal-backdrop.show", core_css)
        self.assertIn(".offcanvas-backdrop.show", core_css)
        self.assertIn(
            ".modal-backdrop.show,\n.offcanvas-backdrop.show {\n  transition: none;",
            core_css,
        )
        self.assertIn(
            "transition: color var(--moo-overlay-motion-duration, 0.3s) ease-out",
            core_css,
        )
        self.assertIn(
            "animation: moo-overlay-backdrop-enter var(--moo-overlay-motion-duration, 0.3s) ease-out both;",
            core_css,
        )
        self.assertIn("@keyframes moo-overlay-backdrop-enter", core_css)
        self.assertIn("@keyframes moo-overlay-backdrop-exit", core_css)
        self.assertIn(
            "opacity: var(--moo-overlay-backdrop-opacity, 1)",
            core_css,
        )
        self.assertNotIn("body:has(.moo-ui .modal.show) > .modal-backdrop", core_css)
        self.assertNotIn("body:has(.modal.show) > .modal-backdrop", core_css)
        self.assertNotIn("offcanvas.sheet:is(.showing, .show)", core_css)
        self.assertNotIn("offcanvas.sheet.hiding", core_css)

    def test_root_theme_tokens_follow_resolved_owner_scope(self) -> None:
        tokens_root = (SCSS / "themes/_root.scss").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("body[data-bs-theme]", tokens_root)
        self.assertNotIn(":root", tokens_root)
        self.assertIn(".moo-ui[data-bs-theme] {", tokens_root)
        owner_tokens = tokens_root.split(".moo-ui[data-bs-theme] {", 1)[1].split(
            "}",
            1,
        )[0]
        self.assertIn("@include moo-core-scales;", owner_tokens)
        self.assertIn("@include moo-core-shared;", owner_tokens)

    def test_scope_layer_owns_component_and_form_imports(self) -> None:
        scope_layer = (SCSS / "foundations/_scope.scss").read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            active_scss_imports(scope_layer),
            [
                "../components",
                "../foundations/focus",
                "../utilities/scroll_fade",
                "../layouts/app",
                "../themes/forms",
            ],
        )
        self.assertIn("@scope (.moo-ui)", scope_layer)
        self.assertIn("@include moo-overlay-backdrop-scoped;", scope_layer)

    def test_standalone_layer_only_owns_standalone_minimum_size(self) -> None:
        standalone = (SCSS / "themes/_standalone.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn("body > .moo-ui[data-bs-theme] {", standalone)
        self.assertIn("min-block-size: 100dvh;", standalone)
        self.assertNotIn("@include", standalone)
