from __future__ import annotations

import re
import unittest

from tests.helpers import ROOT


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
        self.assertNotIn("root.body.appendChild(container)", source)

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
