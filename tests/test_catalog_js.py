from __future__ import annotations

import subprocess

from tests.helpers import DIST, ROOT, CatalogTestCase


CATALOG_JS = ROOT / "src/js/catalog"
MODULES = {
    "theme.js": "initTheme",
    "catalog-filter.js": "initCatalogFilter",
    "command.js": "initCommand",
    "toc.js": "initToc",
    "code-preview.js": "initCodePreview",
    "bootstrap-preview.js": "initBootstrapPreview",
    "home-motion.js": "initHomeMotion",
    "block-frame.js": "initBlockFrames",
}


class CatalogJavaScriptTests(CatalogTestCase):
    def test_catalog_features_have_idempotent_init_and_disposal(self) -> None:
        for module_name, initializer in MODULES.items():
            with self.subTest(module_name=module_name):
                source = (CATALOG_JS / module_name).read_text(encoding="utf-8")
                self.assertIn(f"export function {initializer}(root = document)", source)
                self.assertIn("if (states.has(root))", source)
                self.assertIn("states.set(root, dispose);", source)
                self.assertIn("states.delete(root);", source)

    def test_catalog_feature_imports_have_no_document_side_effect(self) -> None:
        imports = "\n".join(
            f'import "./src/js/catalog/{module_name}";' for module_name in MODULES
        )
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", imports],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_catalog_entrypoint_only_orchestrates_public_components(self) -> None:
        source = (CATALOG_JS / "index.js").read_text(encoding="utf-8")

        self.assertIn('import Combobox from "../components/combobox.js";', source)
        self.assertIn('import Sidebar from "../components/sidebar.js";', source)
        self.assertIn("Combobox.getOrCreateInstance(element)", source)
        self.assertIn("Sidebar.getOrCreateInstance(element)", source)
        self.assertIn("export function initCatalog(root = document)", source)
        self.assertIn("[...disposers].reverse()", source)
        self.assertNotIn(".combobox-input", source)
        self.assertNotIn("mooSidebarState", source)
        self.assertFalse((ROOT / "static/js/preview.js").exists())

    def test_build_copies_catalog_tree_recursively(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        for module_name in (*MODULES, "index.js"):
            self.assertTrue((DIST / f"assets/js/catalog/{module_name}").is_file())
