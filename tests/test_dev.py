from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from tests.helpers import ROOT, SITE_DIST


def load_dev_module():
    module_path = ROOT / "dev.py"
    assert module_path.exists(), "dev.py should exist"
    spec = importlib.util.spec_from_file_location("moo_dev", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DevRunnerTests(unittest.TestCase):
    def test_watcher_rebuild_uses_updated_build_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_source = """from pathlib import Path
ROOT = Path(__file__).resolve().parent
def source_snapshot():
    source = ROOT / 'build.py'
    return ((str(source), source.stat().st_mtime_ns),)
def build():
    (ROOT / 'rendered.txt').write_text({value!r}, encoding='utf-8')
"""
            (root / "build.py").write_text(
                build_source.format(value="old layout"), encoding="utf-8"
            )
            driver = """import importlib.util
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('moo_dev', sys.argv[1])
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)
replacement = sys.argv[2]

class OneSourceChange:
    calls = 0
    def wait(self, timeout):
        self.calls += 1
        if self.calls == 1:
            Path('build.py').write_text(replacement, encoding='utf-8')
            return False
        return True

dev.watch_sources(OneSourceChange())
"""
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    driver,
                    str(ROOT / "dev.py"),
                    build_source.format(value="current archive layout and navigation"),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (root / "rendered.txt").read_text(encoding="utf-8"),
                "current archive layout and navigation",
            )

    def test_help_lists_dev_server_options(self) -> None:
        result = subprocess.run(
            [sys.executable, "dev.py", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--host", result.stdout)
        self.assertIn("--port", result.stdout)
        self.assertIn("--open", result.stdout)

    def test_parser_defaults_match_documented_local_url(self) -> None:
        dev = load_dev_module()

        args = dev.create_parser().parse_args([])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 4173)
        self.assertFalse(args.open)

    def test_display_url_uses_localhost_for_loopback_host(self) -> None:
        dev = load_dev_module()

        self.assertEqual(
            dev.display_url("127.0.0.1", 4173),
            "http://localhost:4173/",
        )

    def test_server_handler_serves_site_dist_as_root(self) -> None:
        dev = load_dev_module()

        handler = dev.create_handler()

        self.assertIsInstance(handler, partial)
        # The dev server wraps SimpleHTTPRequestHandler in a no-store
        # subclass so rebuilds are never masked by heuristic caching.
        self.assertTrue(issubclass(handler.func, SimpleHTTPRequestHandler))
        self.assertEqual(handler.keywords, {"directory": str(SITE_DIST)})

    def test_server_does_not_publish_directory_listings(self) -> None:
        dev = load_dev_module()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "layouts/previews").mkdir(parents=True)
            (root / "layouts/previews/example.html").write_text(
                "preview\n",
                encoding="utf-8",
            )
            dev.SITE_DIST = root
            server = HTTPServer(("127.0.0.1", 0), dev.create_handler())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with self.assertRaises(HTTPError) as error:
                    urlopen(
                        f"http://127.0.0.1:{server.server_port}/layouts/",
                        timeout=2,
                    )
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
