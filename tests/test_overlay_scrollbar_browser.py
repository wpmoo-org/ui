from __future__ import annotations

import subprocess
import sys
import unittest

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT
from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)


FIXTURE = '''<!doctype html>
<html lang="en" dir="{{ direction }}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/dist/assets/css/moo-ui.css"><title>Scrollbar contract</title></head>
<body><div class="moo-ui" data-bs-theme="{{ theme }}">
{% from "components/button.html.jinja" import button %}
<main class="container py-3"><h1>Native scrolling</h1>
{{ button("Keep focus here") }}
{% if nested %}<div id="reader" class="overflow-auto border mt-3" style="height:18rem">{% endif %}
{% for index in range(80) %}<p>Reading section {{ index }}. Native content remains in its original scrollport.</p>{% endfor %}
{% if nested %}</div>{% endif %}
</main></div></body></html>'''


class OverlayScrollbarBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        skip_if_browser_launch_is_sandboxed()
        result = subprocess.run([sys.executable, 'build.py'], cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def open_fixture(self, *, nested=False, theme='light', direction='ltr', initialize=True, mobile=False):
        options = {'viewport': {'width': 390 if mobile else 1040, 'height': 844}, 'reduced_motion': 'reduce'}
        if self.browser.browser_type.name != 'firefox':
            options.update(is_mobile=mobile, has_touch=mobile)
        context = self.browser.new_context(**options)
        self.addCleanup(context.close)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        self.addCleanup(evidence.assert_clean)
        html = create_environment().from_string(FIXTURE).render(nested=nested, theme=theme, direction=direction)
        page.route('**/overlay-scrollbar-contract', lambda route: route.fulfill(content_type='text/html', body=html))
        page.goto(self.base_url + '/overlay-scrollbar-contract')
        page.evaluate('document.fonts.ready')
        page.evaluate('''async () => { window.Scrollbar = (await import('/src/js/components/overlay-scrollbar.js')).default; }''')
        if initialize:
            page.evaluate('''nested => {
                window.scrollbarRoot = nested ? document.getElementById('reader') : document.scrollingElement;
                window.scrollbar = new Scrollbar(document.querySelector('.moo-ui'), {
                    scrollElement: scrollbarRoot, hideDelay: 100, label: 'Reading position'
                });
            }''', nested)
        return page

    def test_import_is_explicit_and_package_exports_exist(self):
        page = self.open_fixture(initialize=False)
        self.assertEqual(page.locator('.scrollbar-overlay').count(), 0)
        self.assertFalse(page.locator('html').evaluate('(el) => el.classList.contains("scrollbar-overlay-native")'))
        exports = page.evaluate('''async () => ({
            direct: typeof (await import('/dist/js/overlay-scrollbar.js')).default,
            aggregate: typeof (await import('/dist/js/moo-ui.js')).OverlayScrollbar
        })''')
        self.assertEqual(exports, {'direct': 'function', 'aggregate': 'function'})

    def test_document_reveal_idle_width_and_accessible_position(self):
        """Check idle hiding with the pointer away from either scrollbar edge."""
        for theme, direction in (('light', 'ltr'), ('dark', 'rtl')):
            with self.subTest(theme=theme, direction=direction):
                page = self.open_fixture(theme=theme, direction=direction)
                page.mouse.move(
                    page.viewport_size['width'] / 2,
                    page.viewport_size['height'] / 2,
                )
                bar = page.get_by_role('scrollbar', name='Reading position')
                before = page.evaluate('document.documentElement.clientWidth')
                page.evaluate('window.scrollTo({top:400,behavior:"instant"})')
                expect(bar).to_have_attribute('data-scrollbar-visible', 'true')
                page.wait_for_function('document.querySelector(".scrollbar-overlay").getAttribute("aria-valuenow") === "400"')
                self.assertEqual(page.evaluate('document.documentElement.clientWidth'), before)
                self.assertEqual(page.locator('html').evaluate('(el) => el.clientWidth'), page.evaluate('innerWidth'))
                page.wait_for_function('!document.querySelector(".scrollbar-overlay").hasAttribute("data-scrollbar-visible")')
                self.assertEqual(bar.evaluate('(el) => +getComputedStyle(el).opacity'), 0)
                self.assertEqual(page.evaluate('document.documentElement.clientWidth'), before)
                self.assertEqual(bar.get_attribute('aria-orientation'), 'vertical')
                self.assertGreater(int(bar.get_attribute('aria-valuemax')), 400)
                bounds = bar.bounding_box()
                self.assertAlmostEqual(bounds['x'] if direction == 'rtl' else bounds['x'] + bounds['width'],
                                       0 if direction == 'rtl' else before, delta=1)

    def test_native_element_scrollport_and_track_geometry(self):
        for direction in ('ltr', 'rtl'):
            with self.subTest(direction=direction):
                page = self.open_fixture(nested=True, direction=direction)
                before = page.locator('#reader').evaluate('(el) => el.clientWidth')
                page.locator('#reader').evaluate('(el) => el.scrollTo({top:300,behavior:"instant"})')
                expect(page.get_by_role('scrollbar')).to_have_attribute('data-scrollbar-visible', 'true')
                self.assertEqual(page.evaluate('scrollY'), 0)
                self.assertEqual(page.locator('#reader').evaluate('(el) => el.clientWidth'), before)
                state = page.evaluate('''() => {
                    const root=document.getElementById('reader'), bar=document.querySelector('.scrollbar-overlay');
                    const r=root.getBoundingClientRect(),b=bar.getBoundingClientRect();
                    return {top:b.top,expectedTop:r.top+root.clientTop,bottom:b.bottom,
                        expectedBottom:r.top+root.clientTop+root.clientHeight,controls:bar.getAttribute('aria-controls')};
                }''')
                self.assertAlmostEqual(state['top'], state['expectedTop'], delta=1)
                self.assertAlmostEqual(state['bottom'], state['expectedBottom'], delta=1)
                self.assertEqual(state['controls'], 'reader')

    def test_initial_activation_removes_a_reserved_native_gutter(self):
        page = self.open_fixture(nested=True, initialize=False)
        page.locator('#reader').evaluate('''el => {
            el.style.cssText += ';scrollbar-gutter:stable;width:300px';
            const child=document.createElement('div');
            child.style.cssText='width:298px;height:1px';
            el.prepend(child);
        }''')
        before = page.locator('#reader').evaluate('(el)=>({client:el.clientWidth,scroll:el.scrollWidth})')
        self.assertGreater(before['scroll'], before['client'])
        page.evaluate('''() => {window.scrollbar=new Scrollbar(document.querySelector('.moo-ui'), {
            scrollElement:document.getElementById('reader')
        });}''')
        expect(page.get_by_role('scrollbar')).to_be_visible()
        self.assertEqual(page.locator('#reader').evaluate('(el)=>el.clientWidth'), 298)
        page.wait_for_timeout(100)
        self.assertEqual(page.locator('#reader').evaluate('(el)=>el.scrollWidth'), 298)

    def test_scroll_element_direction_overrides_its_theme_owners_direction(self):
        for owner_direction, direction in (('ltr', 'rtl'), ('rtl', 'ltr')):
            with self.subTest(owner=owner_direction, scroller=direction):
                page = self.open_fixture(nested=True, direction=owner_direction)
                page.locator('#reader').evaluate('(el,dir)=>el.dir=dir', direction)
                page.evaluate('scrollbar.refresh()')
                state = page.evaluate('''() => {
                    const root=document.getElementById('reader');
                    const bar=document.querySelector('.scrollbar-overlay');
                    const thumb=document.querySelector('.scrollbar-overlay-thumb');
                    const r=root.getBoundingClientRect(),b=bar.getBoundingClientRect(),t=thumb.getBoundingClientRect();
                    const rtl=getComputedStyle(root).direction==='rtl';
                    return {direction:getComputedStyle(bar).direction,
                        barGap:rtl?b.left-r.left-root.clientLeft:r.left+root.clientLeft+root.clientWidth-b.right,
                        gap:rtl?t.left-r.left-root.clientLeft:r.left+root.clientLeft+root.clientWidth-t.right};
                }''')
                self.assertEqual(state['direction'], direction)
                self.assertAlmostEqual(state['barGap'], 0, delta=1)
                self.assertAlmostEqual(state['gap'], 4, delta=1)

    def test_keyboard_controls_native_scroll_without_trapping_tab(self):
        page = self.open_fixture(nested=True)
        bar = page.get_by_role('scrollbar')
        bar.focus()
        bar.press('End')
        page.wait_for_function('scrollbarRoot.scrollTop === scrollbarRoot.scrollHeight - scrollbarRoot.clientHeight')
        bar.press('Home')
        page.wait_for_function('scrollbarRoot.scrollTop === 0')
        bar.press('PageDown')
        page.wait_for_function('scrollbarRoot.scrollTop > 0')
        bar.press('Tab')
        self.assertFalse(bar.evaluate('(el) => el === document.activeElement'))
        self.assertEqual(page.evaluate('scrollY'), 0)

    def test_pointer_drag_preserves_focus_and_hides_when_idle(self):
        page = self.open_fixture(nested=True)
        button = page.get_by_role('button', name='Keep focus here')
        button.focus()
        bar = page.get_by_role('scrollbar')
        rect = bar.bounding_box()
        thumb = page.locator('.scrollbar-overlay-thumb').bounding_box()
        x, y = rect['x'] + rect['width'] - 2, thumb['y'] + thumb['height'] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x, y + 60, steps=6)
        page.mouse.up()
        page.mouse.move(100, 10)
        self.assertGreater(page.locator('#reader').evaluate('(el) => el.scrollTop'), 0)
        expect(button).to_be_focused()
        page.wait_for_function('!document.querySelector(".scrollbar-overlay").hasAttribute("data-scrollbar-visible")')

    def test_touch_scrolling_remains_native(self):
        if self.browser.browser_type.name != 'chromium':
            self.skipTest('Trusted touch-event injection in this contract uses Chromium CDP.')
        page = self.open_fixture(mobile=True)
        cdp = page.context.new_cdp_session(page)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': 180, 'y': 650}]})
        for y in range(620, 349, -30):
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': 180, 'y': y}]})
            page.wait_for_timeout(40)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        page.wait_for_function('scrollY > 0')
        self.assertEqual(page.evaluate('document.scrollingElement === scrollbarRoot'), True)
        page.wait_for_function('!document.querySelector(".scrollbar-overlay").hasAttribute("data-scrollbar-visible")')
        self.assertEqual(page.get_by_role('scrollbar').evaluate('(el) => +getComputedStyle(el).opacity'), 0)

    def test_native_fallback_scroll_locks_and_reduced_motion(self):
        page = self.open_fixture()
        bar = page.get_by_role('scrollbar')
        page.emulate_media(forced_colors='active')
        expect(bar).to_be_hidden()
        self.assertFalse(page.locator('html').evaluate('(el) => el.classList.contains("scrollbar-overlay-native")'))
        page.emulate_media(forced_colors='none', reduced_motion='reduce')
        expect(bar).to_be_visible()
        self.assertEqual(bar.evaluate('(el) => getComputedStyle(el).transitionDuration'), '0s')
        page.evaluate('document.body.style.overflow = "hidden"')
        expect(bar).to_be_hidden()
        self.assertEqual(page.evaluate('document.body.style.overflow'), 'hidden')
        page.evaluate('document.body.style.removeProperty("overflow")')
        expect(bar).to_be_visible()
        page.evaluate('''() => {const wide=document.createElement('div');wide.id='wide';wide.style.cssText='width:200vw;height:1px';document.body.append(wide);}''')
        expect(bar).to_be_hidden()
        self.assertFalse(page.locator('html').evaluate('(el) => el.classList.contains("scrollbar-overlay-native")'))
        page.locator('#wide').evaluate('(el) => el.remove()')
        expect(bar).to_be_visible()

    def test_lifecycle_idempotence_and_owner_boundaries(self):
        page = self.open_fixture()
        result = page.evaluate('''() => {
            const owner=document.querySelector('.moo-ui');
            const same=Scrollbar.getOrCreateInstance(owner)===scrollbar && Scrollbar.getInstance(owner)===scrollbar;
            let rejected=0;
            const other=document.createElement('div');other.className='moo-ui';other.dataset.bsTheme='dark';
            const target=document.createElement('div');other.append(target);document.body.append(other);
            for(const action of [()=>new Scrollbar(owner,{hideDelay:-1}),()=>new Scrollbar(owner,{label:''}),
                ()=>new Scrollbar(owner,{scrollElement:target}),()=>new Scrollbar(other)]) {
                try{action();}catch{rejected++;}
            }
            window.dispatchEvent(new Event('resize'));
            scrollbar.dispose();scrollbar.dispose();
            return {same,rejected,remaining:document.querySelectorAll('.scrollbar-overlay').length,
                id:document.documentElement.getAttribute('id'),disposed:Scrollbar.getInstance(owner)===null,
                native:document.documentElement.classList.contains('scrollbar-overlay-native')};
        }''')
        self.assertEqual(result, {'same': True, 'rejected': 4, 'remaining': 0, 'id': None, 'disposed': True, 'native': False})
        page.wait_for_timeout(150)

    def test_missing_stylesheet_keeps_native_scrollbar(self):
        page = self.open_fixture(initialize=False)
        page.locator('link[rel="stylesheet"]').evaluate('(el) => el.remove()')
        self.assertTrue(page.evaluate('''() => {
            try{new Scrollbar(document.querySelector('.moo-ui'));}catch{return !document.documentElement.classList.contains('scrollbar-overlay-native') && !document.querySelector('.scrollbar-overlay');}
            return false;
        }'''))
