from __future__ import annotations

import re
import subprocess

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase

IMAGES = [
    {"src": "/a-640.webp", "href": "/a-1600.webp", "width": 1600, "height": 1067, "alt": "Hills <at> dawn"},
    {"src": "/b-640.webp", "href": "/b-1600.webp", "width": 1067, "height": 1600, "alt": "Lake"},
    {"src": "/c-640.webp", "width": 1600, "height": 1200, "alt": "Valley",
     "srcset": "/c-320.webp 320w, /c-640.webp 640w", "sizes": "33vw",
     "large_srcset": "/c-1600.webp 1600w, /c-2400.webp 2400w"},
]


class ImageGalleryTests(CatalogTestCase):
    @staticmethod
    def thumbnails_part(output: str) -> str:
        return output.split('class="modal fade')[0]

    def render(self, images=IMAGES, **options) -> str:
        template = create_environment().from_string(
            '{% from "blocks/image_gallery.html.jinja" import image_gallery %}'
            "{{ image_gallery('album', images, **options) }}"
        )
        return " ".join(template.render(images=images, options=options).split())

    def thumbnails(self, output: str) -> list[str]:
        return re.findall(r"<a [^>]*data-gallery-index=[^>]*>", output)

    def test_every_thumbnail_links_to_its_large_image_and_opens_the_lightbox(self) -> None:
        output = self.render()
        links = self.thumbnails(output)
        self.assertEqual(len(links), 3)
        for index, (link, href) in enumerate(zip(links, ["/a-1600.webp", "/b-1600.webp", "/c-640.webp"])):
            self.assertIn(f'href="{href}"', link)
            self.assertIn('data-bs-toggle="modal" data-bs-target="#album-lightbox"', link)
            self.assertIn(f'data-gallery-index="{index}"', link)
        self.assertIn(
            '<img class="object-fit-cover" src="/a-640.webp" width="1600" height="1067" '
            'alt="Hills &lt;at&gt; dawn" loading="lazy" decoding="async">',
            output,
        )
        self.assertIn('srcset="/c-320.webp 320w, /c-640.webp 640w" sizes="33vw"', output)
        self.assertIn('id="album" data-image-gallery', output)

    def test_grid_crops_tiles_to_the_ratio_with_columns_per_breakpoint(self) -> None:
        output = self.render(ratio="3x2", columns={"md": 4, "xs": 2}, gap=3)
        self.assertIn('<div class="row row-cols-2 row-cols-md-4 g-3">', output)
        self.assertEqual(output.count("ratio ratio-3x2 d-block rounded overflow-hidden"), 3)
        for ratio in ("1x1", "4x3"):
            self.assertIn(f"ratio-{ratio} ", self.render(ratio=ratio))

    def test_justified_rows_carry_each_photo_ratio(self) -> None:
        output = self.render(layout="justified", gap=1)
        self.assertIn('<div class="gallery-justified gap-1">', output)
        self.assertIn('style="--moo-gallery-ratio: 1.4995"', output)
        self.assertIn('style="--moo-gallery-ratio: 0.6669"', output)
        self.assertIn('class="d-block w-100 h-auto" src="/b-640.webp"', output)

    def test_masonry_flows_uncropped_photos_through_columns(self) -> None:
        output = self.render(layout="masonry", columns={"xs": 2, "lg": 4})
        self.assertIn('<div class="columns-2 columns-lg-4 column-gap-2">', output)
        self.assertEqual(output.count('class="d-inline-block w-100 mb-2 rounded overflow-hidden"'), 3)
        self.assertNotIn("ratio-", self.thumbnails_part(output))

    def test_featured_shows_the_first_photo_large(self) -> None:
        output = self.render(layout="featured", ratio="1x1", columns={"xs": 3})
        first, rest = output.split('<div class="row row-cols-3 g-2">', 1)
        self.assertIn("ratio ratio-16x9", first)
        self.assertIn('data-gallery-index="0"', first)
        self.assertEqual(self.thumbnails_part(rest).count("ratio ratio-1x1"), 2)

    def test_limit_hides_extra_thumbnails_behind_a_show_all_button(self) -> None:
        images = [dict(IMAGES[0], alt=f"Photo {n}") for n in range(12)]
        output = self.render(images=images)
        self.assertEqual(output.count('<div class="col d-none">'), 3)
        self.assertIn('data-bs-toggle="modal" data-bs-target="#album-lightbox"', output)
        self.assertIn("Show all 12 photos", output)
        self.assertEqual(self.thumbnails_part(self.render(images=images, layout="justified", limit=4)).count(" d-none\""), 8)
        unlimited = self.render(images=images, limit="all")
        self.assertNotIn("d-none\"", self.thumbnails_part(unlimited))
        self.assertNotIn("Show all", unlimited)
        self.assertNotIn("Show all", self.render())

    def test_lightbox_requests_no_large_image_before_it_opens(self) -> None:
        output = self.render()
        lightbox = output[output.index('class="modal fade"'):]
        self.assertIn('aria-label="Photos"', lightbox)
        self.assertIn("modal-dialog modal-xl modal-fullscreen-lg-down modal-dialog-centered", lightbox)
        self.assertIn(
            '<div class="carousel slide flex-grow-1 gallery-stage" id="album-lightbox-carousel" '
            'data-bs-interval="false" data-bs-touch="true" data-gallery-stage>',
            lightbox,
        )
        self.assertIn('class="modal-body d-flex p-0 bg-body-tertiary"', lightbox)
        self.assertEqual(lightbox.count('class="carousel-item h-100'), 3)
        self.assertEqual(lightbox.count('class="carousel-item h-100 active"'), 1)
        self.assertEqual(lightbox.count('<img class="mw-100 mh-100 w-auto h-auto rounded-2 border shadow-sm"'), 3)
        self.assertNotIn(" src=", lightbox)
        self.assertNotIn(" srcset=", lightbox)
        self.assertIn('data-gallery-src="/a-1600.webp"', lightbox)
        self.assertIn(
            'data-gallery-src="/c-640.webp" data-gallery-srcset="/c-1600.webp 1600w, /c-2400.webp 2400w" '
            'sizes="(min-width: 1200px) 1140px, 100vw"',
            lightbox,
        )
        self.assertIn('aria-live="polite" data-gallery-counter="{current} of {total}">1 of 3<', lightbox)
        self.assertIn("data-gallery-caption>Hills &lt;at&gt; dawn<", lightbox)
        for control in ("previous", "play", "pause", "next", "fullscreen", "windowed"):
            self.assertIn(f'id="album-lightbox-{control}"', lightbox)
        self.assertIn('data-bs-dismiss="modal"', lightbox)
        self.assertIn('class="progress rounded-0 d-none" role="progressbar" aria-label="Time until the next photo"', lightbox)
        single = self.render(images=IMAGES[:1])
        self.assertNotIn('id="album-lightbox-play"', single)
        self.assertNotIn('class="progress', single)
        self.assertIn('id="album-lightbox-fullscreen"', single)

    def test_lightbox_shows_a_caption_and_credit_when_given(self) -> None:
        images = [dict(IMAGES[0], caption="Sports day", credit="Schoolyard, 2025 · Photo by A. Teacher"), IMAGES[1]]
        output = self.render(images=images)
        self.assertIn('data-gallery-slide-title="Sports day" data-gallery-slide-credit="Schoolyard, 2025 · Photo by A. Teacher"', output)
        self.assertIn('data-gallery-slide-title="Lake">', output)
        self.assertIn("data-gallery-caption>Sports day<", output)
        self.assertIn('class="m-0 small text-body-secondary" data-gallery-credit>Schoolyard, 2025 · Photo by A. Teacher<', output)
        self.assertIn('class="m-0 small text-body-secondary d-none" data-gallery-credit><', self.render())

    def test_every_label_is_translatable(self) -> None:
        labels = {
            "title": "Fotos", "close": "Schließen", "previous": "Zurück",
            "next": "Weiter", "play": "Diashow starten", "pause": "Diashow anhalten",
            "progress": "Zeit bis zum nächsten Foto",
            "fullscreen": "Vollbild", "exit_fullscreen": "Vollbild beenden",
            "counter": "{current} von {total}", "show_all": "Alle {total} Fotos anzeigen",
        }
        output = self.render(images=IMAGES * 4, labels=labels)
        for text in ("Alle 12 Fotos anzeigen", "1 von 12", "Zurück </button>", "Weiter <svg"):
            self.assertIn(text, output)
        for name in ("Fotos", "Schließen", "Diashow starten", "Diashow anhalten", "Vollbild", "Vollbild beenden",
                     "Zeit bis zum nächsten Foto"):
            self.assertIn(f'aria-label="{name}"', output)
        self.assertIn('data-gallery-counter="{current} von {total}"', output)

    def test_invalid_options_fail_at_render_time(self) -> None:
        for options in (
            {"layout": "carousel"}, {"ratio": "16x9"}, {"gap": 6}, {"limit": 0},
            {"limit": "some"}, {"columns": {"xs": 5}}, {"columns": {"phone": 2}},
        ):
            with self.subTest(options=options), self.assertRaises(Exception):
                self.render(**options)
        for images in ([], [{"src": "/a.webp", "alt": "No size"}], [{"src": "/a.webp", "width": 1, "height": 1}]):
            with self.subTest(images=images), self.assertRaises(Exception):
                self.render(images=images)

    def test_sass_extends_bootstrap_maps_and_keeps_justified_on_a_setting(self) -> None:
        utilities = (ROOT / "scss/utilities/_gallery.scss").read_text(encoding="utf-8")
        self.assertIn('$aspect-ratios: map-merge($aspect-ratios, ("3x2": calc(2 / 3 * 100%)));', utilities)
        self.assertIn('"column-count": (', utilities)
        self.assertIn("class: columns,", utilities)
        component = (ROOT / "scss/components/_gallery.scss").read_text(encoding="utf-8")
        self.assertIn("--moo-gallery-row-height: #{$moo-gallery-row-height};", component)
        self.assertIn(
            "flex: var(--moo-gallery-ratio, 1) 1 calc(var(--moo-gallery-ratio, 1) * var(--moo-gallery-row-height));",
            component,
        )
        settings = (ROOT / "scss/settings/_component_variables.scss").read_text(encoding="utf-8")
        self.assertIn("$moo-gallery-row-height: 6rem !default;", settings)
        self.assertIn("$moo-gallery-row-height-md: 8rem !default;", settings)
        self.assertIn('$moo-gallery-stage-height: unquote("min(62svh, 38rem)") !default;', settings)
        self.assertIn("height: $moo-gallery-stage-height;", component)

    def test_compiled_css_ships_the_gallery_helpers(self) -> None:
        build = self.run_build()
        self.assertEqual(build.returncode, 0, build.stderr)
        css = (ROOT / "dist/assets/css/moo-ui.css").read_text(encoding="utf-8")
        compact = re.sub(r"\s+", "", css)
        self.assertIn(".ratio-3x2{--bs-aspect-ratio:", compact)
        self.assertIn(".columns-md-3{column-count:3!important", compact)
        self.assertIn(".gallery-justified::after{flex-grow:1e9;", compact)
        self.assertIn(".gallery-stage{height:min(62svh,38rem)", compact)
        core = re.sub(r"\s+", "", (ROOT / "dist/assets/css/moo.css").read_text(encoding="utf-8"))
        for selector in (".ratio-3x2{", ".columns-lg-4{", ".gallery-justified{", ".gallery-stage{"):
            self.assertIn(selector, core)

    def test_module_import_is_side_effect_free(self) -> None:
        result = subprocess.run(
            ["node", "--input-type=module", "--eval",
             'import ImageGallery, { initImageGalleries } from "./src/js/components/image-gallery.js"; '
             'if (typeof ImageGallery.getOrCreateInstance !== "function" '
             '|| typeof initImageGalleries !== "function") process.exit(1);'],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
