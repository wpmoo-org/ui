from __future__ import annotations

import re
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase
from tests.helpers.browser_harness import launch_certification_browser

PHOTOS = ["dawn-hills", "lake-evening", "green-valley", "dunes", "winter-ridge"]
SIZES = {"dawn-hills": (1600, 1067), "lake-evening": (1067, 1600), "green-valley": (1600, 1200),
         "dunes": (1600, 900), "winter-ridge": (1600, 1600)}


def has_class(name: str) -> re.Pattern[str]:
    return re.compile(rf"(^|\s){re.escape(name)}(\s|$)")


class ImageGalleryBrowserTests(CatalogTestCase):
    def test_lightbox_opens_at_the_photo_and_loads_only_its_neighbours(self) -> None:
        build = self.run_build()
        self.assertEqual(build.returncode, 0, build.stderr)
        images = [
            {"src": f"/thumb/{name}.webp", "href": f"/large/{name}.webp",
             "width": SIZES[name][0], "height": SIZES[name][1], "alt": name.replace("-", " ")}
            for name in PHOTOS
        ]
        page_html = create_environment().from_string('''
            {% from "blocks/image_gallery.html.jinja" import image_gallery %}
            <!doctype html><html dir="{{ direction }}"><head><meta name="viewport" content="width=device-width,initial-scale=1">
            <link rel="stylesheet" href="/moo-ui.css"></head><body>
            <main class="moo-ui container py-4" data-bs-theme="light" dir="{{ direction }}">
              {{ image_gallery("album", images, layout="justified", limit=4) }}
            </main>
            <script src="/bootstrap.js"></script>
            <script type="module">import { initImageGalleries } from "/image-gallery.js";
              initImageGalleries(document); document.body.dataset.ready = "true";</script>
            </body></html>''')
        assets = {
            "/moo-ui.css": ((ROOT / "dist/assets/css/moo-ui.css").read_bytes(), "text/css"),
            "/bootstrap.js": ((ROOT / "vendor/bootstrap/dist/js/bootstrap.bundle.min.js").read_bytes(), "text/javascript"),
            "/image-gallery.js": ((ROOT / "src/js/components/image-gallery.js").read_bytes(), "text/javascript"),
        }
        for name in PHOTOS:
            for kind, size in (("thumb", 640), ("large", 1600)):
                path = ROOT / f"site/static/images/gallery/{name}-{size}.webp"
                assets[f"/{kind}/{name}.webp"] = (path.read_bytes(), "image/webp")

        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for direction in ("ltr", "rtl"):
                    with self.subTest(direction=direction):
                        context = browser.new_context(viewport={"width": 1280, "height": 900})
                        try:
                            page = context.new_page()
                            requested: list[str] = []
                            foreign: list[str] = []

                            def serve(route):
                                path = urlparse(route.request.url).path
                                requested.append(path)
                                if path == "/probe":
                                    route.fulfill(body=page_html.render(images=images, direction=direction),
                                                  content_type="text/html")
                                elif path in assets:
                                    body, kind = assets[path]
                                    route.fulfill(body=body, content_type=kind)
                                else:
                                    route.fulfill(status=404, body="Unknown fixture asset")

                            page.route("http://gallery.invalid/**", serve)
                            page.on("request", lambda request: foreign.append(request.url)
                                    if not request.url.startswith(("http://gallery.invalid/", "data:")) else None)
                            page.goto("http://gallery.invalid/probe")
                            page.wait_for_function("document.body.dataset.ready === 'true'")
                            page.wait_for_load_state("networkidle")
                            self.assertEqual([p for p in requested if p.startswith("/large/")], [])

                            dialog = page.locator("#album-lightbox")
                            counter = dialog.locator("[data-gallery-counter]")
                            caption = dialog.locator("[data-gallery-caption]")
                            trigger = page.locator('a[data-gallery-index="2"]')
                            trigger.click()
                            expect(dialog).to_be_visible()
                            expect(counter).to_have_text("3 of 5")
                            expect(caption).to_have_text("green valley")
                            loaded = dialog.locator(".carousel-item img[src]")
                            expect(loaded).to_have_count(3)
                            self.assertEqual(
                                sorted(loaded.evaluate_all("images => images.map(i => i.getAttribute('src'))")),
                                ["/large/dunes.webp", "/large/green-valley.webp", "/large/lake-evening.webp"],
                            )

                            page.wait_for_function(
                                "document.querySelector('#album-lightbox').contains(document.activeElement)")
                            forward = "ArrowRight" if direction == "ltr" else "ArrowLeft"
                            page.keyboard.press(forward)
                            expect(counter).to_have_text("4 of 5")
                            expect(dialog.locator(".carousel-item img[src]")).to_have_count(4)
                            page.wait_for_function("!document.querySelector('#album-lightbox .carousel-item-next, #album-lightbox .carousel-item-prev')")
                            page.locator("#album-lightbox-previous").click()
                            expect(counter).to_have_text("3 of 5")

                            page.locator("#album-lightbox-fullscreen").click()
                            expect(dialog.locator(".modal-dialog")).to_have_class(has_class("modal-fullscreen"))
                            expect(dialog.locator("[data-gallery-stage]")).not_to_have_class(has_class("gallery-stage"))
                            expect(page.locator("#album-lightbox-windowed")).to_be_focused()
                            expect(page.locator("#album-lightbox-fullscreen")).to_be_hidden()
                            page.locator("#album-lightbox-windowed").click()
                            expect(dialog.locator(".modal-dialog")).not_to_have_class(has_class("modal-fullscreen"))
                            expect(dialog.locator("[data-gallery-stage]")).to_have_class(has_class("gallery-stage"))

                            page.locator("#album-lightbox-play").click()
                            expect(page.locator("#album-lightbox-pause")).to_be_focused()
                            expect(counter).to_have_attribute("aria-live", "off")
                            page.locator("#album-lightbox-pause").click()
                            expect(page.locator("#album-lightbox-play")).to_be_visible()
                            expect(counter).to_have_attribute("aria-live", "polite")

                            page.keyboard.press("Escape")
                            expect(dialog).to_be_hidden()
                            expect(trigger).to_be_focused()

                            page.get_by_role("button", name="Show all 5 photos").click()
                            expect(counter).to_have_text("1 of 5")
                            self.assertEqual(foreign, [])

                            # Below the lg breakpoint the dialog fills the screen, the
                            # stage takes the remaining height and needs no switch.
                            page.wait_for_function(
                                "document.querySelector('#album-lightbox').contains(document.activeElement)")
                            page.keyboard.press("Escape")
                            expect(dialog).to_be_hidden()
                            page.set_viewport_size({"width": 390, "height": 844})
                            trigger.click()
                            expect(dialog).to_be_visible()
                            expect(dialog.locator("[data-gallery-stage]")).not_to_have_class(has_class("gallery-stage"))
                            expect(page.locator("#album-lightbox-fullscreen")).to_be_hidden()
                            stage = dialog.locator("[data-gallery-stage]").bounding_box()
                            self.assertGreater(stage["height"], 500)
                        finally:
                            context.close()
            finally:
                browser.close()
