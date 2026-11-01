"""Password feedback contracts, including the standalone browser lifecycle."""

from __future__ import annotations

import subprocess
import sys
import unittest
from html.parser import HTMLParser

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT
from tests.helpers.browser_harness import launch_certification_browser


class ParsedMarkup(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.nodes = []
        self.text = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def handle_data(self, text):
        self.text.append(text)


class PasswordRequirementsTests(unittest.TestCase):
    def test_button_identity_is_available_and_escaped_for_native_control_binding(self) -> None:
        template = create_environment().from_string(
            '{% from "components/button.html.jinja" import button %}'
            '{{ button("Continue", element=element, id=identity) }}'
        )
        for element in ('button', 'input', 'a'):
            output = template.render(element=element, identity='target" autofocus="bad')
            parsed = ParsedMarkup(output)
            control = next(attrs for tag, attrs in parsed.nodes if tag == element)
            self.assertEqual(control['id'], 'target" autofocus="bad')
            self.assertNotIn('autofocus', control)

    def test_public_import_is_side_effect_free(self) -> None:
        program = '''
            globalThis.document = new Proxy({}, {
                get() { throw new Error("import touched document"); },
            });
            const {default: Requirements, passwordRequirementStates} =
                await import("./src/js/components/password-requirements.js");
            if (typeof Requirements.getOrCreateInstance !== "function" ||
                typeof Requirements.getInstance !== "function" ||
                typeof passwordRequirementStates !== "function") process.exit(1);
        '''
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", program],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_description_exposes_native_hidden_and_live_semantics(self) -> None:
        template = create_environment().from_string(
            '{% from "components/field.html.jinja" import field_description %}'
            '{{ field_description("warning", text, hidden=true, live="polite") }}'
        )
        output = template.render(text='<Repeated pattern>')
        parsed = ParsedMarkup(output)
        attrs = parsed.nodes[0][1]
        self.assertIn('hidden', attrs)
        self.assertEqual(attrs['aria-live'], 'polite')
        self.assertEqual(attrs['aria-atomic'], 'true')
        self.assertEqual(''.join(parsed.text).strip(), '<Repeated pattern>')

    def test_field_feedback_list_preserves_linked_escaped_items(self) -> None:
        template = create_environment().from_string('''
            {% from "components/field.html.jinja" import field_group, field_description %}
            {% call field_group(as_list=true) %}
              {{ field_description("warning-item", "<Choose another value>", list_item=true, hidden=true) }}
            {% endcall %}
        ''')
        output = template.render()
        parsed = ParsedMarkup(output)
        self.assertEqual([tag for tag, _ in parsed.nodes], ['ul', 'li'])
        self.assertEqual(parsed.nodes[1][1]['id'], 'warning-item')
        self.assertIn('hidden', parsed.nodes[1][1])
        self.assertEqual(''.join(parsed.text).strip(), '<Choose another value>')

    def test_requirements_are_not_a_strength_estimator(self) -> None:
        result = subprocess.run(
            ['node', '--input-type=module', '--eval', '''
                import {passwordRequirementStates} from './src/js/components/password-requirements.js';
                const policy={minlength:12,maxlength:128,whitespace:' ',rules:
                  ['length','case','number','symbol','maximum'].map(key=>({key,label:key}))};
                const states=passwordRequirementStates('Password123!',policy);
                if(!states.every(state=>state.met) || states.some(state=>'score' in state)) process.exit(1);
                if(passwordRequirementStates('x'.repeat(129),policy).find(s=>s.key==='maximum').met) process.exit(2);
            '''], cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_local_rules_optional_analysis_reset_and_disposal(self) -> None:
        # This unittest is also supported standalone, with no generated dist.
        subprocess.run([sys.executable, 'build.py', '--core'], cwd=ROOT,
                       check=True, capture_output=True, text=True)
        template = create_environment().from_string('''
            {% from "includes/password-feedback-preview.html.jinja" import password_feedback_preview %}
            <!doctype html><html><body><main class="moo-ui">
            {{ password_feedback_preview() }}
            <script src="/bootstrap.js"></script>
            </main></body></html>
        ''')
        module_url = "http://requirements.invalid/modules/password-requirements.js"
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                page = browser.new_page()
                def respond(route):
                    name = route.request.url.rsplit('/', 1)[-1]
                    if name == 'password-requirements.js':
                        route.fulfill(body=(ROOT / 'dist/js' / name).read_bytes(), content_type='text/javascript')
                    elif name == 'bootstrap.js':
                        route.fulfill(body=(ROOT / 'vendor/bootstrap/dist/js/bootstrap.bundle.min.js').read_bytes(), content_type='text/javascript')
                    else:
                        route.fulfill(body=template.render(), content_type='text/html')
                page.route("http://requirements.invalid/**", respond)
                page.goto("http://requirements.invalid/probe")
                page.evaluate('''async url => {
                    const {default: Requirements} = await import(url);
                    window.fetch = () => { throw new Error('Local feedback must not send requests'); };
                    for (const name of ['localStorage', 'sessionStorage']) {
                        Object.defineProperty(window, name, {
                            get() { throw new Error('Local feedback must not persist secrets'); },
                        });
                    }
                    window.Requirements = Requirements;
                    window.changes = [];
                    const root = document.querySelector('#password-preview-requirements');
                    root.dataset.requirementsReady = 'host-ready';
                    root.querySelector('[id$="-length"]').dataset.requirementMet = 'host-met';
                    window.instance = Requirements.getOrCreateInstance(root, {
                        onChange: states => window.changes.push(states),
                    });
                    await window.instance.ready;
                }''', module_url)
                prefix = '#password-preview-requirements-'
                self.assertTrue(page.evaluate('''() => {
                    const ids = [...document.querySelectorAll('#password-preview-requirements [id]')].map(node => node.id);
                    return new Set(ids).size === ids.length;
                }'''))
                warning = page.locator(prefix + 'maximum')
                submit = page.locator('#password-preview-submit')
                expect(submit).to_be_disabled()
                page.locator('#password-preview-input').fill('glacier maple lantern harbor !')
                page.locator('#password-preview-confirm').fill('glacier maple lantern harbor !')
                expect(submit).to_be_disabled()
                page.locator('#password-preview-requirements-submit-hint').focus()
                expect(page.locator('.tooltip.show')).to_contain_text('Upper and lower case')
                expect(page.locator('.tooltip.show')).to_contain_text('At least one number')
                page.locator('#password-preview-input').focus()
                expect(warning).to_be_hidden()
                page.locator('#password-preview-input').fill('Grove!82 ' + 'x' * 121)
                expect(page.locator(prefix + 'maximum')).to_be_visible()
                page.locator('#password-preview-input').fill('Fir!82meadow')
                for key in ('length', 'case', 'number', 'symbol'):
                    expect(page.locator(prefix + key)).to_have_attribute('data-requirement-met', 'true')
                expect(warning).to_be_hidden()
                page.locator('#password-preview-confirm').fill('Different fixture')
                expect(page.locator(prefix + 'confirmation')).to_be_visible()
                expect(submit).to_be_disabled()
                self.assertTrue(page.evaluate('''() => {
                    const event=new Event('submit',{bubbles:true,cancelable:true});
                    document.querySelector('#password-preview-input').form.dispatchEvent(event);
                    return event.defaultPrevented;
                }'''))
                page.locator('#password-preview-confirm').fill('Fir!82meadow')
                expect(page.locator(prefix + 'confirmation')).to_be_hidden()
                expect(submit).to_be_enabled()
                expect(page.locator('#password-preview-requirements-submit-hint')).not_to_have_attribute('role', 'button')
                expect(page.locator('#password-preview-strength')).to_have_count(0)
                expect(page.locator(prefix + 'summary')).to_contain_text('Shown checks met.')
                self.assertTrue(page.evaluate('''() => {
                    const root = document.querySelector('#password-preview-requirements');
                    return !root.textContent.includes('Fir!82meadow') &&
                        !root.dataset.passwordRequirements.includes('Fir!82meadow') &&
                        changes.every(states => states.every(state =>
                            Object.keys(state).sort().join(',') === 'key,met' && typeof state.met === 'boolean'));
                }'''))
                page.locator('#password-preview-input').evaluate('input => input.form.reset()')
                expect(submit).to_be_disabled()
                expect(page.locator('#password-preview-input')).to_have_value('')
                expect(warning).to_be_hidden()
                expect(page.locator(prefix + 'length')).to_have_attribute('data-requirement-met', 'false')
                self.assertTrue(page.evaluate('''() => {
                    const root = document.querySelector('#password-preview-requirements');
                    const previous = instance;
                    previous.dispose();
                    instance = Requirements.getOrCreateInstance(root);
                    previous.dispose();
                    return Requirements.getInstance(root) === instance;
                }'''))
                page.evaluate('window.instance.dispose()')
                expect(warning).to_be_hidden()
                expect(page.locator('#password-preview-requirements-submit-hint')).to_be_hidden()
                expect(submit).to_be_disabled()
                self.assertTrue(page.evaluate('''() => {
                    const root=document.querySelector('#password-preview-requirements');
                    return Requirements.getInstance(root) === null &&
                        root.dataset.requirementsReady === 'host-ready' &&
                        root.querySelector('[id$="-length"]').dataset.requirementMet === 'host-met' &&
                        !root.querySelector('[id$="-maximum"]').hasAttribute('data-requirement-met');
                }'''))
                self.assertTrue(page.evaluate('''() => {
                    const root=document.querySelector('#password-preview-requirements');
                    const input=document.querySelector('#password-preview-input');
                    const confirm=document.querySelector('#password-preview-confirm');
                    const submit=document.querySelector('#password-preview-submit');
                    input.value=confirm.value='Password123!';
                    let score=null;
                    const instance=Requirements.getOrCreateInstance(root,{
                        analyze:()=>({met:false,score:1}),
                        onChange:(states,active,value)=>{score=value;},
                    });
                    const blocked=submit.disabled && score===1;
                    instance.dispose();
                    const noEstimator=Requirements.getOrCreateInstance(root,{
                        onChange:(states,active,value)=>{score=value;},
                    });
                    const allowed=!submit.disabled && score===null;
                    noEstimator.dispose();
                    input.value=confirm.value='   ';
                    let called=false;
                    const whitespace=Requirements.getOrCreateInstance(root,{
                        analyze:()=>{called=true; throw new Error('Must not analyze empty input');},
                    });
                    const emptyBlocked=submit.disabled && !called;
                    whitespace.dispose();
                    const original=document.querySelector('#password-preview-requirements-submit-hint');
                    const parent=submit.parentNode;
                    const Tooltip=bootstrap.Tooltip;
                    delete bootstrap.Tooltip;
                    let missingRejected=false;
                    try { Requirements.getOrCreateInstance(root); } catch { missingRejected=true; }
                    bootstrap.Tooltip=Tooltip;
                    const untouched=submit.parentNode===parent && original.hidden;
                    const create=bootstrap.Tooltip.getOrCreateInstance;
                    bootstrap.Tooltip.getOrCreateInstance=()=>{throw new Error('Fixture failure');};
                    let failed=false;
                    try { Requirements.getOrCreateInstance(root); } catch { failed=true; }
                    bootstrap.Tooltip.getOrCreateInstance=create;
                    return blocked && allowed && emptyBlocked && missingRejected && untouched && failed && submit.parentNode===parent &&
                        original.hidden && Requirements.getInstance(root)===null;
                }'''))
                self.assertTrue(page.evaluate('''() => {
                    const root=document.querySelector('#password-preview-requirements');
                    const original=root.dataset.passwordRequirements;
                    const config=JSON.parse(original);
                    config.confirmation=config.input;
                    root.dataset.passwordRequirements=JSON.stringify(config);
                    let rejected=false;
                    try { Requirements.getOrCreateInstance(root); } catch (error) {
                        rejected=error instanceof TypeError;
                    }
                    root.dataset.passwordRequirements=original;
                    return rejected && Requirements.getInstance(root)===null;
                }'''))
                self.assertTrue(page.evaluate('''() => {
                    const root=document.querySelector('#password-preview-requirements');
                    const hint=document.querySelector('#password-preview-requirements-submit-hint');
                    const input=document.querySelector('#password-preview-input');
                    input.value='';
                    const outcomes=[];
                    for (const enabled of [true,false]) {
                        const host=new bootstrap.Tooltip(hint,{animation:false});
                        if (!enabled) host.disable();
                        const feedback=Requirements.getOrCreateInstance(root);
                        feedback.dispose();
                        hint.hidden=false;
                        host.show();
                        const shown=Boolean(document.querySelector('.tooltip.show'));
                        outcomes.push(bootstrap.Tooltip.getInstance(hint)===host && shown===enabled);
                        host.dispose();
                        hint.hidden=true;
                    }
                    return outcomes.every(Boolean);
                }'''))
            finally:
                browser.close()
