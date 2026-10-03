from __future__ import annotations

import unittest

from playwright.sync_api import sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class ChartLoadingBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.addClassCleanup(cls.playwright_manager.__exit__, None, None, None)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def test_aggregate_fetches_chart_on_demand_and_retains_its_lifecycle(self) -> None:
        for filename in ("moo-ui.js", "moo-ui.min.js"):
            for case in CERTIFICATION_CASES:
                with self.subTest(module=filename, case=case.name):
                    context = new_case_context(self.browser, case)
                    try:
                        page = context.new_page()
                        evidence = BrowserEvidence(page)
                        requests = []
                        page.on("request", lambda request: requests.append(request.url))
                        page.route(
                            f"{self.base_url}/chart-loader-contract.html",
                            lambda route: route.fulfill(
                                content_type="text/html",
                                body="<!doctype html><html><head>"
                                '<link rel="stylesheet" href="/dist/assets/css/moo-ui.css">'
                                '</head><body><div class="moo-ui" data-bs-theme="'
                                + case.color_scheme + '"></div></body></html>',
                            ),
                        )
                        page.goto(
                            f"{self.base_url}/chart-loader-contract.html",
                            wait_until="networkidle",
                        )
                        prepare_page(page, case)
                        loaded = page.evaluate(
                            """async (url) => {
                              window.loaderApi = await import(url);
                              return typeof window.loaderApi.loadChart;
                            }""",
                            f"{self.base_url}/dist/js/{filename}",
                        )
                        self.assertEqual(loaded, "function")
                        chart_url = f"{self.base_url}/dist/js/chart.js"
                        self.assertNotIn(chart_url, requests)
                        report = page.evaluate("""async () => {
                          const api = window.loaderApi;
                          const [Chart, again] = await Promise.all([
                            api.loadChart(), api.default.loadChart(),
                          ]);
                          const direct = (await import("/dist/js/chart.js")).default;
                          const root = document.createElement("div");
                          root.className = "chart";
                          root.style.cssText = "width: 300px; height: 200px";
                          root.dataset.chart = "line";
                          root.dataset.chartData = JSON.stringify({
                            labels: ["One", "Two"],
                            datasets: [{label: "Values", data: [1, 2]}],
                          });
                          root.append(document.createElement("canvas"));
                          document.querySelector(".moo-ui").append(root);
                          const uninitialized = Chart.getInstance(root) === null;
                          const instance = Chart.getOrCreateInstance(root);
                          const report = {
                            shared: Chart === again && Chart === direct,
                            uninitialized,
                            rendered: instance.chart.canvas === root.firstElementChild,
                            sameInstance: Chart.getOrCreateInstance(root) === instance,
                          };
                          instance.dispose();
                          report.disposed = Chart.getInstance(root) === null;
                          return report;
                        }""")
                        self.assertEqual(report, {
                            "shared": True, "uninitialized": True, "rendered": True,
                            "sameInstance": True, "disposed": True,
                        })
                        self.assertEqual(requests.count(chart_url), 1)
                        evidence.assert_clean()
                    finally:
                        context.close()
