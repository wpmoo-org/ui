from __future__ import annotations

import re

from tests.helpers import DIST, ROOT, CatalogTestCase
from tests.helpers.css_contract import (
    assert_allowed_global_rules,
    assert_animation_closure,
    assert_safe_assets,
    assert_single_moo_scope,
)
from tests.test_design_gates import active_component_imports


CORE_CSS = DIST / "assets/css/moo-core.css"
SCSS = ROOT / "scss"
COMPONENTS_SCSS = SCSS / "components"
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
    ':where(html, body)[data-bs-theme="dark"] .moo-ui:not([data-bs-theme])',
    '.moo-ui[data-bs-theme="light"]',
    '.moo-ui[data-bs-theme="dark"]',
    '.moo-ui[dir="rtl"]',
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
            "build.py must emit dist/assets/css/moo-core.css",
        )
        return CORE_CSS.read_text(encoding="utf-8")

    def test_build_emits_moo_core_css(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(CORE_CSS.is_file())

    def test_core_css_uses_one_native_moo_scope(self) -> None:
        assert_single_moo_scope(self, self._build_and_read_core())

    def test_core_css_allows_only_explicit_global_rules(self) -> None:
        assert_allowed_global_rules(self, self._build_and_read_core())

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

    def test_bootstrap_component_layer_is_ordered_and_explicit(self) -> None:
        layer = SCSS / "_bootstrap_component_layer.scss"

        self.assertTrue(layer.is_file(), "missing Bootstrap component layer")
        imports = active_scss_imports(layer.read_text(encoding="utf-8"))
        normalized = [
            item.removeprefix("../vendor/bootstrap/scss/")
            .removeprefix("bootstrap/scss/")
            for item in imports
        ]
        self.assertEqual(normalized, REQUIRED_BOOTSTRAP_IMPORTS)
        self.assertEqual(len(normalized), len(set(normalized)))
        self.assertFalse(FORBIDDEN_BOOTSTRAP_IMPORTS.intersection(normalized))

    def test_component_layer_imports_every_moo_partial_once(self) -> None:
        layer = SCSS / "_component_layer.scss"

        self.assertTrue(layer.is_file(), "missing Moo component layer")
        source = layer.read_text(encoding="utf-8")
        imported_components = active_component_imports(source)
        expected_components = {
            path.stem.removeprefix("_")
            for path in COMPONENTS_SCSS.glob("_*.scss")
        }
        self.assertEqual(imported_components, expected_components)
        self.assertEqual(
            source.count('@import "utilities/scroll_fade"'),
            1,
            "Scroll Fade selector partial must be imported exactly once",
        )

    def test_moo_component_and_utility_scss_do_not_reference_assets(self) -> None:
        offenders: list[str] = []
        for directory in (COMPONENTS_SCSS, UTILITIES_SCSS):
            for path in sorted(directory.glob("_*.scss")):
                if "url(" in path.read_text(encoding="utf-8").lower():
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_core_state_layer_bridges_detached_overlay_backdrops(self) -> None:
        state_layer = (SCSS / "_core_state_layer.scss").read_text(encoding="utf-8")

        self.assertIn(
            "body:has(.moo-ui .modal.show) > .modal-backdrop",
            state_layer,
        )
        self.assertIn("--#{$prefix}backdrop-opacity: 1", state_layer)
        self.assertIn(
            "var(--#{$prefix}black) 10%",
            state_layer,
        )
        self.assertNotIn("offcanvas.sheet.show", state_layer)
        self.assertEqual(state_layer.count("backdrop-filter: blur(4px)"), 2)

        core_css = CORE_CSS.read_text(encoding="utf-8")
        self.assertIn(
            ":has(> .offcanvas.sheet:is(.showing, .show)) > .offcanvas-backdrop",
            core_css,
        )
        self.assertIn(
            ":has(> .offcanvas.sheet.hiding) > .offcanvas-backdrop",
            core_css,
        )
