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
)


class CertificationBrowserHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
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
                menu = page.locator("#certification-combobox-listbox")
                hidden_value = root.locator('input[type="hidden"]')
                empty_state = root.locator("[data-moo-combobox-empty]")
                live_region = root.locator("[data-moo-combobox-live]")
                expect(page.locator("body")).to_have_attribute("data-combobox-ready", "true")
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
                self.assertEqual(root.locator("[data-moo-combobox-empty]").count(), 0)
                self.assertEqual(root.locator("[data-moo-combobox-live]").count(), 0)
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
                self.assertEqual(root.locator("[data-moo-combobox-empty]").count(), 1)
                self.assertEqual(root.locator("[data-moo-combobox-live]").count(), 1)
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
                expect(root).to_have_attribute("data-moo-sidebar-ready", "")
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
                    expect(root).to_have_attribute("data-moo-sidebar-state", "expanded")
                    expect(trigger).to_have_attribute("aria-expanded", "true")
                    trigger.click()
                    expect(root).to_have_attribute("data-moo-sidebar-state", "collapsed")
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
                    expect(root).to_have_attribute("data-moo-sidebar-state", "expanded")
                    search.focus()
                    page.keyboard.press("Control+b")
                    expect(root).to_have_attribute("data-moo-sidebar-state", "expanded")
                    self.assertEqual(run_axe(page), [])

                self.assertTrue(
                    root.evaluate(
                        """
                        element => {
                          window.certificationSidebar.dispose();
                          return window.CertificationSidebar.getInstance(element) === null
                            && !element.hasAttribute("data-moo-sidebar-ready");
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
                            && element.hasAttribute("data-moo-sidebar-ready");
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

    def test_canonical_bootstrap_lane_resolves_the_real_local_bundle(self) -> None:
        self.assertEqual(CERTIFICATION_BOOTSTRAP_LANES, (CANONICAL_BOOTSTRAP,))
        self.assertEqual(CANONICAL_BOOTSTRAP.version, "5.3.3")
        context = self.browser.new_context()
        response = context.request.get(CANONICAL_BOOTSTRAP.bundle_url(self.base_url))
        self.assertTrue(response.ok)
        self.assertIn("Bootstrap v5.3.3", response.text())
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
                    "form-text"
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
                ).to_have_class("invalid-feedback")

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

                expect(textarea).to_have_attribute("aria-label", "Review notes")
                textarea.fill("Grouped text area")
                expect(textarea).to_have_value("Grouped text area")
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
                expect(form).to_have_class("needs-validation")
                expect(form).to_have_attribute("novalidate", "")
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

                self.assertEqual(page.locator(".avatar").count(), 7)

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

                badge_count = page.locator("#certification-avatar-badge-count")
                expect(badge_count.locator(".avatar-badge")).to_have_text("3")
                expect(badge_count.locator(".avatar-badge")).to_have_attribute(
                    "aria-label", "3 unread messages"
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


if __name__ == "__main__":
    unittest.main()
