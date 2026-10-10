import importlib.util
import json
from pathlib import Path
import tempfile

from markupsafe import Markup

from build import create_environment, _load_evidence_index
from tests.helpers import ROOT, CatalogTestCase


class EmptyTests(CatalogTestCase):
    def test_source_candidate_is_excluded_from_release_certification(self):
        inventory = json.loads((ROOT / 'src/certification/evidence-inventory.json').read_text())
        for name in ('manifest', 'attestation'):
            with self.subTest(generator=name):
                script = ROOT / ('scripts/build-certification-%s.py' % name)
                spec = importlib.util.spec_from_file_location('certification_' + name, script)
                generator = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(generator)
                components = generator.certified_components(inventory) if name == 'manifest' else generator.certified_components()
                slugs = {component['slug'] for component in components}
                self.assertNotIn('empty', slugs)
                self.assertIn('card', slugs)

    def test_ordinary_component_still_requires_accepted_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / 'inventory.json'
            evidence = Path(directory) / 'evidence.json'
            inventory.write_text(json.dumps({
                'profiles': {'static': {'tier': 0}},
                'components': [{'slug': 'button', 'profile': 'static'}],
            }))
            evidence.write_text(json.dumps({'components': [{
                'slug': 'button', 'tier': 0, 'profile': 'static', 'status': 'source-checked',
            }]}))
            with self.assertRaisesRegex(RuntimeError, 'Missing accepted evidence record for components: button'):
                _load_evidence_index(inventory, (evidence,))

    def test_source_evidence_does_not_claim_visual_acceptance(self):
        evidence = _load_evidence_index()['empty']
        self.assertEqual(evidence['latestEvidence']['status'], 'source-checked')
        self.assertFalse(evidence['accepted'])
        self.assertEqual(evidence['acceptedEvidence'], [])

    def render_empty(self, **values):
        self.assertTrue((ROOT / 'src/components/empty.html.jinja').is_file(), 'Empty composition is not implemented')
        template = create_environment().from_string(
            '{% from "components/empty.html.jinja" import empty %}'
            '{{ empty(**values) }}'
        )
        return template.render(values=values)

    def test_message_and_class_values_are_escaped(self):
        output = self.render_empty(title='<No items>', description='<Try again>', extra_class='x" onclick="bad')
        self.assertIn('&lt;No items&gt;', output)
        self.assertIn('&lt;Try again&gt;', output)
        self.assertIn('x&#34; onclick=&#34;bad', output)

    def test_visible_message_is_required(self):
        for values in ({}, {'title': ' ', 'description': ' '}):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, 'Empty title or description is required'):
                self.render_empty(**values)
        self.assertIn('Try again', self.render_empty(description='Try again'))

    def test_captured_icon_and_action_keep_their_semantics(self):
        output = self.render_empty(
            title='No items yet', icon=Markup('<svg aria-hidden="true" width="24" height="24"></svg>'),
            action=Markup('<button type="button">Create item</button>'),
        )
        self.assertIn('<svg aria-hidden="true" width="24" height="24"></svg>', output)
        self.assertIn('<button type="button">Create item</button>', output)
