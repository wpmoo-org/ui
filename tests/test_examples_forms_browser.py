from __future__ import annotations

import unittest

from playwright.sync_api import sync_playwright

from tests.helpers.browser_harness import (
    CERTIFICATION_CASES,
    launch_certification_browser,
    new_case_context,
    prepare_page,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


SIGN_IN_PATH = "/site-dist/examples/auth/sign-in/index.html"
FORGOT_PASSWORD_PATH = "/site-dist/examples/auth/forgot-password/index.html"
SETTINGS_PROFILE_PATH = "/site-dist/examples/settings/profile/index.html"


class ExamplesFormsDoNotSubmitBrowserTests(unittest.TestCase):
    """Every auth/settings example page's footer says its form "does not
    submit anywhere or store any data." These pages' submit buttons don't
    carry type="submit" (see button() usage in the auth/settings templates)
    specifically so that claim holds in a real browser, not just in a
    static button[type] check. Forgot Password is the one page with
    exactly one text field and no submit button in its form -- the one
    shape the HTML spec's implicit form submission can still fire for even
    when no button in the form is type="submit"."""

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

    def open(self, path: str):
        context = new_case_context(self.browser, CERTIFICATION_CASES[0])
        page = context.new_page()
        navigations: list[str] = []
        page.on(
            "framenavigated",
            lambda frame: navigations.append(frame.url)
            if frame == page.main_frame
            else None,
        )
        response = page.goto(f"{self.base_url}{path}", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, CERTIFICATION_CASES[0])
        navigations.clear()  # drop the initial goto() navigation itself
        return context, page, navigations

    def test_forgot_password_single_field_enter_does_not_submit(self) -> None:
        context, page, navigations = self.open(FORGOT_PASSWORD_PATH)
        try:
            email = page.locator("#forgot-password-email")
            email.fill("demo@example.com")
            email.press("Enter")
            page.wait_for_timeout(300)
            self.assertEqual(
                navigations,
                [],
                "Pressing Enter in the lone Email field navigated the page "
                "-- the implicit single-field form submission the HTML "
                "spec still allows without a type=\"submit\" button.",
            )
            self.assertEqual(email.input_value(), "demo@example.com")
        finally:
            context.close()

    def test_sign_in_button_click_does_not_submit(self) -> None:
        context, page, navigations = self.open(SIGN_IN_PATH)
        try:
            page.locator("#sign-in-email").fill("demo@example.com")
            page.locator("#sign-in-password").fill("hunter2")
            page.get_by_role("button", name="Sign in").click()
            page.wait_for_timeout(300)
            self.assertEqual(
                navigations,
                [],
                "Clicking Sign in navigated the page.",
            )
        finally:
            context.close()

    def test_settings_profile_save_does_not_submit(self) -> None:
        # Covers the guard's other scope branch ([data-moo-example-settings]
        # form) -- Sign In only exercises .moo-auth-page form. Save changes
        # is type="button" and Enter doesn't implicitly submit a 3-field
        # form, so neither actually dispatches a submit event on its own --
        # asserting on them would pass even without the guard. Call
        # requestSubmit() directly (not submit(), which skips event
        # handlers entirely) so this actually exercises the guard's
        # preventDefault, not just the absence of anything that would
        # trigger it.
        context, page, navigations = self.open(SETTINGS_PROFILE_PATH)
        try:
            page.locator("#settings-name").fill("Ada Lovelace")
            page.evaluate("document.querySelector('form').requestSubmit()")
            page.wait_for_timeout(300)
            self.assertEqual(
                navigations,
                [],
                "The Settings/Profile form submitted despite the guard.",
            )
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
