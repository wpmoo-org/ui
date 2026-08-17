from __future__ import annotations

import re
import subprocess

from tests.helpers import DIST, ROOT, CatalogTestCase


CATALOG_JS = ROOT / "site/src/js/catalog"
MODULES = {
    "acceptance.js": "initAcceptancePortal",
    "theme.js": "initTheme",
    "catalog-filter.js": "initCatalogFilter",
    "catalog-view-toggle.js": "initCatalogViewToggle",
    "command.js": "initCommand",
    "examples-chart.js": "initExamplesChart",
    "examples-forms.js": "initExamplesForms",
    "examples-tasks.js": "initExamplesTasks",
    "examples-users.js": "initExamplesUsers",
    "toc.js": "initToc",
    "code-preview.js": "initCodePreview",
    "bootstrap-preview.js": "initBootstrapPreview",
    "home-motion.js": "initHomeMotion",
    "block-frame.js": "initBlockFrames",
    "card-spacing.js": "initCardSpacing",
    "settings-panel.js": "initSettingsPanel",
}


def without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^[ \t]*//.*$", "", source, flags=re.MULTILINE)


class CatalogJavaScriptTests(CatalogTestCase):
    def test_catalog_module_surface_is_explicit(self) -> None:
        discovered = {
            path.relative_to(CATALOG_JS).as_posix()
            for path in CATALOG_JS.rglob("*.js")
        }
        self.assertEqual(discovered, {*MODULES, "index.js"})

    def test_catalog_features_have_idempotent_init_and_disposal(self) -> None:
        for module_name, initializer in MODULES.items():
            with self.subTest(module_name=module_name):
                source = without_comments(
                    (CATALOG_JS / module_name).read_text(encoding="utf-8")
                )
                self.assertIn(f"export function {initializer}(root = document)", source)
                self.assertIn("if (states.has(root))", source)
                if module_name == "examples-chart.js":
                    self.assertIn("states.set(root, release);", source)
                else:
                    self.assertIn("states.set(root, dispose);", source)
                self.assertIn("states.delete(root);", source)

    def test_catalog_feature_imports_have_no_document_side_effect(self) -> None:
        imports = "\n".join(
            f'import * as module{index} from "./site/src/js/catalog/{module_name}";\n'
            f'if (typeof module{index}.{initializer} !== "function") process.exit(2);'
            for index, (module_name, initializer) in enumerate(MODULES.items())
        )
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", imports],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_examples_chart_registers_pending_disposal_before_async_load(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-chart.js").read_text(encoding="utf-8")
        )

        pending_state = source.index("const pending =")
        registered = source.index("states.set(root, release);", pending_state)
        async_load = source.index("loadChartJs().then", registered)

        self.assertLess(registered, async_load)
        self.assertIn("pending.disposed", source)
        self.assertIn("if (pending.disposed)", source)

    def test_examples_chart_uses_effective_dataset_type_for_theme_updates(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-chart.js").read_text(encoding="utf-8")
        )

        self.assertIn("const datasetType = dataset.type || chart.config.type;", source)
        self.assertIn("if (datasetType === \"line\")", source)
        self.assertIn("} else if (datasetType === \"bar\")", source)
        self.assertNotIn("color-mix(in srgb, \${color} 65%, #ffffff)", source)

    def test_examples_chart_uses_a_bright_dark_theme_palette(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-chart.js").read_text(encoding="utf-8")
        )

        self.assertIn('"--bs-info-text-emphasis"', source)
        self.assertIn('"--bs-success-text-emphasis"', source)
        self.assertIn('"--bs-warning-text-emphasis"', source)
        self.assertIn('"--bs-danger-text-emphasis"', source)
        self.assertIn("const lightPalette", source)
        self.assertIn("const darkPalette", source)
        self.assertIn("const palette = isDark ? darkPalette : lightPalette;", source)
        self.assertIn('primary: colors["--bs-info"]', source)
        self.assertIn('primary: colors["--bs-info-text-emphasis"]', source)
        self.assertIn(
            "color-mix(in srgb, " + "$" + "{color} 92%, " + "$" + "{theme.color})",
            source,
        )
        self.assertIn(
            "color-mix(in srgb, " + "$" + "{color} 78%, transparent)",
            source,
        )

    def test_examples_chart_loader_is_version_pinned_and_integrity_checked(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-chart.js").read_text(encoding="utf-8")
        )

        self.assertIn("chart.js@4.5.1/dist/chart.umd.min.js", source)
        self.assertIn("const CHART_SRI = \"sha384-", source)
        self.assertIn("script.integrity = CHART_SRI", source)
        self.assertIn("script.crossOrigin = \"anonymous\"", source)

    def test_catalog_entrypoint_only_orchestrates_public_components(self) -> None:
        source = without_comments(
            (CATALOG_JS / "index.js").read_text(encoding="utf-8")
        )

        for module_name, initializer in MODULES.items():
            self.assertRegex(
                source,
                rf'import \{{ {initializer} \}} from "\./{re.escape(module_name)}";',
            )
            self.assertIn(f"{initializer}(root)", source)

        self.assertIn(
            'import Combobox from "../../../../src/js/components/combobox.js";',
            source,
        )
        self.assertIn(
            'import Sidebar from "../../../../src/js/components/sidebar.js";',
            source,
        )
        self.assertIn(
            'import ContextMenu from "../../../../src/js/components/context-menu.js";',
            source,
        )
        self.assertIn("Combobox.getOrCreateInstance(element)", source)
        self.assertIn("Sidebar.getOrCreateInstance(element)", source)
        self.assertIn("ContextMenu.getOrCreateInstance(element)", source)
        self.assertIn("export function initCatalog(root = document)", source)
        self.assertIn("[...disposers].reverse()", source)
        self.assertNotIn(".combobox-input", source)
        self.assertNotIn("mooSidebarState", source)
        self.assertFalse((ROOT / "site/static/js/preview.js").exists())

    def test_examples_row_actions_survive_reparented_menus(self) -> None:
        for module_name in ("examples-tasks.js", "examples-users.js"):
            with self.subTest(module_name=module_name):
                source = without_comments(
                    (CATALOG_JS / module_name).read_text(encoding="utf-8")
                )

                self.assertIn("const documentRoot = root.ownerDocument || root;", source)
                self.assertIn(
                    'target.closest(".dropdown-menu[data-datatable-row-action-owner]")',
                    source,
                )
                self.assertIn("rowById(ownerId)", source)
                self.assertIn(
                    'getAttribute("data-datatable-row-action-trigger")',
                    source,
                )
                self.assertIn("documentRoot.getElementById(triggerId)", source)
                self.assertIn('documentRoot.addEventListener("click", onPageClick);', source)
                self.assertIn(
                    'documentRoot.removeEventListener("click", onPageClick);',
                    source,
                )

    def test_examples_users_bulk_updates_keep_datatable_metadata_fresh(self) -> None:
        source = without_comments(
            (CATALOG_JS / "examples-users.js").read_text(encoding="utf-8")
        )

        self.assertIn("const syncBulkMetadata = (row, values) => {", source)
        self.assertRegex(
            source,
            r'row\.setAttribute\(\s*"data-datatable-search"',
        )
        self.assertIn('row.setAttribute("data-datatable-facet-status", status);', source)
        self.assertIn('row.setAttribute("data-datatable-facet-team", team);', source)
        self.assertIn(
            "row.querySelector('[data-datatable-column=\"team\"]')?.setAttribute",
            source,
        )
        self.assertIn(
            "row.querySelector('[data-datatable-column=\"status\"]')?.setAttribute",
            source,
        )
        self.assertIn('if (key !== "status" && key !== "team")', source)
        self.assertIn("queueMicrotask(reinitTable);", source)

    def test_build_copies_catalog_tree_recursively(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for module_name in (*MODULES, "index.js"):
            self.assertTrue((DIST / f"assets/js/catalog/{module_name}").is_file())
