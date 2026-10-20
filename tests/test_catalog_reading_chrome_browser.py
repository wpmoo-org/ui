from __future__ import annotations

import subprocess
import sys
import unittest

from playwright.sync_api import expect, sync_playwright

from tests.helpers import ROOT
from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_directory,
    skip_if_browser_launch_is_sandboxed,
)


class CatalogReadingChromeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        skip_if_browser_launch_is_sandboxed()
        result = subprocess.run([sys.executable, 'build.py'], cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.server = serve_directory(ROOT / 'site-dist')
        cls.base_url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = launch_certification_browser(cls.playwright)
        cls.addClassCleanup(cls.browser.close)

    def open_page(self, path='/introduction/', width=390, theme='light', direction='ltr', motion='reduce', touch=False):
        options = {'viewport': {'width': width, 'height': 844}, 'reduced_motion': motion}
        if touch:
            options.update(is_mobile=True, has_touch=True)
        context = self.browser.new_context(**options)
        self.addCleanup(context.close)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        self.addCleanup(evidence.assert_clean)
        page.goto(self.base_url + path)
        page.wait_for_function('document.querySelector("[data-catalog-reading-bar]").hasAttribute("data-catalog-reading-bar-visible")')
        page.evaluate('document.fonts.ready')
        page.evaluate('''([theme,direction])=>{
            document.querySelector('.moo-ui').dataset.bsTheme=theme;
            document.documentElement.dir=direction;
        }''', [theme, direction])
        return page

    def test_compact_reveal_fade_boundary_hysteresis_and_stable_layout(self):
        for theme, direction in (('light', 'ltr'), ('dark', 'rtl')):
            with self.subTest(theme=theme, direction=direction):
                page = self.open_page(theme=theme, direction=direction)
                panel = page.locator('[data-catalog-reading-bar]')
                main = page.locator('main#main-content')
                initial = main.bounding_box()
                expect(panel).to_be_hidden()
                self.assertTrue(panel.evaluate('(el)=>el.inert'))
                self.assertEqual(main.evaluate('(el)=>getComputedStyle(el).maskImage'), 'none')
                for y, visible in ((350, False), (700, True), (350, True), (200, False)):
                    main.evaluate('(el,y)=>el.scrollTo({top:y,behavior:"instant"})', y)
                    expect(panel).to_have_attribute('data-catalog-reading-bar-visible', str(visible).lower())
                    if visible:
                        expect(panel).to_be_visible()
                    else:
                        expect(panel).to_be_hidden()
                    page.wait_for_function('getComputedStyle(document.querySelector("main#main-content")).maskImage !== "none"')
                    page.wait_for_function(r'''visible=>{
                        const main=document.querySelector('main#main-content'),panel=document.querySelector('[data-catalog-reading-bar]');
                        return Math.abs(parseFloat(getComputedStyle(main).maskPosition.split(/\s+/)[1])-(visible?panel.getBoundingClientRect().height:0))<1;
                    }''', arg=visible)
                    current = main.bounding_box()
                    self.assertAlmostEqual(current['y'], initial['y'], delta=1)
                    self.assertAlmostEqual(current['height'], initial['height'], delta=1)
                    self.assertEqual(page.evaluate('scrollY'), 0)
                    self.assertNotEqual(main.evaluate('(el)=>getComputedStyle(el).maskImage'), 'none')
                main.evaluate('(el)=>el.scrollTo({top:0,behavior:"instant"})')
                page.wait_for_function('getComputedStyle(document.querySelector("main#main-content")).maskImage === "none"')

    def test_whole_bar_fades_in_place_and_fast_reversal_keeps_latest_state(self):
        page = self.open_page(motion='no-preference')
        trace = page.evaluate('''async()=>{
            const main=document.querySelector('main#main-content'),panel=document.querySelector('[data-catalog-reading-bar]');
            main.scrollTo({top:700,behavior:'instant'});
            const frames=[];
            for(let i=0;i<24;i++){
                await new Promise(requestAnimationFrame);
                const r=panel.getBoundingClientRect(),s=getComputedStyle(panel);
                frames.push({opacity:+s.opacity,height:r.height,transform:s.transform});
            }
            return frames;
        }''')
        self.assertTrue(any(0 < frame['opacity'] < 1 and frame['height'] > 0 for frame in trace))
        heights = [frame['height'] for frame in trace if frame['height'] > 0]
        self.assertLess(max(heights) - min(heights), 0.1)
        self.assertTrue(all(frame['transform'] == 'none' for frame in trace))
        page.evaluate('''async()=>{
            const main=document.querySelector('main#main-content');
            for(const y of [200,700,200,700]){
                main.scrollTo({top:y,behavior:'instant'});
                await new Promise(resolve=>setTimeout(resolve,35));
            }
        }''')
        page.wait_for_function('''()=>{const p=document.querySelector('[data-catalog-reading-bar]');return !p.hidden && +getComputedStyle(p).opacity===1;}''')
        page.emulate_media(reduced_motion='reduce')
        self.assertEqual(page.locator('[data-catalog-reading-bar]').evaluate('(el)=>getComputedStyle(el).transitionDuration'), '0s')
        page.evaluate('''async()=>{
            const script=document.querySelector('script[type="module"][src*="catalog/index"]');
            const module=await import(script.src);module.initCatalog(document)();
        }''')
        panel = page.locator('[data-catalog-reading-bar]')
        self.assertTrue(panel.evaluate('(el)=>el.hidden && el.inert && !el.hasAttribute("data-catalog-reading-bar-visible")'))
        self.assertEqual(page.locator('.scrollbar-overlay').count(), 0)

    def test_desktop_preserves_content_side_toc(self):
        page = self.open_page(width=1440)
        main = page.locator('main#main-content')
        initial = main.bounding_box()
        main.evaluate('(el)=>el.scrollTo({top:700,behavior:"instant"})')
        expect(page.locator('[data-catalog-reading-bar]')).to_be_hidden()
        expect(page.locator('#catalog-toc-list')).to_be_visible()
        self.assertNotEqual(main.evaluate('(el)=>getComputedStyle(el).maskImage'), 'none')
        self.assertAlmostEqual(main.bounding_box()['y'], initial['y'], delta=1)
        self.assertEqual(page.evaluate('scrollY'), 0)

    def test_every_catalog_shell_route_attaches_the_shared_scrollbar(self):
        routes = sorted(
            '/' + path.relative_to(ROOT / 'site-dist').as_posix().removesuffix('index.html')
            for path in (ROOT / 'site-dist').rglob('index.html')
            if 'data-moo-shell="catalog"' in path.read_text(encoding='utf-8')
        )
        self.assertTrue(routes)
        context = self.browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        self.addCleanup(context.close)
        page = context.new_page()
        evidence = BrowserEvidence(page)
        self.addCleanup(evidence.assert_clean)
        for route in routes:
            with self.subTest(route=route):
                page.goto(self.base_url + route)
                page.wait_for_selector('.scrollbar-overlay', state='attached')
                state = page.evaluate('''() => {
                    const main=document.querySelector('main#main-content');
                    const bar=document.querySelector('.scrollbar-overlay');
                    return {count:document.querySelectorAll('.scrollbar-overlay').length,
                        controls:bar.getAttribute('aria-controls'),
                        nativeHidden:main.classList.contains('scrollbar-overlay-native'),
                        horizontal:main.scrollWidth>main.clientWidth+1};
                }''')
                self.assertEqual(state['count'], 1)
                self.assertEqual(state['controls'], 'main-content')
                self.assertEqual(state['nativeHidden'], not state['horizontal'])
                if route == '/installation/':
                    # The accepted long-URL wrapping fix must keep the mobile
                    # reading region within its viewport, not merely fall back.
                    self.assertFalse(state['horizontal'])

    def test_failed_catalog_scrollbar_initialization_restores_host_state(self):
        page = self.open_page()
        result = page.evaluate('''async () => {
            const script=document.querySelector('script[type="module"][src*="catalog/index"]');
            const {initCatalog}=await import(script.src);
            initCatalog(document)();
            const main=document.querySelector('main#main-content');
            const original=main.classList.contains('no-scrollbar');
            const sheets=[...document.styleSheets];
            sheets.forEach(sheet=>sheet.disabled=true);
            const {initCatalogScrollbar}=await import('/assets/js/catalog/overlay-scrollbar.js');
            let rejected=false;
            try { initCatalogScrollbar(document); } catch { rejected=true; }
            const restored=main.classList.contains('no-scrollbar')===original;
            const remaining=document.querySelectorAll('.scrollbar-overlay').length;
            sheets.forEach(sheet=>sheet.disabled=false);
            const release=initCatalogScrollbar(document);
            const recovered=!!document.querySelector('.scrollbar-overlay');
            release();
            return {rejected,restored,remaining,recovered};
        }''')
        self.assertEqual(result, {'rejected': True, 'restored': True, 'remaining': 0, 'recovered': True})

    def test_visible_scrollbar_does_not_capture_a_second_touch_swipe_at_the_edge(self):
        if self.browser.browser_type.name != 'chromium':
            self.skipTest('Trusted touch-event injection in this contract uses Chromium CDP.')
        page = self.open_page(touch=True)
        main = page.locator('main#main-content')
        main.evaluate('(el)=>el.scrollTo({top:500,behavior:"instant"})')
        expect(page.get_by_role('scrollbar')).to_have_attribute('data-scrollbar-visible', 'true')
        self.assertEqual(page.get_by_role('scrollbar').evaluate('(el)=>getComputedStyle(el).pointerEvents'), 'none')
        cdp = page.context.new_cdp_session(page)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': 387, 'y': 650}]})
        page.wait_for_timeout(30)
        self.assertEqual(main.evaluate('(el)=>el.scrollTop'), 500)
        for y in range(620, 349, -30):
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': 387, 'y': y}]})
            page.wait_for_timeout(30)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        page.wait_for_function('document.getElementById("main-content").scrollTop > 520')
        self.assertEqual(page.evaluate('scrollY'), 0)

    def test_chart_gallery_uses_common_toc_and_retains_deep_links(self):
        for width in (390, 1440):
            with self.subTest(width=width):
                page = self.open_page(path='/charts/#chart-line', width=width)
                page.wait_for_function(r'''async()=>{
                    const entry=performance.getEntriesByType('resource').find(e=>/\/assets\/js\/components\/chart\.js/.test(e.name));
                    if(!entry)return false;
                    const {default:Chart}=await import(entry.name);
                    return document.querySelectorAll('.chart').length>0 && [...document.querySelectorAll('.chart')].every(el=>Chart.getInstance(el));
                }''')
                page.wait_for_function('''()=>{
                    const main=document.querySelector('main#main-content'),panel=document.querySelector('[data-catalog-reading-bar]');
                    const bottom=panel.getClientRects().length?panel.getBoundingClientRect().bottom:main.getBoundingClientRect().top;
                    const top=document.getElementById('chart-line').getBoundingClientRect().top;
                    return main.scrollTop>0 && top>=bottom-1 && top<bottom+100;
                }''')
                # The user explicitly retired the competing chart-only navigator.
                self.assertEqual(page.locator('.moo-chart-template-nav').count(), 0)
                selector = '#catalog-toc-compact' if width < 992 else '#catalog-toc-list'
                if width < 992:
                    page.locator(selector + ' button').click()
                link = page.locator(selector + ' a[href="#chart-bar"]')
                link.click()
                expect(link).to_have_attribute('aria-current', 'location')
                expect(page).to_have_url(self.base_url + '/charts/#chart-bar')
                self.assertEqual(page.evaluate('scrollY'), 0)
