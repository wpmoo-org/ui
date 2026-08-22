import os
import re
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    CANONICAL_BOOTSTRAP,
    CERTIFICATION_BOOTSTRAP_LANES,
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    run_axe,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


class CertificationBrowserHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.playwright_manager = sync_playwright()
        cls.playwright = cls.playwright_manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright_manager.__exit__(None, None, None)
        cls.server.__exit__(None, None, None)

    def test_chart_fixture_proves_built_bundle_rendering_and_diagnostics(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                try:
                    page = context.new_page()
                    evidence = BrowserEvidence(page)
                    response = page.goto(
                        f"{self.base_url}/tests/fixtures/certification/chart.html",
                        wait_until="networkidle",
                    )
                    self.assertIsNotNone(response)
                    self.assertTrue(response.ok)
                    prepare_page(page, case)

                    expect(page.locator("body")).to_have_attribute(
                        "data-chart-ready", "true"
                    )
                    self.assertEqual(
                        page.evaluate(
                            """() => [
                              window.certificationLineChart.chart.config.type,
                              window.certificationBarChart.chart.config.type,
                            ]"""
                        ),
                        ["line", "bar"],
                    )
                    self.assertTrue(
                        page.evaluate(
                            """() => [
                              '#certification-chart-line',
                              '#certification-chart-bar',
                            ].map(id => document.querySelector(`${id} canvas`)).every(canvas => {
                              const data = canvas.getContext('2d').getImageData(
                                0, 0, canvas.width, canvas.height
                              ).data;
                              return data.some(value => value !== 0);
                            })"""
                        )
                    )
                    self.assertIn(
                        "MooChart could not parse data-chart-data as JSON:",
                        page.evaluate("() => window.certificationInvalidMessage"),
                    )
                    evidence.assert_clean()
                finally:
                    context.close()

    def test_accordion_fixture_proves_data_api_state_and_keyboard_flow(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/accordion.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                first_trigger = page.locator("#certification-first-trigger")
                first_panel = page.locator("#certification-first")
                second_trigger = page.locator("#certification-second-trigger")
                second_panel = page.locator("#certification-second")
                self.assertEqual(first_trigger.get_attribute("aria-expanded"), "true")
                self.assertTrue(first_panel.evaluate("element => element.classList.contains('show')"))
                self.assertEqual(second_trigger.get_attribute("aria-expanded"), "false")
                self.assertEqual(
                    page.evaluate(
                        """
                        () => bootstrap.Collapse.getOrCreateInstance(
                          document.querySelector("#certification-second"),
                          { toggle: false },
                        )._config.parent?.id
                        """
                    ),
                    "certification-accordion",
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const panel = document.querySelector("#certification-second");
                      panel.addEventListener("shown.bs.collapse", resolve, { once: true });
                      document.querySelector("#certification-second-trigger").click();
                    })
                    """
                )
                expect(second_trigger).to_have_attribute("aria-expanded", "true")
                expect(first_trigger).to_have_attribute("aria-expanded", "false")
                self.assertTrue(second_panel.evaluate("element => element.classList.contains('show')"))
                self.assertFalse(first_panel.evaluate("element => element.classList.contains('show')"))

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const panel = document.querySelector("#certification-second");
                      panel.addEventListener("hidden.bs.collapse", resolve, { once: true });
                      document.querySelector("#certification-second-trigger").click();
                    })
                    """
                )
                expect(second_trigger).to_have_attribute("aria-expanded", "false")
                first_trigger.focus()
                first_trigger.press("Enter")
                expect(first_trigger).to_have_attribute("aria-expanded", "true")
                expect(first_panel).to_have_class("accordion-collapse collapse show")
                first_trigger.press("Space")
                expect(first_panel).to_have_class("accordion-collapse collapse")
                expect(first_trigger).to_have_attribute("aria-expanded", "false")
                self.assertTrue(
                    first_trigger.evaluate(
                        "element => document.activeElement === element"
                    )
                )

                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_combobox_fixture_proves_public_esm_keyboard_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/combobox.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                root = page.locator("#certification-combobox")
                combobox_input = page.locator("#certification-combobox-input")
                indicator = root.locator(".combobox-indicator")
                menu = page.locator("#certification-combobox-listbox")
                hidden_value = root.locator('input[type="hidden"]')
                empty_state = root.locator("[data-combobox-empty]")
                live_region = root.locator("[data-combobox-live]")
                expect(page.locator("body")).to_have_attribute("data-combobox-ready", "true")
                expect(indicator.locator('[data-lucide="chevron-down"]')).to_have_count(1)
                self.assertEqual(indicator.inner_text().strip(), "")
                self.assertTrue(
                    root.evaluate(
                        """
                        element => window.CertificationCombobox.getInstance(element)
                          === window.certificationCombobox
                        """
                    )
                )

                combobox_input.focus()
                expect(combobox_input).to_have_attribute("aria-expanded", "true")
                expect(menu).to_have_class("dropdown-menu combobox-menu show")
                expect(combobox_input).to_have_attribute(
                    "aria-activedescendant",
                    "certification-combobox-option-1",
                )
                combobox_input.press("ArrowDown")
                expect(combobox_input).to_have_attribute(
                    "aria-activedescendant",
                    "certification-combobox-option-2",
                )
                self.assertTrue(
                    combobox_input.evaluate("element => document.activeElement === element")
                )
                self.assertEqual(run_axe(page), [])

                combobox_input.press("Enter")
                expect(combobox_input).to_have_value("Grace Hopper")
                expect(hidden_value).to_have_value("grace")
                expect(combobox_input).to_have_attribute("aria-expanded", "false")
                expect(page.locator("body")).to_have_attribute(
                    "data-combobox-values",
                    "grace",
                )
                expect(page.locator("#certification-combobox-option-2")).to_have_attribute(
                    "aria-selected",
                    "true",
                )

                combobox_input.focus()
                combobox_input.fill("not-a-reviewer")
                expect(empty_state).to_be_visible()
                expect(live_region).to_have_text("No results")
                expect(combobox_input).to_have_attribute("aria-expanded", "true")
                combobox_input.press("Escape")
                expect(combobox_input).to_have_attribute("aria-expanded", "false")

                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationCombobox.dispose();
                          return window.CertificationCombobox.getInstance(element) === null;
                        }
                        """
                    )
                )
                self.assertEqual(root.locator("[data-combobox-empty]").count(), 0)
                self.assertEqual(root.locator("[data-combobox-live]").count(), 0)
                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationCombobox = window.CertificationCombobox
                            .getOrCreateInstance(element);
                          return window.CertificationCombobox.getInstance(element)
                            === window.certificationCombobox;
                        }
                        """
                    )
                )
                self.assertEqual(root.locator("[data-combobox-empty]").count(), 1)
                self.assertEqual(root.locator("[data-combobox-live]").count(), 1)
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_sidebar_fixture_proves_desktop_mobile_state_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/sidebar.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                root = page.locator('[data-slot="sidebar-wrapper"]')
                sidebar = page.locator("#certification-sidebar")
                trigger = page.locator("#certification-sidebar-trigger")
                search = page.locator("#certification-sidebar-search")
                expect(page.locator("body")).to_have_attribute("data-sidebar-ready", "true")
                expect(root).to_have_attribute("data-sidebar-ready", "")
                self.assertTrue(
                    root.evaluate(
                        """
                        element => window.CertificationSidebar.getInstance(element)
                          === window.certificationSidebar
                        """
                    )
                )

                if case.is_mobile:
                    expect(trigger).to_have_attribute("aria-expanded", "false")
                    page.evaluate(
                        """
                        () => {
                          document.querySelector("#certification-sidebar").addEventListener(
                            "shown.bs.offcanvas",
                            () => document.body.dataset.sidebarShown = "true",
                            { once: true },
                          );
                        }
                        """
                    )
                    trigger.click()
                    expect(page.locator("body")).to_have_attribute("data-sidebar-shown", "true")
                    expect(sidebar).to_have_class("sidebar offcanvas-lg offcanvas-start show")
                    expect(trigger).to_have_attribute("aria-expanded", "true")
                    self.assertEqual(page.locator(".offcanvas-backdrop.show").count(), 1)
                    self.assertEqual(run_axe(page), [])

                    page.evaluate(
                        """
                        () => {
                          document.querySelector("#certification-sidebar").addEventListener(
                            "hidden.bs.offcanvas",
                            () => document.body.dataset.sidebarHidden = "true",
                            { once: true },
                          );
                        }
                        """
                    )
                    page.keyboard.press("Escape")
                    expect(page.locator("body")).to_have_attribute("data-sidebar-hidden", "true")
                    expect(trigger).to_have_attribute("aria-expanded", "false")
                    expect(trigger).to_be_focused()
                    self.assertEqual(page.locator(".offcanvas-backdrop").count(), 0)
                else:
                    expect(root).to_have_attribute("data-sidebar-state", "expanded")
                    expect(trigger).to_have_attribute("aria-expanded", "true")
                    trigger.click()
                    expect(root).to_have_attribute("data-sidebar-state", "collapsed")
                    expect(trigger).to_have_attribute("aria-expanded", "false")
                    expect(page.locator("body")).to_have_attribute(
                        "data-sidebar-state",
                        "collapsed",
                    )
                    self.assertEqual(
                        page.evaluate(
                            "localStorage.getItem('moo-sidebar:certification-shell')"
                        ),
                        "collapsed",
                    )
                    page.keyboard.press("Control+b")
                    expect(root).to_have_attribute("data-sidebar-state", "expanded")
                    search.focus()
                    page.keyboard.press("Control+b")
                    expect(root).to_have_attribute("data-sidebar-state", "expanded")
                    self.assertEqual(run_axe(page), [])

                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationSidebar.dispose();
                          return window.CertificationSidebar.getInstance(element) === null
                            && !element.hasAttribute("data-sidebar-ready");
                        }
                        """
                    )
                )
                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationSidebar = window.CertificationSidebar
                            .getOrCreateInstance(element);
                          return window.CertificationSidebar.getInstance(element)
                            === window.certificationSidebar
                            && element.hasAttribute("data-sidebar-ready");
                        }
                        """
                    )
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_sidebar_mobile_offcanvas_keeps_bootstrap_transform_transition(self) -> None:
        context_options: dict[str, object] = {
            "viewport": {"width": 390, "height": 844},
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "locale": "en-US",
        }
        # Firefox rejects the mobile/touch emulation options; the offcanvas
        # transition under audit does not depend on them.
        if self.browser.browser_type.name != "firefox":
            context_options["is_mobile"] = True
            context_options["has_touch"] = True
        context = self.browser.new_context(**context_options)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        response = page.goto(
            f"{self.base_url}/tests/fixtures/certification/sidebar.html",
            wait_until="networkidle",
        )
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        page.locator("html").evaluate(
            """
            element => {
              element.setAttribute("dir", "ltr");
              element.setAttribute("data-bs-theme", "light");
            }
            """
        )
        expect(page.locator("body")).to_have_attribute("data-sidebar-ready", "true")

        transition = page.locator("#certification-sidebar").evaluate(
            """
            element => {
              const style = getComputedStyle(element);
              return {
                property: style.transitionProperty,
                duration: style.transitionDuration,
                timing: style.transitionTimingFunction,
                transform: style.transform,
                variable: style.getPropertyValue("--bs-offcanvas-transition").trim(),
              };
            }
            """
        )
        self.assertIn("transform", transition["variable"])
        self.assertIn("transform", transition["property"])
        self.assertNotEqual(transition["duration"], "0s")
        self.assertNotEqual(transition["transform"], "none")
        evidence.assert_clean()
        context.close()

    def test_tooltip_fixture_proves_placement_focus_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/tooltip.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                body = page.locator("body")
                edge_trigger = page.locator("#certification-tooltip-edge-trigger")
                repeat_trigger = page.locator("#certification-tooltip-repeat-trigger")
                expect(body).to_have_attribute("data-tooltip-ready", "true")
                self.assertTrue(
                    edge_trigger.evaluate(
                        "element => bootstrap.Tooltip.getInstance(element) "
                        "=== window.certificationEdgeTooltip"
                    )
                )
                self.assertTrue(
                    repeat_trigger.evaluate(
                        "element => bootstrap.Tooltip.getInstance(element) "
                        "=== window.certificationRepeatTooltip"
                    )
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-tooltip-edge-trigger"
                      );
                      trigger.addEventListener("shown.bs.tooltip", resolve, { once: true });
                      trigger.focus();
                    })
                    """
                )
                described_by = edge_trigger.get_attribute("aria-describedby")
                self.assertIsNotNone(described_by)
                edge_tip = page.locator(f"#{described_by}")
                expect(edge_tip).to_have_attribute("role", "tooltip")
                edge_placement = edge_tip.get_attribute("data-popper-placement")
                self.assertIn(edge_placement, {"top", "right", "bottom"})
                if not case.is_mobile:
                    self.assertEqual(edge_placement, "right")
                expect(edge_tip.locator(".tooltip-inner")).to_have_text(
                    "Placement flips away from the viewport edge"
                )
                edge_box = edge_tip.bounding_box()
                self.assertIsNotNone(edge_box)
                self.assertGreaterEqual(edge_box["x"], 0)
                self.assertLessEqual(
                    edge_box["x"] + edge_box["width"],
                    case.viewport["width"] + 1,
                )
                self.assertEqual(page.locator(".modal-backdrop, .offcanvas-backdrop").count(), 0)
                self.assertNotEqual(page.evaluate("getComputedStyle(document.body).overflow"), "hidden")
                self.assertEqual(run_axe(page), [])

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const edge = document.querySelector(
                        "#certification-tooltip-edge-trigger"
                      );
                      const repeat = document.querySelector(
                        "#certification-tooltip-repeat-trigger"
                      );
                      let hidden = false;
                      let shown = false;
                      const finish = () => hidden && shown && resolve();
                      edge.addEventListener("hidden.bs.tooltip", () => {
                        hidden = true;
                        finish();
                      }, { once: true });
                      repeat.addEventListener("shown.bs.tooltip", () => {
                        shown = true;
                        finish();
                      }, { once: true });
                      repeat.focus();
                    })
                    """
                )
                self.assertIsNone(edge_trigger.get_attribute("aria-describedby"))
                repeat_tip_id = repeat_trigger.get_attribute("aria-describedby")
                self.assertIsNotNone(repeat_tip_id)
                self.assertTrue(
                    page.locator(f"#{repeat_tip_id}").evaluate(
                        "element => element.classList.contains('tooltip') "
                        "&& element.classList.contains('show')"
                    )
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-tooltip-repeat-trigger"
                      );
                      trigger.addEventListener("hidden.bs.tooltip", resolve, { once: true });
                      trigger.blur();
                    })
                    """
                )
                self.assertIsNone(repeat_trigger.get_attribute("aria-describedby"))
                self.assertTrue(
                    repeat_trigger.evaluate(
                        """
                        element => {
                          window.certificationRepeatTooltip.dispose();
                          return bootstrap.Tooltip.getInstance(element) === null;
                        }
                        """
                    )
                )
                self.assertTrue(
                    repeat_trigger.evaluate(
                        """
                        element => {
                          window.certificationRepeatTooltip = bootstrap.Tooltip
                            .getOrCreateInstance(element, { container: document.body });
                          return bootstrap.Tooltip.getInstance(element)
                            === window.certificationRepeatTooltip;
                        }
                        """
                    )
                )
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-tooltip-repeat-trigger"
                      );
                      trigger.addEventListener("shown.bs.tooltip", resolve, { once: true });
                      trigger.focus();
                    })
                    """
                )
                self.assertIsNotNone(repeat_trigger.get_attribute("aria-describedby"))
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_popover_fixture_proves_dismissal_placement_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/popover.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                body = page.locator("body")
                focus_trigger = page.locator("#certification-popover-focus-trigger")
                edge_trigger = page.locator("#certification-popover-edge-trigger")
                next_target = page.locator("#certification-popover-next")
                expect(body).to_have_attribute("data-popover-ready", "true")
                self.assertTrue(
                    focus_trigger.evaluate(
                        "element => bootstrap.Popover.getInstance(element) "
                        "=== window.certificationFocusPopover"
                    )
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-popover-focus-trigger"
                      );
                      trigger.addEventListener("shown.bs.popover", resolve, { once: true });
                      trigger.focus();
                    })
                    """
                )
                focus_tip_id = focus_trigger.get_attribute("aria-describedby")
                self.assertIsNotNone(focus_tip_id)
                focus_tip = page.locator(f"#{focus_tip_id}")
                expect(focus_tip).to_have_attribute("role", "tooltip")
                expect(focus_tip.locator(".popover-header")).to_have_text("Review status")
                expect(focus_tip.locator(".popover-body")).to_have_text(
                    "The change is ready for a final review."
                )
                expect(focus_trigger).to_be_focused()
                self.assertEqual(run_axe(page), [])

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-popover-focus-trigger"
                      );
                      trigger.addEventListener("hidden.bs.popover", resolve, { once: true });
                      document.querySelector("#certification-popover-next").focus();
                    })
                    """
                )
                self.assertIsNone(focus_trigger.get_attribute("aria-describedby"))
                expect(next_target).to_be_focused()

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-popover-edge-trigger"
                      );
                      trigger.addEventListener("shown.bs.popover", resolve, { once: true });
                      trigger.click();
                    })
                    """
                )
                edge_tip_id = edge_trigger.get_attribute("aria-describedby")
                self.assertIsNotNone(edge_tip_id)
                edge_tip = page.locator(f"#{edge_tip_id}")
                self.assertIn(
                    edge_tip.get_attribute("data-popper-placement"),
                    {"top", "right", "bottom"},
                )
                edge_box = edge_tip.bounding_box()
                self.assertIsNotNone(edge_box)
                self.assertGreaterEqual(edge_box["x"], -1)
                self.assertLessEqual(
                    edge_box["x"] + edge_box["width"],
                    case.viewport["width"] + 1,
                )
                self.assertEqual(page.locator(".modal-backdrop, .offcanvas-backdrop").count(), 0)
                self.assertNotEqual(page.evaluate("getComputedStyle(document.body).overflow"), "hidden")

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-popover-edge-trigger"
                      );
                      trigger.addEventListener("hidden.bs.popover", resolve, { once: true });
                      trigger.click();
                    })
                    """
                )
                self.assertIsNone(edge_trigger.get_attribute("aria-describedby"))
                self.assertTrue(
                    edge_trigger.evaluate(
                        """
                        element => {
                          window.certificationEdgePopover.dispose();
                          return bootstrap.Popover.getInstance(element) === null;
                        }
                        """
                    )
                )
                self.assertTrue(
                    edge_trigger.evaluate(
                        """
                        element => {
                          window.certificationEdgePopover = bootstrap.Popover
                            .getOrCreateInstance(element, {
                              boundary: document.body,
                              container: document.body,
                            });
                          return bootstrap.Popover.getInstance(element)
                            === window.certificationEdgePopover;
                        }
                        """
                    )
                )
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const trigger = document.querySelector(
                        "#certification-popover-edge-trigger"
                      );
                      trigger.addEventListener("shown.bs.popover", resolve, { once: true });
                      trigger.click();
                    })
                    """
                )
                self.assertIsNotNone(edge_trigger.get_attribute("aria-describedby"))
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_toast_catalog_repeated_trigger_stacked_deck_contracts(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 900, "height": 844},
            reduced_motion="no-preference",
        )
        page = context.new_page()
        evidence = BrowserEvidence(page)
        response = page.goto(
            f"{self.base_url}/site-dist/components/toast/index.html",
            wait_until="networkidle",
        )
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)

        trigger = page.locator('[data-toast-target="#toast-demo-template"]')
        deck = page.locator('.toast-container--stacked[data-toast-stack="deck"]')
        generated = deck.locator('[data-toast-generated="true"]')
        self.assertEqual(trigger.count(), 1)
        expect(deck.locator("template[data-toast-template=\"toast\"]")).to_have_count(1)
        expect(deck.locator('[data-toast-stack-index]')).to_have_count(0)

        for _ in range(6):
            trigger.click()

        expect(generated).to_have_count(6)
        expect(deck.locator(".toast.show")).to_have_count(6)
        visible = deck.locator('.toast.show:not([data-toast-stack-limited])')
        limited = deck.locator('.toast.show[data-toast-stack-limited]')
        expect(visible).to_have_count(3)
        expect(limited).to_have_count(3)
        ids = generated.evaluate_all("elements => elements.map(element => element.id)")
        indexes = visible.evaluate_all(
            "elements => elements.map(element => element.dataset.toastStackIndex)"
        )
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(indexes), ["0", "1", "2"])
        self.assertEqual(
            generated.evaluate_all(
                "elements => elements.map(element => element.dataset.toastStackIndex)"
            ),
            ["0", "1", "2", "3", "4", "5"],
        )
        self.assertTrue(
            all(
                limited.evaluate_all(
                    "elements => elements.map(element => element.hasAttribute('inert'))"
                )
            )
        )
        self.assertEqual(
            sorted(
                visible.evaluate_all(
                    "elements => elements.map(element => element.style.getPropertyValue('--moo-toast-stack-z'))"
                )
            ),
            ["1", "2", "3"],
        )

        newest = deck.locator('.toast.show[data-toast-stack-index="0"]')
        newest_box = newest.bounding_box()
        self.assertIsNotNone(newest_box)
        client_width = page.evaluate("document.documentElement.clientWidth")
        self.assertAlmostEqual(
            newest_box["x"] + newest_box["width"],
            client_width - 16,
            delta=2,
        )
        self.assertAlmostEqual(newest_box["width"], 384, delta=2)
        self.assertEqual(
            newest.evaluate("element => getComputedStyle(element).transformOrigin"),
            f"{newest_box['width'] / 2:g}px {newest_box['height']:g}px",
        )
        self.assertLessEqual(newest_box["y"] + newest_box["height"], 845)
        self.assertGreater(newest_box["x"] + newest_box["width"] / 2, client_width / 2)
        expect(newest.locator(".btn-close")).to_have_attribute("aria-label", "Close")
        expect(newest.locator('[data-bs-dismiss="toast"]')).to_have_count(2)

        older = deck.locator('.toast.show[data-toast-stack-index="1"]')
        older_before = older.bounding_box()
        self.assertIsNotNone(older_before)
        self.assertLess(older_before["y"], newest_box["y"])
        newest.hover()
        page.wait_for_timeout(250)
        older_after = older.bounding_box()
        self.assertIsNotNone(older_after)
        self.assertNotEqual(older_before["y"], older_after["y"])

        close_button = newest.locator(".btn-close")
        close_button.focus()
        expect(close_button).to_be_focused()
        close_button.press("Enter")
        expect(generated).to_have_count(5)
        expect(visible).to_have_count(3)
        expect(limited).to_have_count(2)
        self.assertEqual(
            sorted(
                visible.evaluate_all(
                    "elements => elements.map(element => element.dataset.toastStackIndex)"
                )
            ),
            ["0", "1", "2"],
        )
        expect(page.locator("template[data-toast-template=\"toast\"]")).to_have_count(1)

        page.mouse.move(0, 0)
        expect(generated).to_have_count(0, timeout=7000)
        self.assertEqual(deck.locator('[data-toast-stack-index]').count(), 0)
        self.assertEqual(run_axe(page), [])
        evidence.assert_clean()
        context.close()

    def test_toast_stack_fallback_fixture_keeps_static_toasts_in_flow(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/toast-stack-fallback.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                deck = page.locator("#certification-toast-stack-fallback")
                toasts = deck.locator(":scope > .toast")
                expect(toasts).to_have_count(2)
                self.assertEqual(
                    toasts.evaluate_all(
                        "elements => elements.map(element => element.dataset.toastStackIndex || null)"
                    ),
                    [None, None],
                )
                first_box = toasts.nth(0).bounding_box()
                second_box = toasts.nth(1).bounding_box()
                self.assertIsNotNone(first_box)
                self.assertIsNotNone(second_box)
                self.assertGreaterEqual(second_box["y"], first_box["y"] + first_box["height"])
                self.assertEqual(run_axe(page), [])
                evidence.assert_clean()
                context.close()

    def test_toast_fixture_proves_status_dismissal_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/toast.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                body = page.locator("body")
                trigger = page.locator("#certification-toast-trigger")
                toast = page.locator("#certification-toast")
                close_button = toast.locator(".btn-close")
                expect(body).to_have_attribute("data-toast-ready", "true")
                self.assertTrue(
                    toast.evaluate(
                        "element => bootstrap.Toast.getInstance(element) "
                        "=== window.certificationToast"
                    )
                )
                expect(toast).to_have_attribute("role", "status")
                expect(toast).to_have_attribute("aria-live", "polite")
                expect(toast).to_have_attribute("aria-atomic", "true")

                trigger.focus()
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const toast = document.querySelector("#certification-toast");
                      toast.addEventListener("shown.bs.toast", resolve, { once: true });
                      document.querySelector("#certification-toast-trigger").click();
                    })
                    """
                )
                self.assertTrue(toast.evaluate("element => element.classList.contains('show')"))
                expect(trigger).to_be_focused()
                toast_box = toast.bounding_box()
                self.assertIsNotNone(toast_box)
                self.assertGreaterEqual(toast_box["x"], -1)
                self.assertLessEqual(
                    toast_box["x"] + toast_box["width"],
                    case.viewport["width"] + 1,
                )
                self.assertEqual(run_axe(page), [])

                close_button.focus()
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const toast = document.querySelector("#certification-toast");
                      toast.addEventListener("hidden.bs.toast", resolve, { once: true });
                      toast.querySelector(".btn-close").click();
                    })
                    """
                )
                self.assertFalse(toast.evaluate("element => element.classList.contains('show')"))
                self.assertTrue(
                    toast.evaluate(
                        """
                        element => {
                          window.certificationToast.dispose();
                          return bootstrap.Toast.getInstance(element) === null;
                        }
                        """
                    )
                )
                self.assertTrue(
                    toast.evaluate(
                        """
                        element => {
                          window.certificationToast = bootstrap.Toast
                            .getOrCreateInstance(element, { autohide: false });
                          return bootstrap.Toast.getInstance(element)
                            === window.certificationToast;
                        }
                        """
                    )
                )
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const toast = document.querySelector("#certification-toast");
                      toast.addEventListener("shown.bs.toast", resolve, { once: true });
                      document.querySelector("#certification-toast-trigger").click();
                    })
                    """
                )
                self.assertTrue(toast.evaluate("element => element.classList.contains('show')"))
                self.assertEqual(page.locator(".modal-backdrop, .offcanvas-backdrop").count(), 0)
                self.assertNotEqual(page.evaluate("getComputedStyle(document.body).overflow"), "hidden")
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_sheet_fixture_proves_focus_backdrop_scroll_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/sheet.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                trigger = page.locator("#certification-sheet-trigger")
                sheet = page.locator("#certification-sheet")
                close_button = sheet.locator(".btn-close")
                name_input = page.locator("#certification-sheet-name")
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const sheet = document.querySelector("#certification-sheet");
                      sheet.addEventListener("shown.bs.offcanvas", resolve, { once: true });
                      document.querySelector("#certification-sheet-trigger").click();
                    })
                    """
                )
                self.assertTrue(sheet.evaluate("element => element.classList.contains('show')"))
                expect(sheet).to_have_attribute("role", "dialog")
                expect(sheet).to_have_attribute("aria-modal", "true")
                expect(sheet).to_be_focused()
                self.assertEqual(page.locator(".offcanvas-backdrop.show").count(), 1)
                self.assertEqual(page.evaluate("getComputedStyle(document.body).overflow"), "hidden")

                close_button.focus()
                page.keyboard.press("Tab")
                expect(name_input).to_be_focused()
                trigger.focus()
                expect(close_button).to_be_focused()
                self.assertEqual(run_axe(page), [])

                page.evaluate(
                    """
                    () => {
                      document.querySelector("#certification-sheet").addEventListener(
                        "hidden.bs.offcanvas",
                        () => document.body.dataset.sheetHidden = "true",
                        { once: true },
                      );
                    }
                    """
                )
                page.keyboard.press("Escape")
                expect(page.locator("body")).to_have_attribute("data-sheet-hidden", "true")
                expect(trigger).to_be_focused()
                self.assertEqual(page.locator(".offcanvas-backdrop").count(), 0)

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const sheet = document.querySelector("#certification-sheet");
                      sheet.addEventListener("shown.bs.offcanvas", resolve, { once: true });
                      document.querySelector("#certification-sheet-trigger").click();
                    })
                    """
                )
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const sheet = document.querySelector("#certification-sheet");
                      sheet.addEventListener("hidden.bs.offcanvas", resolve, { once: true });
                      sheet.querySelector(".btn-close").click();
                    })
                    """
                )
                expect(trigger).to_be_focused()
                self.assertTrue(
                    sheet.evaluate(
                        """
                        element => {
                          const instance = bootstrap.Offcanvas.getInstance(element);
                          instance.dispose();
                          return bootstrap.Offcanvas.getInstance(element) === null;
                        }
                        """
                    )
                )
                self.assertTrue(
                    sheet.evaluate(
                        """
                        element => bootstrap.Offcanvas.getOrCreateInstance(element)
                          === bootstrap.Offcanvas.getInstance(element)
                        """
                    )
                )

                scroll_trigger = page.locator("#certification-scroll-sheet-trigger")
                scroll_sheet = page.locator("#certification-scroll-sheet")
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const sheet = document.querySelector("#certification-scroll-sheet");
                      sheet.addEventListener("shown.bs.offcanvas", resolve, { once: true });
                      document.querySelector("#certification-scroll-sheet-trigger").click();
                    })
                    """
                )
                self.assertTrue(
                    scroll_sheet.evaluate("element => element.classList.contains('show')")
                )
                self.assertEqual(page.locator(".offcanvas-backdrop").count(), 0)
                self.assertNotEqual(page.evaluate("getComputedStyle(document.body).overflow"), "hidden")
                scroll_sheet.focus()
                page.evaluate(
                    """
                    () => {
                      document.querySelector("#certification-scroll-sheet").addEventListener(
                        "hidden.bs.offcanvas",
                        () => document.body.dataset.scrollSheetHidden = "true",
                        { once: true },
                      );
                    }
                    """
                )
                page.keyboard.press("Escape")
                expect(page.locator("body")).to_have_attribute(
                    "data-scroll-sheet-hidden",
                    "true",
                )
                expect(scroll_trigger).to_be_focused()
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_dialog_fixture_proves_focus_backdrop_and_escape_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/dialog.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                trigger = page.locator("#open-certification-dialog")
                dialog = page.locator("#certification-dialog")
                close_button = dialog.locator(".btn-close")
                display_name = page.locator("#certification-display-name")

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-dialog");
                      dialog.addEventListener("shown.bs.modal", resolve, { once: true });
                      document.querySelector("#open-certification-dialog").click();
                    })
                    """
                )
                expect(dialog).to_have_class("modal fade show")
                expect(dialog).to_have_attribute("aria-modal", "true")
                expect(dialog).to_have_attribute("role", "dialog")
                self.assertIsNone(dialog.get_attribute("aria-hidden"))
                self.assertEqual(page.locator(".modal-backdrop.show").count(), 1)
                self.assertTrue(
                    dialog.evaluate("element => document.activeElement === element")
                )

                close_button.focus()
                page.keyboard.press("Tab")
                expect(display_name).to_be_focused()
                trigger.focus()
                expect(close_button).to_be_focused()
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)

                page.evaluate(
                    """
                    () => {
                      document.querySelector("#certification-dialog").addEventListener(
                        "hidden.bs.modal",
                        () => document.body.dataset.dialogHidden = "true",
                        { once: true },
                      );
                    }
                    """
                )
                page.keyboard.press("Escape")
                expect(page.locator("body")).to_have_attribute("data-dialog-hidden", "true")
                self.assertEqual(page.locator(".modal-backdrop").count(), 0)
                self.assertTrue(
                    trigger.evaluate("element => document.activeElement === element")
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-dialog");
                      dialog.addEventListener("shown.bs.modal", resolve, { once: true });
                      document.querySelector("#open-certification-dialog").click();
                    })
                    """
                )
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-dialog");
                      dialog.addEventListener("hidden.bs.modal", resolve, { once: true });
                      dialog.querySelector(".btn-close").click();
                    })
                    """
                )
                self.assertEqual(page.locator(".modal-backdrop").count(), 0)
                self.assertTrue(
                    trigger.evaluate("element => document.activeElement === element")
                )
                evidence.assert_clean()
                context.close()

    def test_alert_dialog_fixture_proves_static_confirmation_contract(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/alert-dialog.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                trigger = page.locator("#open-certification-alert-dialog")
                dialog = page.locator("#certification-alert-dialog")
                title = page.locator("#certification-alert-dialog-title")
                cancel = page.locator("#cancel-certification-alert-dialog")
                confirm = page.locator("#confirm-certification-alert-dialog")

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-alert-dialog");
                      dialog.addEventListener("shown.bs.modal", resolve, { once: true });
                      document.querySelector("#open-certification-alert-dialog").click();
                    })
                    """
                )
                expect(dialog).to_have_class("modal fade modal--alert show")
                expect(dialog).to_have_attribute("data-bs-backdrop", "static")
                expect(dialog).to_have_attribute("data-bs-keyboard", "false")
                expect(dialog).to_have_attribute("aria-modal", "true")
                expect(dialog).to_have_attribute("role", "dialog")
                expect(dialog).to_have_attribute(
                    "aria-describedby",
                    "certification-alert-dialog-description",
                )
                expect(title).to_have_text("Discard this draft invoice?")
                self.assertEqual(dialog.locator(".btn-close").count(), 0)
                self.assertEqual(page.locator(".modal-backdrop.show").count(), 1)
                self.assertTrue(
                    dialog.evaluate("element => document.activeElement === element")
                )

                page.evaluate(
                    """
                    () => {
                      const dialog = document.querySelector("#certification-alert-dialog");
                      dialog.addEventListener(
                        "hidden.bs.modal",
                        () => document.body.dataset.alertDialogHidden = "true",
                      );
                      dialog.addEventListener(
                        "hidePrevented.bs.modal",
                        () => document.body.dataset.alertDialogPrevented = "true",
                        { once: true },
                      );
                    }
                    """
                )
                page.keyboard.press("Escape")
                expect(page.locator("body")).to_have_attribute(
                    "data-alert-dialog-prevented",
                    "true",
                )
                self.assertIsNone(page.locator("body").get_attribute("data-alert-dialog-hidden"))
                expect(dialog).to_have_class("modal fade modal--alert show")

                cancel.focus()
                page.keyboard.press("Tab")
                expect(confirm).to_be_focused()
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-alert-dialog");
                      dialog.addEventListener("hidden.bs.modal", resolve, { once: true });
                      document.querySelector("#cancel-certification-alert-dialog").click();
                    })
                    """
                )
                self.assertEqual(page.locator(".modal-backdrop").count(), 0)
                self.assertTrue(
                    trigger.evaluate("element => document.activeElement === element")
                )

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-alert-dialog");
                      dialog.addEventListener("shown.bs.modal", resolve, { once: true });
                      document.querySelector("#open-certification-alert-dialog").click();
                    })
                    """
                )
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const dialog = document.querySelector("#certification-alert-dialog");
                      dialog.addEventListener("hidden.bs.modal", resolve, { once: true });
                      document.querySelector("#confirm-certification-alert-dialog").click();
                    })
                    """
                )
                self.assertEqual(page.locator(".modal-backdrop").count(), 0)
                self.assertTrue(
                    trigger.evaluate("element => document.activeElement === element")
                )
                evidence.assert_clean()
                context.close()

    def test_bootstrap_lane_resolves_the_real_local_bundle(self) -> None:
        expected_version = os.environ.get(
            "MOO_UI_BOOTSTRAP_EXPECTED_VERSION",
            CANONICAL_BOOTSTRAP.version,
        )
        if expected_version == CANONICAL_BOOTSTRAP.version:
            self.assertEqual(CERTIFICATION_BOOTSTRAP_LANES, (CANONICAL_BOOTSTRAP,))
            self.assertEqual(CANONICAL_BOOTSTRAP.version, "5.3.3")
        context = self.browser.new_context()
        response = context.request.get(CANONICAL_BOOTSTRAP.bundle_url(self.base_url))
        self.assertTrue(response.ok)
        self.assertIn(f"Bootstrap v{expected_version}", response.text())
        context.close()

    def test_badge_fixture_proves_the_browser_evidence_pipeline(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/badge.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case, normalize_screenshot=True)

                self.assertEqual(page.locator("h1").count(), 1)
                self.assertEqual(page.locator(".badge").count(), 9)
                self.assertEqual(
                    page.locator(".visually-hidden").inner_text(),
                    "unread notifications",
                )
                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )

                violations = run_axe(page)
                self.assertEqual(
                    violations,
                    [],
                    "axe violations: "
                    + ", ".join(
                        str(violation.get("id", "unknown"))
                        for violation in violations
                    ),
                )

                badge_style = page.locator(".badge").first.evaluate(
                    """
                    element => {
                      const style = getComputedStyle(element);
                      return {
                        animationDuration: style.animationDuration,
                        transitionDuration: style.transitionDuration,
                      };
                    }
                    """
                )
                self.assertEqual(badge_style["animationDuration"], "0s")
                self.assertEqual(badge_style["transitionDuration"], "0s")
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_input_fixture_proves_native_form_control_states(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/input.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                name = page.locator("#certification-input-name")
                search = page.locator("#certification-input-search")
                required = page.locator("#certification-input-required")
                readonly = page.locator("#certification-input-readonly")
                disabled = page.locator("#certification-input-disabled")

                self.assertEqual(page.locator("h1").count(), 1)
                expect(page.locator('label[for="certification-input-name"]')).to_have_text(
                    "Display name"
                )
                expect(name).to_have_attribute(
                    "aria-describedby",
                    "certification-input-name-help",
                )
                expect(page.locator("#certification-input-name-help")).to_have_class(
                    "form-text"
                )
                expect(search).to_have_attribute("type", "search")
                expect(required).to_have_class("form-control is-invalid")
                expect(required.locator("xpath=ancestor::div[1]")).to_have_attribute(
                    "data-invalid",
                    "true",
                )
                expect(required).to_have_attribute("aria-invalid", "true")
                expect(required).to_have_attribute(
                    "aria-describedby",
                    "certification-input-required-help "
                    "certification-input-required-feedback",
                )
                expect(page.locator("#certification-input-required-feedback")).to_be_visible()

                name.focus()
                expect(name).to_be_focused()
                name.fill("Grace Hopper")
                expect(name).to_have_value("Grace Hopper")
                page.keyboard.press("Tab")
                expect(search).to_be_focused()
                search.fill("Ada")
                expect(search).to_have_value("Ada")

                expect(readonly).to_have_attribute("readonly", "")
                readonly.focus()
                expect(readonly).to_be_focused()
                readonly.press("X")
                expect(readonly).to_have_value("eu-central-1")
                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )
                self.assertTrue(
                    required.evaluate("element => element.validity.valueMissing")
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_textarea_fixture_proves_native_multiline_control_states(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/textarea.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                message = page.locator("#certification-textarea-message")
                required = page.locator("#certification-textarea-required")
                readonly = page.locator("#certification-textarea-readonly")
                disabled = page.locator("#certification-textarea-disabled")

                self.assertEqual(page.locator("h1").count(), 1)
                expect(
                    page.locator('label[for="certification-textarea-message"]')
                ).to_have_text("Review notes")
                expect(message).to_have_attribute(
                    "aria-describedby",
                    "certification-textarea-message-help",
                )
                expect(message).to_have_attribute("rows", "4")
                expect(page.locator("#certification-textarea-message-help")).to_have_class(
                    "form-text"
                )
                expect(required).to_have_class("form-control is-invalid")
                expect(required).to_have_attribute("aria-invalid", "true")
                expect(required).to_have_attribute(
                    "aria-describedby",
                    "certification-textarea-required-help "
                    "certification-textarea-required-feedback",
                )
                expect(page.locator("#certification-textarea-required-feedback")).to_be_visible()

                message.focus()
                expect(message).to_be_focused()
                message.fill("First line\nSecond line")
                expect(message).to_have_value("First line\nSecond line")
                page.keyboard.press("Tab")
                expect(required).to_be_focused()
                self.assertTrue(
                    required.evaluate("element => element.validity.valueMissing")
                )

                expect(readonly).to_have_attribute("readonly", "")
                readonly.focus()
                expect(readonly).to_be_focused()
                readonly.press("X")
                expect(readonly).to_have_value("Sync is paused until approval.")
                expect(disabled).to_be_disabled()
                self.assertEqual(
                    disabled.evaluate("element => getComputedStyle(element).resize"),
                    "none",
                )
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_input_group_fixture_proves_bootstrap_grouped_control_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/input-group.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                url_group = page.locator("#certification-input-group-url")
                url_input = page.locator("#certification-input-group-url-input")
                invalid_group = page.locator("#certification-input-group-invalid")
                invalid_input = page.locator("#certification-input-group-token")
                search_input = page.locator("#certification-input-group-search")
                search_button = page.locator("#certification-input-group-search-button")
                textarea = page.locator("#certification-input-group-notes")
                textarea_post = page.locator("#certification-input-group-post")
                readonly = page.locator("#certification-input-group-readonly")
                disabled = page.locator("#certification-input-group-disabled")

                self.assertEqual(page.locator("h1").count(), 1)
                expect(url_group).to_have_class("input-group")
                expect(
                    page.locator('label[for="certification-input-group-url-input"]')
                ).to_have_text("Project URL")
                self.assertFalse(
                    page.locator('label[for="certification-input-group-url-input"]')
                    .evaluate("element => Boolean(element.closest('.input-group'))")
                )
                expect(url_input).to_have_attribute(
                    "aria-describedby",
                    "certification-input-group-url-addon "
                    "certification-input-group-url-help",
                )
                expect(page.locator("#certification-input-group-url-addon")).to_have_class(
                    "input-group-text"
                )
                expect(page.locator("#certification-input-group-url-help")).to_have_class(
                    "field-description form-text"
                )

                expect(invalid_group).to_have_class("input-group has-validation")
                expect(invalid_input).to_have_class("form-control is-invalid")
                expect(invalid_input).to_have_attribute("required", "")
                expect(invalid_input).to_have_attribute("aria-invalid", "true")
                expect(invalid_input).to_have_attribute(
                    "aria-describedby",
                    "certification-input-group-token-addon "
                    "certification-input-group-token-feedback",
                )
                expect(
                    page.locator("#certification-input-group-token-feedback")
                ).to_have_class("field-error invalid-feedback d-block")

                url_input.focus()
                expect(url_input).to_be_focused()
                url_input.fill("release-notes")
                expect(url_input).to_have_value("release-notes")
                page.keyboard.press("Tab")
                expect(invalid_input).to_be_focused()
                self.assertTrue(
                    invalid_input.evaluate("element => element.validity.valueMissing")
                )
                page.keyboard.press("Tab")
                expect(search_input).to_be_focused()
                page.keyboard.press("Tab")
                expect(search_button).to_be_focused()
                expect(search_button).to_have_attribute("type", "button")

                expect(textarea).to_have_attribute("aria-label", "Comment")
                textarea.fill("Grouped text area")
                expect(textarea).to_have_value("Grouped text area")
                expect(textarea_post).to_have_attribute("type", "button")
                expect(readonly).to_have_attribute("readonly", "")
                readonly.focus()
                expect(readonly).to_be_focused()
                readonly.press("X")
                expect(readonly).to_have_value("eu-west-1")
                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_select_fixture_proves_native_select_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/select.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                workspace = page.locator("#certification-select-workspace")
                grouped = page.locator("#certification-select-queue")
                invalid = page.locator("#certification-select-invalid")
                multiple = page.locator("#certification-select-teams")
                sized = page.locator("#certification-select-priority")
                disabled = page.locator("#certification-select-disabled")

                self.assertEqual(page.locator("h1").count(), 1)
                expect(
                    page.locator('label[for="certification-select-workspace"]')
                ).to_have_text("Workspace")
                expect(workspace).to_have_class("form-select")
                expect(workspace).to_have_attribute(
                    "aria-describedby",
                    "certification-select-workspace-help",
                )
                expect(workspace).to_have_attribute("data-selected", "ops")
                self.assertEqual(workspace.input_value(), "ops")
                workspace.focus()
                expect(workspace).to_be_focused()
                workspace.select_option("design")
                self.assertEqual(workspace.input_value(), "design")

                expect(grouped.locator('optgroup[label="Primary queues"]')).to_have_count(1)
                expect(
                    grouped.locator('optgroup[label="Archive queues"]')
                ).to_have_attribute("disabled", "")
                grouped.select_option("incident")
                self.assertEqual(grouped.input_value(), "incident")

                expect(invalid).to_have_class("form-select is-invalid")
                expect(invalid).to_have_attribute("required", "")
                expect(invalid).to_have_attribute("aria-invalid", "true")
                expect(invalid).to_have_attribute(
                    "aria-describedby",
                    "certification-select-invalid-help "
                    "certification-select-invalid-feedback",
                )
                expect(
                    page.locator("#certification-select-invalid-feedback")
                ).to_have_class("invalid-feedback")
                invalid.focus()
                expect(invalid).to_be_focused()
                self.assertTrue(
                    invalid.evaluate("element => element.validity.valueMissing")
                )

                expect(multiple).to_have_attribute("multiple", "")
                expect(multiple).to_have_attribute("size", "5")
                multiple.select_option(["platform", "security"])
                self.assertEqual(
                    multiple.evaluate(
                        """
                        element => Array.from(element.selectedOptions)
                          .map(option => option.value)
                        """
                    ),
                    ["platform", "security"],
                )

                expect(sized).to_have_class("form-select form-select-lg")
                expect(sized).to_have_attribute("size", "4")
                self.assertEqual(
                    sized.evaluate("element => getComputedStyle(element).backgroundImage"),
                    "none",
                )
                sized.select_option("high")
                self.assertEqual(sized.input_value(), "high")

                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_checkbox_fixture_proves_native_form_check_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/checkbox.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                default = page.locator("#certification-checkbox-default")
                default_label = page.locator(
                    'label[for="certification-checkbox-default"]'
                )
                checked = page.locator("#certification-checkbox-checked")
                described = page.locator("#certification-checkbox-described")
                standalone = page.locator("#certification-checkbox-standalone")
                invalid = page.locator("#certification-checkbox-invalid")
                disabled = page.locator("#certification-checkbox-disabled")
                disabled_label = page.locator(
                    'label[for="certification-checkbox-disabled"]'
                )

                self.assertEqual(page.locator("h1").count(), 1)
                expect(default.locator("xpath=ancestor::div[1]")).to_have_class(
                    "form-check"
                )
                expect(default).to_have_class("form-check-input")
                expect(default).to_have_attribute("type", "checkbox")
                expect(default_label).to_have_class("form-check-label")
                self.assertTrue(
                    default.evaluate(
                        """
                        element => element.nextElementSibling?.matches(
                          'label.form-check-label[for="certification-checkbox-default"]'
                        )
                        """
                    )
                )
                default_label.click()
                expect(default).to_be_checked()
                default.press("Space")
                self.assertFalse(default.is_checked())

                expect(checked).to_be_checked()
                checked.focus()
                expect(checked).to_be_focused()
                checked.press("Space")
                self.assertFalse(checked.is_checked())

                expect(described).to_have_attribute(
                    "aria-describedby",
                    "certification-checkbox-described-description",
                )
                expect(
                    page.locator("#certification-checkbox-described-description")
                ).to_have_class("form-text")

                expect(standalone).to_have_attribute(
                    "aria-label",
                    "Accept audit export",
                )
                self.assertEqual(
                    standalone.locator(
                        'xpath=following-sibling::label[contains(@class, "form-check-label")]'
                    ).count(),
                    0,
                )

                expect(invalid).to_have_class("form-check-input is-invalid")
                expect(invalid).to_have_attribute("aria-invalid", "true")
                expect(invalid).to_have_attribute(
                    "aria-describedby",
                    "certification-checkbox-invalid-feedback",
                )
                expect(
                    page.locator("#certification-checkbox-invalid-feedback")
                ).to_have_class("invalid-feedback")

                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )
                self.assertLess(
                    disabled_label.evaluate(
                        "element => Number(getComputedStyle(element).opacity)"
                    ),
                    default_label.evaluate(
                        "element => Number(getComputedStyle(element).opacity)"
                    ),
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_radio_group_fixture_proves_native_form_check_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/radio-group.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                default = page.locator("#certification-radio-email")
                default_label = page.locator(
                    'label[for="certification-radio-email"]'
                )
                alternate = page.locator("#certification-radio-sms")
                described = page.locator("#certification-radio-drive")
                described_alternate = page.locator("#certification-radio-sftp")
                invalid = page.locator("#certification-radio-invalid-admin")
                disabled = page.locator("#certification-radio-disabled-mobile")
                disabled_label = page.locator(
                    'label[for="certification-radio-disabled-mobile"]'
                )

                self.assertEqual(page.locator("h1").count(), 1)
                expect(default.locator("xpath=ancestor::fieldset[1]")).to_have_class(
                    "radio-group"
                )
                expect(default.locator("xpath=ancestor::fieldset[1]/legend")).to_have_class(
                    "form-label"
                )
                expect(default.locator("xpath=ancestor::div[1]")).to_have_class(
                    "form-check"
                )
                expect(default).to_have_class("form-check-input")
                expect(default).to_have_attribute("type", "radio")
                expect(default).to_have_attribute("name", "certification-channel")
                expect(alternate).to_have_attribute("name", "certification-channel")
                expect(default_label).to_have_class("form-check-label")
                expect(default).to_be_checked()
                default_label.click()
                expect(default).to_be_checked()
                alternate.check()
                expect(alternate).to_be_checked()
                self.assertFalse(default.is_checked())

                described.check()
                expect(described).to_be_checked()
                self.assertFalse(described_alternate.is_checked())
                expect(described).to_have_attribute(
                    "aria-describedby",
                    "certification-radio-drive-description",
                )
                expect(
                    page.locator("#certification-radio-drive-description")
                ).to_have_class("form-text")

                expect(invalid).to_have_class("form-check-input is-invalid")
                expect(invalid).to_have_attribute("required", "")
                expect(invalid).to_have_attribute("aria-invalid", "true")
                expect(invalid).to_have_attribute(
                    "aria-describedby",
                    "certification-radio-invalid-feedback",
                )
                expect(
                    page.locator("#certification-radio-invalid-feedback")
                ).to_have_class("invalid-feedback d-block")
                self.assertTrue(
                    invalid.evaluate("element => element.validity.valueMissing")
                )

                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )
                self.assertLess(
                    disabled_label.evaluate(
                        "element => Number(getComputedStyle(element).opacity)"
                    ),
                    default_label.evaluate(
                        "element => Number(getComputedStyle(element).opacity)"
                    ),
                )

                default.check()
                expect(default).to_be_checked()
                default.focus()
                expect(default).to_be_focused()
                page.keyboard.press("ArrowDown")
                expect(alternate).to_be_checked()

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_switch_fixture_proves_native_form_switch_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/switch.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                default = page.locator("#certification-switch-default")
                default_label = page.locator(
                    'label[for="certification-switch-default"]'
                )
                checked = page.locator("#certification-switch-checked")
                described = page.locator("#certification-switch-described")
                standalone = page.locator("#certification-switch-standalone")
                invalid = page.locator("#certification-switch-invalid")
                disabled = page.locator("#certification-switch-disabled")
                disabled_label = page.locator(
                    'label[for="certification-switch-disabled"]'
                )

                self.assertEqual(page.locator("h1").count(), 1)
                expect(default.locator("xpath=ancestor::div[1]")).to_have_class(
                    "form-check form-switch"
                )
                expect(default).to_have_class("form-check-input")
                expect(default).to_have_attribute("type", "checkbox")
                expect(default).to_have_attribute("role", "switch")
                expect(default_label).to_have_class("form-check-label")
                default_label.click()
                expect(default).to_be_checked()
                default.press("Space")
                self.assertFalse(default.is_checked())

                expect(checked).to_be_checked()
                checked.focus()
                expect(checked).to_be_focused()
                checked.press("Space")
                self.assertFalse(checked.is_checked())

                expect(described).to_have_attribute(
                    "aria-describedby",
                    "certification-switch-described-description",
                )
                expect(
                    page.locator("#certification-switch-described-description")
                ).to_have_class("form-text")

                expect(standalone).to_have_attribute(
                    "aria-label",
                    "Enable audit mode",
                )
                self.assertEqual(
                    standalone.locator(
                        'xpath=following-sibling::label[contains(@class, "form-check-label")]'
                    ).count(),
                    0,
                )

                expect(invalid).to_have_class("form-check-input is-invalid")
                expect(invalid).to_have_attribute("role", "switch")
                expect(invalid).to_have_attribute("aria-invalid", "true")

                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )
                self.assertLess(
                    disabled_label.evaluate(
                        "element => Number(getComputedStyle(element).opacity)"
                    ),
                    default_label.evaluate(
                        "element => Number(getComputedStyle(element).opacity)"
                    ),
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_field_fixture_proves_composition_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/field.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                form = page.locator("#certification-field-form")
                project = page.locator("#certification-field-project")
                project_label = page.locator(
                    'label[for="certification-field-project"]'
                )
                project_help = page.locator("#certification-field-project-help")
                slug = page.locator("#certification-field-slug")
                slug_feedback = page.locator("#certification-field-slug-feedback")
                disabled = page.locator("#certification-field-disabled")
                switch = page.locator("#certification-field-notifications")

                self.assertEqual(page.locator("h1").count(), 1)
                expect(form).to_have_class("field-form needs-validation")
                expect(form).to_have_attribute("novalidate", "")
                expect(form).to_have_css("display", "flex")
                self.assertEqual(
                    form.evaluate("element => getComputedStyle(element).rowGap"),
                    "20px",
                )
                expect(project.locator("xpath=ancestor::div[1]")).to_have_class(
                    "field"
                )
                expect(project_label).to_have_class("form-label")
                expect(project).to_have_class("form-control")
                expect(project).to_have_attribute(
                    "aria-describedby",
                    "certification-field-project-help",
                )
                expect(project_help).to_have_class("field-description form-text")
                project.fill("Moo UI")
                expect(project).to_have_value("Moo UI")

                expect(slug).to_have_class("form-control is-invalid")
                expect(slug.locator("xpath=ancestor::div[1]")).to_have_attribute(
                    "data-invalid",
                    "true",
                )
                expect(slug).to_have_attribute("required", "")
                expect(slug).to_have_attribute("aria-invalid", "true")
                expect(slug).to_have_attribute(
                    "aria-describedby",
                    "certification-field-slug-feedback",
                )
                expect(slug_feedback).to_have_class("field-error invalid-feedback")
                expect(slug_feedback).to_be_visible()
                self.assertTrue(slug.evaluate("element => element.validity.valueMissing"))

                expect(page.locator("#certification-fieldset")).to_have_class(
                    "field-fieldset"
                )
                expect(page.locator("#certification-fieldset > legend")).to_have_class(
                    "field-legend"
                )
                expect(page.locator("#certification-fieldset-description")).to_have_class(
                    "field-description form-text"
                )
                expect(page.locator("#certification-field-group")).to_have_class(
                    "field-group"
                )
                expect(switch.locator("xpath=ancestor::div[1]")).to_have_class(
                    "form-check form-switch"
                )
                expect(switch).to_have_attribute("role", "switch")
                switch.press("Space")
                expect(switch).to_be_checked()

                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_form_fixture_proves_static_composite_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/form.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                form = page.locator("#certification-form")
                name = page.locator("#certification-form-name")
                name_feedback = page.locator("#certification-form-name-feedback")
                queue = page.locator("#certification-form-queue")
                notes = page.locator("#certification-form-notes")
                security = page.locator("#certification-form-security")
                backups = page.locator("#certification-form-backups")
                policy_viewer = page.locator("#certification-form-policy-viewer")
                policy_editor = page.locator("#certification-form-policy-editor")
                digest = page.locator("#certification-form-digest")

                self.assertEqual(page.locator("h1").count(), 1)
                expect(form).to_have_class("field-form needs-validation")
                expect(form).to_have_attribute("novalidate", "")
                expect(form).to_have_css("display", "flex")
                self.assertEqual(
                    form.evaluate("element => getComputedStyle(element).rowGap"),
                    "20px",
                )
                self.assertEqual(page.locator("fieldset").count(), 3)
                expect(page.locator("#certification-form-profile")).to_have_class(
                    "field-fieldset"
                )
                expect(page.locator("#certification-form-checks")).to_have_class(
                    "field-fieldset"
                )
                expect(page.locator("#certification-form-policy")).to_have_class(
                    "field-fieldset"
                )

                expect(name.locator("xpath=ancestor::div[1]")).to_have_class("field")
                expect(name).to_have_class("form-control is-invalid")
                expect(name).to_have_attribute("required", "")
                expect(name).to_have_attribute("aria-invalid", "true")
                expect(name).to_have_attribute(
                    "aria-describedby",
                    "certification-form-name-feedback",
                )
                expect(name_feedback).to_have_class("field-error invalid-feedback")
                name.fill("Moo UI release")
                expect(name).to_have_value("Moo UI release")

                expect(queue).to_have_class("form-select")
                expect(queue).to_have_value("ops")
                queue.select_option("support")
                expect(queue).to_have_value("support")

                expect(notes).to_have_class("form-control")
                notes.fill("Validated on local devices.")
                expect(notes).to_have_value("Validated on local devices.")

                expect(security).to_be_checked()
                expect(backups).not_to_be_checked()
                backups.check()
                expect(backups).to_be_checked()

                expect(policy_viewer).to_be_checked()
                policy_editor.check()
                expect(policy_editor).to_be_checked()
                expect(policy_viewer).not_to_be_checked()

                expect(digest).to_have_attribute("role", "switch")
                digest.press("Space")
                expect(digest).to_be_checked()

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_button_fixture_proves_variant_size_and_state_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/button.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                self.assertEqual(page.locator("h1").count(), 1)
                self.assertEqual(page.locator(".btn").count(), 12)

                icon_only = page.locator("#certification-button-icon-only")
                expect(icon_only).to_have_class("btn btn-ghost btn-icon")
                expect(icon_only).to_have_attribute("aria-label", "Open menu")
                self.assertEqual(icon_only.inner_text().strip(), "")

                disabled = page.locator("#certification-button-disabled")
                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                toggle = page.locator("#certification-button-toggle")
                expect(toggle).to_have_attribute("aria-pressed", "false")
                toggle.click()
                expect(toggle).to_have_attribute("aria-pressed", "true")
                toggle.press("Enter")
                expect(toggle).to_have_attribute("aria-pressed", "false")
                self.assertTrue(
                    toggle.evaluate("element => document.activeElement === element")
                )

                disabled_link = page.locator("#certification-button-disabled-link")
                expect(disabled_link).to_have_attribute("aria-disabled", "true")
                expect(disabled_link).to_have_attribute("tabindex", "-1")
                self.assertFalse(disabled_link.evaluate("element => element.hasAttribute('href')"))

                link = page.locator("#certification-button-link")
                link.focus()
                expect(link).to_be_focused()

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_button_group_fixture_proves_grouping_and_layout_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/button-group.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                self.assertEqual(page.locator("h1").count(), 1)

                toolbar = page.locator("#certification-button-group-toolbar")
                expect(toolbar).to_have_attribute("role", "toolbar")
                expect(toolbar).to_have_attribute("aria-label", "Ticket actions")
                self.assertEqual(toolbar.locator(".btn-group").count(), 2)
                for nested_group in toolbar.locator(".btn-group").all():
                    expect(nested_group).to_have_attribute("role", "group")

                vertical = page.locator("#certification-button-group-vertical")
                expect(vertical).to_have_class("btn-group-vertical")
                expect(vertical).to_have_attribute("role", "group")

                small_group = page.locator("#certification-button-group-sm")
                expect(small_group).to_have_class("btn-group btn-group-sm")
                disabled = page.locator("#certification-button-group-disabled")
                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                archive = page.locator("#certification-button-group-archive")
                report = page.locator("#certification-button-group-report")
                archive.focus()
                expect(archive).to_be_focused()
                archive.press("Tab")
                expect(report).to_be_focused()

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_card_fixture_proves_section_composition_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/card.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                self.assertEqual(page.locator("h1").count(), 1)
                self.assertEqual(page.locator(".card").count(), 4)

                content_only = page.locator("#certification-card-content-only")
                self.assertEqual(content_only.locator(".card-header").count(), 0)
                expect(content_only.locator(".card-body")).to_have_text("Body preview")

                header = page.locator("#certification-card-header")
                expect(header.locator(".card-title")).to_have_text("Incident status")
                expect(header.locator(".card-subtitle")).to_have_text(
                    "Validation summary is shown per environment."
                )

                footer = page.locator("#certification-card-footer")
                expect(footer.locator(".card-footer")).to_have_class(
                    "card-footer justify-content-end d-flex gap-2"
                )
                footer_button = page.locator("#certification-card-footer-button")
                footer_button.focus()
                expect(footer_button).to_be_focused()

                rtl_card = page.locator("#certification-card-rtl")
                expect(rtl_card).to_have_attribute("dir", "rtl")
                expect(rtl_card.locator(".card-title")).to_have_text("مراجعة")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_typography_fixture_proves_variant_element_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/typography.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                page_title = page.locator("#certification-typography-page-title")
                self.assertEqual(page_title.evaluate("element => element.tagName"), "H1")
                expect(page_title).to_have_class("fw-semibold")

                page_description = page.locator("#certification-typography-page-description")
                self.assertEqual(page_description.evaluate("element => element.tagName"), "P")
                expect(page_description).to_have_class("moo-page-description text-body-secondary mb-0")

                section_title = page.locator("#certification-typography-section-title")
                self.assertEqual(section_title.evaluate("element => element.tagName"), "H2")
                expect(section_title).to_have_class("h3")

                example_title = page.locator("#certification-typography-example-title")
                self.assertEqual(example_title.evaluate("element => element.tagName"), "H2")
                expect(example_title).to_have_class("h4")

                muted = page.locator("#certification-typography-muted")
                self.assertEqual(muted.evaluate("element => element.tagName"), "SPAN")
                expect(muted).to_have_class("text-body-secondary")

                section_label = page.locator("#certification-typography-section-label")
                self.assertEqual(section_label.evaluate("element => element.tagName"), "SPAN")
                expect(section_label).to_have_class("small fw-semibold")

                inline_code = page.locator("#certification-typography-inline-code")
                self.assertEqual(inline_code.evaluate("element => element.tagName"), "CODE")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_kbd_fixture_proves_native_element_contract(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/kbd.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                self.assertEqual(page.locator("kbd").count(), 3)
                first = page.locator("#certification-kbd-first")
                second = page.locator("#certification-kbd-second")
                single = page.locator("#certification-kbd-single")
                self.assertEqual(first.evaluate("element => element.tagName"), "KBD")
                expect(first).to_have_text("Ctrl")
                expect(second).to_have_text("K")
                expect(single).to_have_text("Esc")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_avatar_fixture_proves_fallback_size_and_badge_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/avatar.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                self.assertEqual(page.locator(".avatar").count(), 6)

                image_avatar = page.locator("#certification-avatar-image")
                expect(image_avatar).to_have_class("avatar avatar--has-image")
                expect(image_avatar.locator("img")).to_have_attribute("alt", "Grace Hopper")

                initials = page.locator("#certification-avatar-initials")
                expect(initials).to_have_attribute("role", "img")
                expect(initials).to_have_attribute("aria-label", "Ada Lovelace")
                expect(initials.locator(".avatar-fallback")).to_have_text("AL")

                small = page.locator("#certification-avatar-sm")
                default = page.locator("#certification-avatar-default")
                large = page.locator("#certification-avatar-lg")
                expect(small).to_have_class("avatar avatar-sm")
                expect(large).to_have_class("avatar avatar-lg")
                small_box = small.bounding_box()
                default_box = default.bounding_box()
                large_box = large.bounding_box()
                self.assertLess(small_box["width"], default_box["width"])
                self.assertLess(default_box["width"], large_box["width"])

                badge_dot = page.locator("#certification-avatar-badge-dot")
                expect(badge_dot.locator(".avatar-badge")).to_have_class(
                    "avatar-badge avatar-badge--dot"
                )
                expect(badge_dot.locator(".avatar-badge")).to_have_attribute(
                    "aria-label", "Online"
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_navigation_fixture_proves_style_state_and_keyboard_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/navigation.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                pills = page.locator("#certification-navigation-pills ul")
                expect(pills).to_have_class("nav nav-pills")

                overview = page.locator("#certification-navigation-overview")
                expect(overview).to_have_class("nav-link active")
                expect(overview).to_have_attribute("aria-current", "page")

                billing = page.locator("#certification-navigation-billing")
                expect(billing).to_have_attribute("aria-disabled", "true")
                expect(billing).to_have_attribute("tabindex", "-1")
                self.assertFalse(billing.evaluate("element => element.hasAttribute('href')"))

                members = page.locator("#certification-navigation-members")
                overview.focus()
                expect(overview).to_be_focused()
                overview.press("Tab")
                expect(members).to_be_focused()

                underline = page.locator("#certification-navigation-underline ul")
                expect(underline).to_have_class("nav nav-underline flex-column gap-1")

                notifications = page.locator("#certification-navigation-notifications")
                expect(notifications.locator(".badge")).to_have_text("3")
                expect(notifications.locator(".badge")).to_have_class(
                    "badge text-bg-secondary rounded-pill ms-auto"
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_separator_fixture_proves_orientation_and_decorative_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/separator.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                horizontal = page.locator("#certification-separator-horizontal")
                self.assertEqual(horizontal.evaluate("element => element.tagName"), "HR")
                expect(horizontal).to_have_attribute("aria-hidden", "true")

                vertical = page.locator("#certification-separator-vertical")
                expect(vertical).to_have_class("vr")
                expect(vertical).to_have_attribute("aria-hidden", "true")
                self.assertEqual(vertical.get_attribute("role"), None)

                semantic = page.locator("#certification-separator-semantic")
                expect(semantic).to_have_attribute("role", "separator")
                expect(semantic).to_have_attribute("aria-orientation", "vertical")
                self.assertEqual(semantic.get_attribute("aria-hidden"), None)

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_skeleton_fixture_proves_placeholder_shape_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/skeleton.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                self.assertEqual(page.locator(".skeleton").count(), 3)
                for locator_id in (
                    "#certification-skeleton-text",
                    "#certification-skeleton-avatar",
                    "#certification-skeleton-block",
                ):
                    skeleton = page.locator(locator_id)
                    expect(skeleton).to_have_class("skeleton placeholder-glow")
                    expect(skeleton).to_have_attribute("aria-hidden", "true")
                    expect(skeleton.locator(".placeholder")).to_have_count(1)

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                skeleton_style = page.locator(".skeleton").first.evaluate(
                    """
                    element => {
                      const style = getComputedStyle(element);
                      return {
                        animationDuration: style.animationDuration,
                        transitionDuration: style.transitionDuration,
                      };
                    }
                    """
                )
                self.assertEqual(skeleton_style["animationDuration"], "0s")
                self.assertEqual(skeleton_style["transitionDuration"], "0s")
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_close_button_fixture_proves_state_and_dismiss_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/close-button.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                default = page.locator("#certification-close-button-default")
                expect(default).to_have_class("btn-close")
                expect(default).to_have_attribute("aria-label", "Close")
                default.focus()
                expect(default).to_be_focused()

                custom_label = page.locator("#certification-close-button-custom-label")
                expect(custom_label).to_have_attribute(
                    "aria-label", "Dismiss notification"
                )

                disabled = page.locator("#certification-close-button-disabled")
                expect(disabled).to_be_disabled()
                disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    disabled.evaluate("element => document.activeElement === element")
                )

                alert = page.locator("#certification-close-button-alert")
                dismiss = page.locator("#certification-close-button-dismiss")
                expect(dismiss).to_have_attribute("data-bs-dismiss", "alert")
                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const alert = document.querySelector("#certification-close-button-alert");
                      alert.addEventListener("closed.bs.alert", resolve, { once: true });
                      document.querySelector("#certification-close-button-dismiss").click();
                    })
                    """
                )
                self.assertEqual(alert.count(), 0)

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_breadcrumb_fixture_proves_trail_and_dropdown_segment_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/breadcrumb.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                basic_nav = page.locator("#certification-breadcrumb-basic")
                expect(basic_nav).to_have_attribute("aria-label", "breadcrumb")
                expect(basic_nav.locator("ol")).to_have_class("breadcrumb")
                self.assertEqual(basic_nav.locator(".breadcrumb-item").count(), 4)

                active = page.locator("#certification-breadcrumb-active")
                expect(active).to_have_class("breadcrumb-item active")
                expect(active).to_have_attribute("aria-current", "page")

                ellipsis = basic_nav.locator(".breadcrumb-ellipsis")
                expect(ellipsis.locator(".visually-hidden")).to_have_text("More")

                workspace = page.locator("#certification-breadcrumb-workspace")
                projects = page.locator("#certification-breadcrumb-projects")
                workspace.focus()
                expect(workspace).to_be_focused()
                workspace.press("Tab")
                expect(projects).to_be_focused()

                trigger = page.locator("#certification-breadcrumb-dropdown-trigger")
                expect(trigger).to_have_attribute("aria-expanded", "false")
                trigger.click()
                expect(trigger).to_have_attribute("aria-expanded", "true")
                menu = page.locator("#certification-breadcrumb-dropdown-nav .dropdown-menu")
                expect(menu).to_be_visible()
                self.assertEqual(menu.locator(".dropdown-item").count(), 2)
                trigger.press("Escape")
                expect(trigger).to_have_attribute("aria-expanded", "false")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_pagination_fixture_proves_nav_state_and_size_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/pagination.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                default_nav = page.locator("#certification-pagination-default")
                expect(default_nav).to_have_attribute("aria-label", "Search results")
                expect(default_nav.locator("ul")).to_have_class("pagination")
                self.assertEqual(default_nav.locator(".page-item").count(), 6)

                page_2 = page.locator("#certification-pagination-page-2")
                expect(page_2.locator("xpath=..")).to_have_class("page-item active")
                expect(page_2.locator("xpath=..")).to_have_attribute("aria-current", "page")
                metrics = page_2.evaluate(
                    """
                    element => {
                      const read = target => {
                        const style = getComputedStyle(target);
                        const rect = target.getBoundingClientRect();
                        return {
                          width: rect.width,
                          height: rect.height,
                          borderRadius: style.borderRadius,
                          fontWeight: style.fontWeight,
                          lineHeight: style.lineHeight,
                          backgroundColor: style.backgroundColor,
                          borderColor: style.borderColor,
                        };
                      };
                      return {
                        active: read(element),
                        adjacent: read(document.querySelector("#certification-pagination-page-3")),
                        ellipsis: read(
                          document.querySelector(
                            "#certification-pagination-default .page-item.disabled .page-link"
                          )
                        ),
                        prev: read(document.querySelector("#certification-pagination-prev")),
                      };
                    }
                    """
                )
                for key in ("active", "adjacent", "ellipsis"):
                    with self.subTest(case=case.name, item=key):
                        self.assertAlmostEqual(metrics[key]["width"], 32, delta=1)
                        self.assertAlmostEqual(metrics[key]["height"], 32, delta=1)
                        self.assertEqual(metrics[key]["borderRadius"], "10px")
                        self.assertEqual(metrics[key]["fontWeight"], "500")
                        self.assertEqual(metrics[key]["lineHeight"], "20px")
                self.assertNotEqual(metrics["active"]["backgroundColor"], "rgba(0, 0, 0, 0)")
                self.assertNotEqual(metrics["active"]["borderColor"], "rgba(0, 0, 0, 0)")
                self.assertEqual(metrics["ellipsis"]["backgroundColor"], "rgba(0, 0, 0, 0)")
                if case.is_mobile:
                    self.assertAlmostEqual(metrics["prev"]["width"], 32, delta=1)

                prev = page.locator("#certification-pagination-prev")
                page_1 = page.locator("#certification-pagination-page-1")
                expect(prev).to_have_attribute("aria-label", "Previous")
                prev.focus()
                expect(prev).to_be_focused()
                prev.press("Tab")
                expect(page_1).to_be_focused()

                small_nav = page.locator("#certification-pagination-small")
                expect(small_nav.locator("ul")).to_have_class("pagination pagination-sm")
                small_prev_disabled = page.locator(
                    "#certification-pagination-small-prev-disabled"
                )
                self.assertEqual(small_prev_disabled.evaluate("element => element.tagName"), "SPAN")
                expect(small_prev_disabled).to_have_attribute("role", "link")
                expect(small_prev_disabled).to_have_attribute("aria-disabled", "true")
                small_prev_disabled.evaluate("element => element.focus()")
                self.assertFalse(
                    small_prev_disabled.evaluate(
                        "element => document.activeElement === element"
                    )
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_progress_fixture_proves_value_bounds_and_label_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/progress.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                basic = page.locator("#certification-progress-basic")
                expect(basic).to_have_attribute("role", "progressbar")
                expect(basic).to_have_attribute("aria-valuenow", "40")
                expect(basic).to_have_attribute("aria-valuemin", "0")
                expect(basic).to_have_attribute("aria-valuemax", "100")
                self.assertGreater(
                    basic.locator(".progress-bar").evaluate(
                        "element => element.getBoundingClientRect().width"
                    ),
                    0,
                )

                labeled = page.locator("#certification-progress-labeled")
                expect(labeled).to_have_attribute("aria-valuenow", "75")
                expect(page.locator("#certification-progress-labeled-percent")).to_have_text("75%")

                empty = page.locator("#certification-progress-empty")
                expect(empty).to_have_attribute("aria-valuenow", "0")
                complete = page.locator("#certification-progress-complete")
                expect(complete).to_have_attribute("aria-valuenow", "100")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_table_fixture_proves_semantic_structure_and_row_actions_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/table.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                table = page.locator("#certification-table")
                expect(table).to_have_class("table table-striped table-hover")
                expect(table.locator("caption")).to_have_text(
                    "Recent deployments across environments"
                )
                self.assertEqual(table.locator("thead th[scope='col']").count(), 4)

                production_row = page.locator("#certification-table-row-production")
                expect(production_row.locator("th[scope='row']")).to_have_text("Production")
                expect(production_row.locator("td").nth(1)).to_have_class("text-end")

                expect(table.locator("tfoot th[scope='row']")).to_have_text("Total")

                trigger = page.locator("#certification-table-row-actions-trigger")
                expect(trigger).to_have_attribute("aria-expanded", "false")
                trigger.click()
                expect(trigger).to_have_attribute("aria-expanded", "true")
                menu = production_row.locator(".dropdown-menu")
                expect(menu).to_be_visible()
                self.assertEqual(menu.locator(".dropdown-item").count(), 2)
                trigger.press("Escape")
                expect(trigger).to_have_attribute("aria-expanded", "false")
                expect(trigger).to_be_focused()

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_spinner_fixture_proves_status_role_and_size_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/spinner.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                default = page.locator("#certification-spinner-default")
                expect(default).to_have_attribute("role", "status")
                expect(default.locator(".visually-hidden")).to_have_text("Loading")

                small = page.locator("#certification-spinner-small")
                expect(small).to_have_class("spinner spinner-sm")
                expect(small.locator(".visually-hidden")).to_have_text("Saving changes")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                spinner_style = page.locator(".spinner").first.evaluate(
                    """
                    element => {
                      const style = getComputedStyle(element);
                      return {
                        animationDuration: style.animationDuration,
                        transitionDuration: style.transitionDuration,
                      };
                    }
                    """
                )
                self.assertEqual(spinner_style["animationDuration"], "0s")
                self.assertEqual(spinner_style["transitionDuration"], "0s")
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


    def test_dropdown_menu_fixture_proves_data_api_keyboard_and_auto_close(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/dropdown-menu.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                trigger = page.locator("#certification-dropdown-trigger")
                menu = trigger.locator("xpath=following-sibling::ul[1]")
                first_item = page.locator("#certification-dropdown-first-item")
                disabled_item = page.locator("#certification-dropdown-disabled-item")
                self.assertEqual(trigger.get_attribute("aria-expanded"), "false")
                self.assertFalse(menu.evaluate("element => element.classList.contains('show')"))
                expect(disabled_item).to_have_attribute("aria-disabled", "true")
                expect(disabled_item).to_have_attribute("tabindex", "-1")

                trigger.click()
                expect(trigger).to_have_attribute("aria-expanded", "true")
                self.assertTrue(menu.evaluate("element => element.classList.contains('show')"))

                page.keyboard.press("ArrowDown")
                self.assertTrue(
                    first_item.evaluate("element => document.activeElement === element")
                )

                page.keyboard.press("Escape")
                expect(trigger).to_have_attribute("aria-expanded", "false")
                self.assertTrue(trigger.evaluate("element => document.activeElement === element"))

                # data-bs-auto-close="outside" means the opposite of its
                # name suggests: an outside click *does* close the menu
                # (Bootstrap's default "true" behavior already covers that);
                # what "outside" actually suppresses is closing on an
                # *inside* click, which the outside item's own click below
                # proves by leaving the menu open.
                outside_trigger = page.locator("#certification-dropdown-outside-trigger")
                outside_target = page.locator("#certification-outside-target")
                outside_item = page.locator("#certification-dropdown-outside-item")
                outside_trigger.click()
                expect(outside_trigger).to_have_attribute("aria-expanded", "true")
                outside_item.click()
                expect(outside_trigger).to_have_attribute("aria-expanded", "true")
                outside_target.click()
                expect(outside_trigger).to_have_attribute("aria-expanded", "false")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


    def test_menubar_fixture_proves_grouped_dropdown_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/menubar.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                menubar = page.locator("#certification-menubar")
                file_trigger = page.locator("#certification-menubar-file")
                edit_trigger = page.locator("#certification-menubar-edit")
                first_file_item = page.locator("#certification-menubar-new-document")
                edit_menu = edit_trigger.locator("xpath=following-sibling::ul[1]")
                checkbox_trigger = page.locator("#certification-menubar-view")
                checkbox_menu = checkbox_trigger.locator("xpath=following-sibling::ul[1]")
                sidebar_toggle = page.locator("#certification-menubar-view-sidebar")
                compact_toggle = page.locator("#certification-menubar-view-compact")
                outside_target = page.locator("#certification-menubar-outside-target")

                expect(menubar).to_have_attribute("role", "group")
                expect(menubar).to_have_attribute("aria-label", "Document actions")
                self.assertEqual(menubar.locator('[role="menubar"], [role="menuitem"]').count(), 0)

                file_trigger.click()
                expect(file_trigger).to_have_attribute("aria-expanded", "true")
                expect(file_trigger.locator("xpath=following-sibling::ul[1]")).to_have_class(
                    "dropdown-menu show"
                )
                page.keyboard.press("ArrowDown")
                self.assertTrue(
                    first_file_item.evaluate("element => document.activeElement === element")
                )

                edit_trigger.click()
                expect(file_trigger).to_have_attribute("aria-expanded", "false")
                expect(edit_trigger).to_have_attribute("aria-expanded", "true")
                expect(edit_menu).to_have_class("dropdown-menu show")

                page.keyboard.press("Escape")
                expect(edit_trigger).to_have_attribute("aria-expanded", "false")
                self.assertTrue(
                    edit_trigger.evaluate("element => document.activeElement === element")
                )

                checkbox_trigger.click()
                expect(checkbox_trigger).to_have_attribute("aria-expanded", "true")
                page.keyboard.press("ArrowDown")
                self.assertEqual(
                    page.evaluate(
                        """
                        () => {
                          const active = document.activeElement;
                          if (!active) {
                            return "";
                          }
                          const ownText = active.textContent?.trim();
                          if (ownText) {
                            return ownText;
                          }
                          return document
                            .querySelector(`label[for="${active.id}"]`)
                            ?.textContent
                            .trim() || "";
                        }
                        """
                    ),
                    "Sidebar",
                )
                page.keyboard.press("ArrowDown")
                self.assertEqual(
                    page.evaluate(
                        """
                        () => {
                          const active = document.activeElement;
                          if (!active) {
                            return "";
                          }
                          const ownText = active.textContent?.trim();
                          if (ownText) {
                            return ownText;
                          }
                          return document
                            .querySelector(`label[for="${active.id}"]`)
                            ?.textContent
                            .trim() || "";
                        }
                        """
                    ),
                    "Compact mode",
                )
                expect(compact_toggle).to_have_attribute("aria-pressed", "false")
                page.keyboard.press("Space")
                expect(compact_toggle).to_have_attribute("aria-pressed", "true")
                page.keyboard.press("Enter")
                expect(compact_toggle).to_have_attribute("aria-pressed", "false")
                expect(sidebar_toggle).to_have_attribute("aria-pressed", "true")
                sidebar_toggle.click()
                expect(sidebar_toggle).to_have_attribute("aria-pressed", "false")
                expect(sidebar_toggle).not_to_have_class(re.compile(r"\bactive\b"))
                expect(compact_toggle).to_have_attribute("aria-pressed", "false")
                expect(checkbox_trigger).to_have_attribute("aria-expanded", "true")
                expect(checkbox_menu).to_have_class("dropdown-menu show")
                outside_target.click()
                expect(checkbox_trigger).to_have_attribute("aria-expanded", "false")

                self.assertTrue(
                    file_trigger.evaluate(
                        """
                        element => bootstrap.Dropdown.getOrCreateInstance(element)
                          === bootstrap.Dropdown.getInstance(element)
                        """
                    )
                )
                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


    def test_alert_fixture_proves_role_dismissal_and_variant_contracts(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/alert.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                dismissible = page.locator("#certification-alert-dismissible")
                destructive = page.locator("#certification-alert-destructive")
                expect(dismissible).to_have_attribute("role", "alert")
                expect(destructive).to_have_attribute("role", "alert")
                expect(destructive).to_have_class("alert alert-danger")

                dismiss_button = page.locator("#certification-alert-dismiss-button")
                dismiss_button.focus()
                self.assertTrue(
                    dismiss_button.evaluate("element => document.activeElement === element")
                )
                self.assertTrue(dismissible.evaluate("element => element.classList.contains('show')"))
                page.keyboard.press("Enter")
                page.wait_for_function(
                    "document.querySelector('#certification-alert-dismissible') === null"
                )
                self.assertEqual(dismissible.count(), 0)

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


    def test_tabs_fixture_proves_data_api_state_and_keyboard_flow(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/tabs.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                account_tab = page.locator("#certification-tabs-account-tab")
                security_tab = page.locator("#certification-tabs-security-tab")
                billing_tab = page.locator("#certification-tabs-billing-tab")
                account_pane = page.locator("#certification-tabs-account-pane")
                security_pane = page.locator("#certification-tabs-security-pane")

                expect(account_tab).to_have_attribute("aria-selected", "true")
                expect(security_tab).to_have_attribute("aria-selected", "false")
                self.assertTrue(account_pane.evaluate("element => element.classList.contains('active')"))
                expect(billing_tab).to_be_disabled()

                security_tab.click()
                expect(security_tab).to_have_attribute("aria-selected", "true")
                expect(account_tab).to_have_attribute("aria-selected", "false")
                self.assertTrue(security_pane.evaluate("element => element.classList.contains('active')"))
                self.assertFalse(account_pane.evaluate("element => element.classList.contains('active')"))
                # The pane switch's own 0.16s opacity/transform CSS transition
                # (not a Bootstrap-fired event this harness can await) is still
                # in flight the instant .active toggles; wait for the fade to
                # actually finish so the later axe pass never samples a
                # transient blended color mid-fade as a false contrast defect.
                page.wait_for_function(
                    """
                    () => getComputedStyle(
                      document.querySelector("#certification-tabs-security-pane")
                    ).opacity === "1"
                    """
                )

                account_tab.focus()
                page.keyboard.press("ArrowRight")
                self.assertTrue(
                    security_tab.evaluate("element => document.activeElement === element")
                )
                expect(security_tab).to_have_attribute("aria-selected", "true")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


    def test_collapsible_fixture_proves_toggle_state_and_keyboard_flow(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/collapsible.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                trigger = page.locator("#certification-collapsible-trigger")
                panel = page.locator("#certification-collapsible-panel")
                self.assertEqual(trigger.get_attribute("aria-expanded"), "false")
                self.assertFalse(panel.evaluate("element => element.classList.contains('show')"))

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const panel = document.querySelector("#certification-collapsible-panel");
                      panel.addEventListener("shown.bs.collapse", resolve, { once: true });
                      document.querySelector("#certification-collapsible-trigger").click();
                    })
                    """
                )
                expect(trigger).to_have_attribute("aria-expanded", "true")
                self.assertTrue(panel.evaluate("element => element.classList.contains('show')"))

                page.evaluate(
                    """
                    () => new Promise(resolve => {
                      const panel = document.querySelector("#certification-collapsible-panel");
                      panel.addEventListener("hidden.bs.collapse", resolve, { once: true });
                      document.querySelector("#certification-collapsible-trigger").click();
                    })
                    """
                )
                expect(trigger).to_have_attribute("aria-expanded", "false")
                self.assertFalse(panel.evaluate("element => element.classList.contains('show')"))

                trigger.focus()
                page.keyboard.press("Enter")
                expect(trigger).to_have_attribute("aria-expanded", "true")
                page.wait_for_function(
                    """
                    () => document
                      .querySelector("#certification-collapsible-panel")
                      .classList.contains("show")
                    """
                )
                self.assertTrue(
                    trigger.evaluate("element => document.activeElement === element")
                )

                page.keyboard.press("Space")
                expect(trigger).to_have_attribute("aria-expanded", "false")
                page.wait_for_function(
                    """
                    () => !document
                      .querySelector("#certification-collapsible-panel")
                      .classList.contains("collapsing")
                    """
                )

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


    def test_toggle_group_fixture_proves_native_radio_state_and_keyboard_flow(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/toggle-group.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                left = page.locator("#certification-toggle-left")
                center = page.locator("#certification-toggle-center")
                right = page.locator("#certification-toggle-right")
                self.assertTrue(left.is_checked())
                self.assertFalse(center.is_checked())
                expect(right).to_be_disabled()

                page.locator("label[for='certification-toggle-center']").click()
                self.assertTrue(center.is_checked())
                self.assertFalse(left.is_checked())

                # A disabled native radio cannot become checked, by construction
                # (force=True bypasses Playwright's actionability check, proving
                # the browser itself -- not merely a missing click handler --
                # rejects the interaction).
                page.locator("label[for='certification-toggle-right']").click(force=True)
                self.assertFalse(right.is_checked())
                self.assertTrue(center.is_checked())

                left.focus()
                self.assertTrue(
                    left.evaluate("element => document.activeElement === element")
                )
                # Native grouped radio inputs move both focus and the checked
                # state together on arrow keys, skipping the disabled item
                # automatically -- this is browser-native radio-group behavior,
                # not anything Toggle Group's markup implements itself.
                page.keyboard.press("ArrowRight")
                self.assertTrue(
                    center.evaluate("element => document.activeElement === element")
                )
                self.assertTrue(center.is_checked())

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )
                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()

    def test_context_menu_fixture_proves_public_esm_pointer_keyboard_and_lifecycle(self) -> None:
        for case in CERTIFICATION_CASES:
            with self.subTest(case=case.name):
                context = new_case_context(self.browser, case)
                page = context.new_page()
                evidence = BrowserEvidence(page)
                response = page.goto(
                    f"{self.base_url}/tests/fixtures/certification/context-menu.html",
                    wait_until="networkidle",
                )
                self.assertIsNotNone(response)
                self.assertTrue(response.ok)
                prepare_page(page, case)

                root = page.locator("#certification-context-menu")
                surface = page.locator("#certification-context-menu-surface")
                fallback = page.locator("#certification-context-menu-fallback")
                menu = page.locator("#certification-context-menu-menu")
                rename_item = page.locator("#certification-context-menu-rename")
                toggle_item = page.locator("#certification-context-menu-toggle")
                restore_item = page.locator("#certification-context-menu-restore")
                self.assertEqual(page.locator("body").get_attribute("data-context-menu-ready"), "true")
                self.assertTrue(
                    root.evaluate(
                        """
                        element => window.CertificationContextMenu.getInstance(element)
                          === window.certificationContextMenu
                        """
                    )
                )
                self.assertEqual(surface.get_attribute("aria-expanded"), "false")
                self.assertEqual(fallback.get_attribute("aria-expanded"), "false")
                expect(restore_item).to_be_disabled()

                # Pointer right-click open focuses the menu container (not an
                # item), so :hover alone drives the highlight instead of a
                # focus ring competing with it; Escape closes and returns
                # focus to the invoking trigger.
                surface.click(button="right")
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                expect(surface).to_have_attribute("aria-expanded", "true")
                expect(fallback).to_have_attribute("aria-expanded", "true")
                self.assertTrue(
                    menu.evaluate("element => element === document.activeElement")
                )
                page.keyboard.press("Escape")
                expect(menu).not_to_have_class("dropdown-menu context-menu-menu show")
                expect(surface).to_be_focused()
                self.assertEqual(surface.get_attribute("aria-expanded"), "false")

                # Keyboard invocation: Shift+F10 and the ContextMenu key,
                # anchored to the trigger rather than stale pointer coordinates.
                surface.focus()
                page.keyboard.press("Shift+F10")
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                expect(rename_item).to_be_focused()
                page.keyboard.press("Escape")
                expect(surface).to_be_focused()

                surface.focus()
                page.keyboard.press("ContextMenu")
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                expect(rename_item).to_be_focused()
                page.keyboard.press("Escape")

                # Explicit fallback trigger for touch/keyboard-only use opens
                # anchored to itself; being a pointer-driven open, it also
                # focuses the menu container rather than the first item, and
                # returns focus to itself on Escape.
                fallback.click()
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                self.assertTrue(
                    menu.evaluate("element => element === document.activeElement")
                )
                fallback_box = fallback.bounding_box()
                surface_box = surface.bounding_box()
                self.assertIsNotNone(fallback_box)
                self.assertIsNotNone(surface_box)
                self.assertGreaterEqual(fallback_box["y"], surface_box["y"])
                self.assertLessEqual(
                    fallback_box["y"] + fallback_box["height"],
                    surface_box["y"] + surface_box["height"],
                )
                page.keyboard.press("Escape")
                expect(fallback).to_be_focused()

                # Space on the focused fallback trigger mirrors Bootstrap's
                # button-toggle feel: the same key that opens the menu closes
                # it again instead of moving focus into the next item.
                fallback.press("Space")
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                expect(fallback).to_have_attribute("aria-expanded", "true")
                fallback.press("Space")
                expect(menu).not_to_have_class("dropdown-menu context-menu-menu show")
                expect(fallback).to_be_focused()

                # Disabled item is skipped by roving focus and does not
                # activate or close the menu; enabled item activation closes it.
                fallback.click()
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                restore_item.click(force=True)
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                rename_item.click()
                expect(menu).not_to_have_class("dropdown-menu context-menu-menu show")

                # A persistent checkbox item keeps the menu open, toggles
                # Bootstrap's own button-toggle Data API state, and shows its
                # check indicator (not just the aria-pressed/.active state:
                # a fixture missing the indicator's icon markup would still
                # pass an aria-pressed-only assertion while rendering nothing
                # visible).
                fallback.click()
                toggle_item.click()
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                expect(toggle_item).to_have_class("dropdown-item dropdown-item-check active")
                expect(toggle_item).to_have_attribute("aria-pressed", "true")
                toggle_indicator = toggle_item.locator(".dropdown-item-check__indicator")
                expect(toggle_indicator).to_have_css("opacity", "1")
                indicator_box = toggle_indicator.locator("svg").bounding_box()
                self.assertIsNotNone(indicator_box)
                self.assertGreater(indicator_box["width"], 0)
                self.assertGreater(indicator_box["height"], 0)

                # Outside click closes the menu.
                page.locator("h1").click()
                expect(menu).not_to_have_class("dropdown-menu context-menu-menu show")

                self.assertEqual(run_axe(page), [])

                # Viewport collision near the bottom-right edge stays clamped
                # inside the viewport.
                edge_surface = page.locator("#certification-context-menu-edge-surface")
                edge_menu = page.locator("#certification-context-menu-edge-menu")
                edge_surface.click(button="right")
                expect(edge_menu).to_have_class("dropdown-menu context-menu-menu show")
                viewport = page.viewport_size
                edge_box = edge_menu.bounding_box()
                self.assertIsNotNone(viewport)
                self.assertIsNotNone(edge_box)
                self.assertLessEqual(edge_box["x"] + edge_box["width"], viewport["width"] + 1)
                self.assertLessEqual(edge_box["y"] + edge_box["height"], viewport["height"] + 1)
                self.assertGreaterEqual(edge_box["x"], -1)
                self.assertGreaterEqual(edge_box["y"], -1)
                page.keyboard.press("Escape")

                self.assertEqual(
                    page.locator("html").get_attribute("dir"),
                    case.direction,
                )
                self.assertEqual(
                    page.locator("html").get_attribute("data-bs-theme"),
                    case.color_scheme,
                )
                self.assertFalse(
                    page.evaluate(
                        "document.documentElement.scrollWidth > "
                        "document.documentElement.clientWidth"
                    )
                )

                # Repeated init returns the same instance; dispose removes
                # listeners/generated state and permits re-initialization.
                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationContextMenu.dispose();
                          return window.CertificationContextMenu.getInstance(element) === null;
                        }
                        """
                    )
                )
                self.assertEqual(surface.get_attribute("aria-expanded"), "false")
                surface.click(button="right")
                expect(menu).not_to_have_class("dropdown-menu context-menu-menu show")
                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationContextMenu = window.CertificationContextMenu
                            .getOrCreateInstance(element);
                          return window.CertificationContextMenu.getInstance(element)
                            === window.certificationContextMenu;
                        }
                        """
                    )
                )
                surface.click(button="right")
                expect(menu).to_have_class("dropdown-menu context-menu-menu show")
                page.keyboard.press("Escape")

                self.assertEqual(run_axe(page), [])
                prepare_page(page, case, normalize_screenshot=True)
                self.assertGreater(len(page.screenshot(full_page=True)), 1000)
                evidence.assert_clean()
                context.close()


if __name__ == "__main__":
    unittest.main()
