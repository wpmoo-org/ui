import ast
import unittest
from pathlib import Path


ADDON_ROOT = Path(__file__).resolve().parents[1]


class TestMooUiContract(unittest.TestCase):

    def test_manifest_declares_minimal_frontend_addon(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertEqual(manifest['version'], '19.0.1.0.0')
        self.assertEqual(manifest['depends'], ['web'])
        self.assertFalse(manifest['application'])
        self.assertTrue(manifest['installable'])


if __name__ == '__main__':
    unittest.main()
