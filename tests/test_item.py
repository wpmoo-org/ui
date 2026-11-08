import re
import unittest

from markupsafe import Markup

from build import ROOT, _load_evidence_index, create_environment


class ItemTests(unittest.TestCase):
    def render(self, source, **values):
        template = create_environment().from_string(
            '{% from "components/item.html.jinja" import item, item_group %}' + source
        )
        return template.render(**values)

    def render_item(self, **values):
        return self.render('{{ item(**values) }}', values=values)

    def test_text_href_and_class_values_are_escaped(self):
        output = self.render_item(
            title='<Alert>',
            description='<Check>',
            href='/a" onclick="bad',
            extra_class='x" onclick="bad',
        )
        self.assertIn('&lt;Alert&gt;', output)
        self.assertIn('&lt;Check&gt;', output)
        self.assertIn('href="/a&#34; onclick=&#34;bad"', output)
        self.assertIn('x&#34; onclick=&#34;bad', output)

    def test_visible_text_is_required(self):
        with self.assertRaisesRegex(Exception, 'Item title or description is required'):
            self.render_item(title=' ', description='')

    def test_variants_and_sizes_map_to_public_classes(self):
        cases = {
            ('default', 'default'): 'item',
            ('outline', 'default'): 'item item-outline',
            ('muted', 'sm'): 'item item-muted item-sm',
        }
        for (variant, size), classes in cases.items():
            with self.subTest(variant=variant, size=size):
                output = self.render_item(title='Row', variant=variant, size=size)
                self.assertIn(f'class="{classes}"', output)

    def test_unknown_variant_size_and_media_variant_fail(self):
        for values, message in (
            ({'variant': 'ghost'}, 'Unknown item variant'),
            ({'size': 'lg'}, 'Unknown item size'),
            ({'media': Markup('<svg data-icon="inline-start"></svg>'), 'media_variant': 'avatar'}, 'Unknown item media variant'),
        ):
            with self.subTest(values=values):
                with self.assertRaisesRegex(Exception, message):
                    self.render_item(title='Row', **values)

    def test_icon_media_is_framed_and_decorative(self):
        output = self.render_item(title='Row', media=Markup('<svg data-icon="inline-start"></svg>'))
        self.assertRegex(output, r'<div class="item-media item-media-icon" aria-hidden="true"><svg')

    def test_link_item_renders_one_anchor_and_refuses_actions(self):
        output = self.render_item(title='Docs', href='/docs/')
        self.assertRegex(output, r'^\s*<a class="item" href="/docs/">')
        self.assertNotIn('<div class="item"', output)
        with self.assertRaisesRegex(Exception, 'A link item cannot also hold an action'):
            self.render_item(title='Docs', href='/docs/', action=Markup('<button>Go</button>'))

    def test_action_renders_in_actions_slot(self):
        output = self.render_item(title='Alert', action=Markup('<button type="button">Review</button>'))
        self.assertIn('<div class="item-actions"><button type="button">Review</button></div>', output)

    def test_group_renders_items_as_list_items(self):
        output = self.render(
            '{% call item_group() %}'
            '{{ item("One", listitem=true) }}{{ item("Two", listitem=true) }}'
            '{% endcall %}'
        )
        self.assertRegex(output, r'^\s*<ul class="item-group">')
        self.assertEqual(len(re.findall(r'<li>\s*<div class="item">', output)), 2)

    def test_source_evidence_does_not_claim_release_certification(self):
        evidence = _load_evidence_index()['item']
        self.assertEqual(evidence['latestEvidence']['status'], 'source-checked')
        self.assertFalse(evidence['accepted'])

    def test_media_frame_spans_title_gap_and_first_description_line(self):
        # Accepted on 2026-11-08: the icon frame's top and bottom edges align
        # with the title's top and the first description line's bottom.
        source = (ROOT / 'scss/components/_item.scss').read_text(encoding='utf-8')
        self.assertIn(
            '$item-media-size: ($font-size-sm * $item-title-line-height) + $item-content-gap'
            ' + ($font-size-sm * $item-description-line-height);',
            source,
        )
        for rule, declarations in (
            ('.item-media-icon', ('width: $item-media-size;', 'height: $item-media-size;')),
            ('.item-content', ('gap: $item-content-gap;',)),
            ('.item-title', ('line-height: $item-title-line-height;',)),
            ('.item-description', ('line-height: $item-description-line-height;',)),
        ):
            block = re.search(re.escape(rule) + r' \{(.*?)\}', source, re.DOTALL).group(1)
            for declaration in declarations:
                with self.subTest(rule=rule, declaration=declaration):
                    self.assertIn(declaration, block)


if __name__ == '__main__':
    unittest.main()
