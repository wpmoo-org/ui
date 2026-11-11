from __future__ import annotations

import hashlib
import json
import re

from build import create_environment
from tests.helpers import CatalogTestCase

CONFIG = {
    "revision": "7b2ac531ea92",
    "links": [{"label": "Cookie policy", "href": "/cookies"}],
    "categories": [
        {"id": "functional", "required": True, "label": "Functional", "description": "Needed <always>",
         "services": [{"id": "site", "name": "Site session", "provider": "Us", "purpose": "Sign-in",
                       "storage": [{"name": "session_id", "type": "cookie", "lifetime": "7 days"}]}]},
        {"id": "statistics", "label": "Statistics",
         "services": [{"id": "matomo", "name": "Matomo", "provider": "Us",
                       "storage": [{"name": "_pk_id.*", "type": "cookie", "lifetime": "13 months"},
                                   {"name": "beacon", "type": "pixel"}]}]},
        {"id": "external_media", "label": "External media",
         "services": [{"id": "video", "name": "Video", "provider": "Example", "privacy_url": "https://example.test/privacy",
                       "storage": [{"name": "yt*", "type": "local"}]}]},
        {"id": "marketing", "label": "Marketing", "services": []},
    ],
}


def revision(lines: list[str], reask: int = 0) -> str:
    """The rule documented in consent.js and implemented by every host."""
    body = sorted(lines) + ([f"reask:{reask}"] if reask else [])
    return hashlib.sha256("\n".join(body).encode()).hexdigest()[:12]


class ConsentTests(CatalogTestCase):
    def render(self, call: str, config=CONFIG, **values) -> str:
        template = create_environment().from_string(
            '{% from "blocks/consent.html.jinja" import consent_card, consent_trigger, '
            "consent_placeholder, consent_policy_table %}" + call
        )
        return " ".join(template.render(config=config, **values).split())

    def runtime(self, output: str) -> dict:
        match = re.search(r'<script type="application/json" data-consent-config>(.*?)</script>', output)
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_card_is_a_hidden_non_modal_dialog_named_by_its_title(self) -> None:
        output = self.render("{{ consent_card('consent', config) }}")
        aside = re.search(r"<aside [^>]*>", output).group(0)
        for attribute in ('id="consent"', 'role="dialog"', 'aria-modal="false"', 'aria-labelledby="consent-title"',
                          'aria-describedby="consent-text"', "data-consent", "hidden", "fixed-bottom"):
            self.assertIn(attribute, aside)
        self.assertIn('id="consent-title" tabindex="-1"', output)

    def test_only_categories_with_services_are_shown(self) -> None:
        output = self.render("{{ consent_card('consent', config) }}")
        triggers = re.findall(r'id="consent-categories-([a-z_]+)-trigger"', output)
        self.assertEqual(triggers, ["functional", "statistics", "external_media"])
        self.assertEqual([entry["id"] for entry in self.runtime(output)["categories"]],
                         ["functional", "statistics", "external_media"])

    def test_optional_categories_start_unchecked_and_functional_is_locked_on(self) -> None:
        output = self.render("{{ consent_card('consent', config) }}")
        switches = re.findall(r'<input [^>]*role="switch"[^>]*>', output)
        self.assertEqual(len(switches), 3)
        for switch, category in zip(switches, ["functional", "statistics", "external_media"]):
            self.assertIn(f'id="consent-category-{category}"', switch)
            self.assertIn(f'aria-labelledby="consent-categories-{category}-trigger"', switch)
        self.assertIn(" checked disabled", switches[0])
        for switch in switches[1:]:
            self.assertNotIn("checked", switch)
            self.assertNotIn("disabled", switch)

    def test_three_answers_carry_equal_weight(self) -> None:
        output = self.render("{{ consent_card('consent', config) }}")
        buttons = re.findall(r'<button class="([^"]+)" id="consent-(accept|decline|save)"', output)
        self.assertEqual([suffix for _, suffix in buttons], ["accept", "decline", "save"])
        self.assertEqual(len({classes for classes, _ in buttons}), 1)

    def test_runtime_config_carries_ids_cookie_and_removable_storage_only(self) -> None:
        runtime = self.runtime(self.render("{{ consent_card('consent', config) }}"))
        self.assertEqual(runtime["revision"], "7b2ac531ea92")
        self.assertEqual(runtime["cookie"], {"name": "moo_consent", "days": 365})
        self.assertEqual(runtime["categories"][0], {"id": "functional", "required": True})
        self.assertEqual(runtime["categories"][1]["storage"], [{"name": "_pk_id.*", "type": "cookie"}])
        self.assertEqual(runtime["categories"][2]["storage"], [{"name": "yt*", "type": "local"}])
        self.assertNotIn("Statistics", json.dumps(runtime))

    def test_text_is_escaped_and_runtime_json_cannot_close_its_script(self) -> None:
        config = json.loads(json.dumps(CONFIG))
        config["revision"] = "</script><b>"
        output = self.render("{{ consent_card('consent', config) }}", config=config)
        self.assertIn("Needed &lt;always&gt;", output)
        self.assertEqual(output.count("</script>"), 1)

    def test_invalid_configurations_fail(self) -> None:
        cases = {
            "revision": {**CONFIG, "revision": ""},
            "required": {**CONFIG, "categories": [{"id": "statistics", "label": "S", "required": True,
                                                    "services": [{"id": "a", "name": "A"}]}]},
            "storage type": {**CONFIG, "categories": [{"id": "statistics", "label": "S", "services": [
                {"id": "a", "name": "A", "storage": [{"name": "x", "type": "indexeddb"}]}]}]},
        }
        for name, config in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                self.render("{{ consent_card('consent', config) }}", config=config)

    def test_trigger_and_placeholder_use_plain_buttons(self) -> None:
        trigger = self.render("{{ consent_trigger('consent') }}")
        self.assertIn('type="button" data-consent-open="consent" aria-haspopup="dialog"', trigger)
        placeholder = self.render("{{ consent_placeholder('video', 'external_media', 'Video', 'Loads from Example.') }}")
        self.assertIn('data-consent-placeholder="external_media"', placeholder)
        self.assertIn('id="video-load" type="button" data-consent-grant="external_media"', placeholder)
        remember = re.search(r'<input [^>]*id="video-remember"[^>]*>', placeholder).group(0)
        self.assertIn("data-consent-remember", remember)
        self.assertNotIn("checked", remember)

    def test_button_rejects_consent_controls_combined_with_other_behaviour(self) -> None:
        template = create_environment().from_string(
            '{% from "components/button.html.jinja" import button %}'
            "{{ button('Settings', consent_open='consent', dialog_target='x') }}"
        )
        with self.assertRaises(ValueError):
            template.render()

    def test_policy_table_renders_one_table_per_shown_category(self) -> None:
        output = self.render("{{ consent_policy_table(config) }}")
        self.assertEqual(re.findall(r'data-consent-policy="([a-z_]+)"', output),
                         ["functional", "statistics", "external_media"])
        self.assertEqual(output.count("<table"), 3)
        self.assertIn('<th scope="row">Site session</th>', output)
        self.assertIn('href="https://example.test/privacy" rel="noopener noreferrer"', output)

    def test_labels_translate_every_visible_string(self) -> None:
        labels = {"title": "Einwilligung verwalten", "accept_all": "Alle akzeptieren", "decline": "Ablehnen",
                  "save": "Auswahl speichern", "types": {"cookie": "Cookie-Datei"}}
        output = self.render("{{ consent_card('consent', config, labels) }}", labels=labels)
        for text in labels.values():
            if isinstance(text, str):
                self.assertIn(text, output)
        self.assertIn("Cookie-Datei, 7 days", output)
        self.assertIn("Local storage", output)

    def test_catalog_revision_follows_the_documented_rule(self) -> None:
        self.assertEqual(revision(["functional/site", "statistics/matomo", "external_media/video"]), "7b2ac531ea92")
        self.assertNotEqual(revision(["functional/site"], reask=1), revision(["functional/site"]))
