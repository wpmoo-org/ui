from __future__ import annotations

import re
import unittest

from playwright.sync_api import sync_playwright

from tests.helpers import ROOT
from tests.helpers.browser_harness import (
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


SIDEBAR_JS = ROOT / "src/js/components/sidebar.js"
DATEPICKER_JS = ROOT / "src/js/components/datepicker.js"
DATATABLE_JS = ROOT / "src/js/components/datatable.js"
BOOTSTRAP_PREVIEW_JS = ROOT / "site/src/js/catalog/bootstrap-preview.js"
FIXTURE = ROOT / "conformance/fixtures/owner-portals.html"
INITIALIZER = ROOT / "conformance/fixtures/assets/init-owner-portals.js"


class OwnerPortalTests(unittest.TestCase):
    def test_moo_portals_resolve_the_trigger_owner_before_falling_back_to_body(
        self,
    ) -> None:
        sidebar = SIDEBAR_JS.read_text(encoding="utf-8")
        datepicker = DATEPICKER_JS.read_text(encoding="utf-8")
        datatable = DATATABLE_JS.read_text(encoding="utf-8")

        for source in (sidebar, datepicker, datatable):
            self.assertIn('from "../theme-owner.js"', source)
            self.assertIn("findThemeOwner", source)
            self.assertIn("ownerPortalRoot", source)

        self.assertIn("this._portalRoot(item).appendChild(flyout);", sidebar)
        self.assertIn("container: this._portalRoot(control)", sidebar)
        self.assertNotIn('container: "body"', sidebar)

        self.assertIn("const owner = findThemeOwner(instance._trigger);", datepicker)
        self.assertIn("const portalRoot = ownerPortalRoot(owner) ||", datepicker)
        self.assertIn("portalRoot.appendChild(popover);", datepicker)
        self.assertNotIn("datepickerPortalHost", datepicker)
        self.assertNotIn("data-datepicker-portal-host", datepicker)

        self.assertIn("this._portalRoot(trigger).appendChild(menu);", datatable)
        self.assertIn("container: this._portalRoot(trigger)", datatable)
        self.assertNotIn("this._document.body.appendChild(menu);", datatable)

    def test_catalog_bootstrap_overlays_receive_explicit_owner_containers(self) -> None:
        source = BOOTSTRAP_PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn('from "../../../../src/js/theme-owner.js"', source)
        self.assertIn("const portalFor = (trigger) =>", source)
        self.assertIn("ownerPortalRoot(findThemeOwner(trigger))", source)
        self.assertIn("Tooltip.getOrCreateInstance(trigger, {", source)
        self.assertIn("Popover.getOrCreateInstance(trigger, { container: portal })", source)
        self.assertIn("portal.appendChild(modal);", source)
        self.assertIn("portal.appendChild(sheet);", source)
        self.assertIn("portal.appendChild(container);", source)
        self.assertIn(
            "const trigger = event.relatedTarget || modal;",
            source,
        )
        self.assertIn(
            "const getSharedToastStack = (sourceContainer, trigger) =>",
            source,
        )
        self.assertIn("ownerPortalFor(trigger) || portalFor(modal)", source)
        self.assertIn(
            "ownerPortalFor(trigger) || portalFor(sourceContainer)",
            source,
        )
        self.assertNotIn("root.body.appendChild(container)", source)

    def test_catalog_bootstrap_preview_routes_modal_and_toast_to_trigger_owner(
        self,
    ) -> None:
        skip_if_browser_launch_is_sandboxed()

        with serve_repository() as base_url, sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                page = browser.new_page()
                response = page.goto(
                    f"{base_url}/tests/fixtures/owner-isolation.html",
                    wait_until="load",
                )
                self.assertIsNotNone(response)
                assert response is not None
                self.assertTrue(response.ok)

                report = page.evaluate(
                    """
                    async (baseUrl) => {
                      document.body.innerHTML = `
                        <div id="outer-owner" class="moo-ui" data-bs-theme="dark">
                          <div id="outer-portal" data-moo-overlay-portal-host></div>
                          <section id="inner-owner" class="moo-ui" data-bs-theme="light">
                            <div id="inner-portal" data-moo-overlay-portal-host></div>
                            <button id="modal-trigger" type="button">Open modal</button>
                            <button id="toast-trigger" type="button" data-toast-target="#toast-template">Show toast</button>
                          </section>
                          <section class="moo-catalog">
                            <div id="outside-modal" class="modal"></div>
                            <div class="toast-container--stacked" data-toast-stack="deck">
                              <template id="toast-template" data-toast-template="toast"><div class="toast"></div></template>
                            </div>
                          </section>
                        </div>`;
                      window.bootstrap = {
                        Toast: {
                          getOrCreateInstance(toast) {
                            return {
                              show() { toast.classList.add("show"); },
                              dispose() {},
                            };
                          },
                        },
                      };
                      const { initBootstrapPreview } = await import(
                        `${baseUrl}/site/src/js/catalog/bootstrap-preview.js?trigger-owner-test`
                      );
                      const dispose = initBootstrapPreview(document);
                      const modal = document.getElementById("outside-modal");
                      const modalEvent = new Event("show.bs.modal", { bubbles: true });
                      Object.defineProperty(modalEvent, "relatedTarget", {
                        value: document.getElementById("modal-trigger"),
                      });
                      modal.dispatchEvent(modalEvent);
                      document.getElementById("toast-trigger").click();
                      const result = {
                        modalParent: modal.parentElement?.id || null,
                        toastParent: document.querySelector(
                          '[data-moo-catalog-toast-stack="shared"]',
                        )?.parentElement?.id || null,
                      };
                      dispose();
                      return result;
                    }
                    """,
                    base_url,
                )
            finally:
                browser.close()

        self.assertEqual(
            report,
            {"modalParent": "inner-portal", "toastParent": "inner-portal"},
        )

    def test_external_fixture_models_a_nested_owner_and_generic_portal_host(self) -> None:
        fixture = FIXTURE.read_text(encoding="utf-8")
        initializer = INITIALIZER.read_text(encoding="utf-8")

        self.assertIn('data-owner-portals-host', fixture)
        self.assertRegex(
            fixture,
            r'class="moo-ui[^\"]*" data-bs-theme="dark"',
        )
        self.assertRegex(
            fixture,
            r'class="moo-ui[^\"]*" data-bs-theme="light"',
        )
        self.assertIn('class="moo-ui" data-moo-overlay-portal-host', fixture)
        self.assertIn('<script src="assets/init-owner-portals.js"></script>', fixture)
        self.assertNotIn("<script>", fixture)

        self.assertIn("const portal = ownerPortalRoot(findThemeOwner(trigger));", initializer)
        self.assertIn("Tooltip.getOrCreateInstance(trigger, { container: portal });", initializer)
        self.assertIn("Popover.getOrCreateInstance(trigger, { container: portal });", initializer)
        self.assertNotIn("document.body.append", initializer)
