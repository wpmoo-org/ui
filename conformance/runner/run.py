#!/usr/bin/env python3
"""Reference runner for the Moo UI Generic Host Conformance Kit.

Drives the kit's five canonical fixtures against a host serving them at
``--base-url`` and emits a JSON report conforming to
``conformance/contract/report.schema.json``.

The runner is host-neutral by design: it only assumes the contract fixture
paths resolve relative to ``--base-url`` and that kit assets are served
same-origin. It imports nothing from this repository's test suite, so the
kit can ship standalone.

All scenario waits are event- or poll-based; the only bounded timeout is
the inert-before-init check, where the *absence* of an opened marker is
the expected outcome. Per the Task 4 independent verification note, the
``openedMarker`` check is a visibility check (element exists AND is
visible), never a DOM-presence check.

Exit codes: 0 = conformance pass, 1 = conformance fail, 2 = usage error.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

KIT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = KIT_ROOT / "contract" / "conformance-contract.json"
REPORT_SCHEMA_VERSION = "1.0"
RUNNER_NAME = "moo-ui-conformance-reference-runner"
RUNNER_VERSION = "1.0"

NAVIGATION_TIMEOUT_MS = 30_000
SCENARIO_TIMEOUT_MS = 4_000
INERT_POLL_TIMEOUT_MS = 1_000
MAX_TAB_FALLBACK = 40
VIEWPORT = {"width": 1280, "height": 900}
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
FAVICON_PATH = "/favicon.ico"
MOO_ESM_READY_JS = "() => document.body.dataset.mooEsmReady === 'true'"

READ_MANY_JS = """
(args) => {
  return Array.from(document.querySelectorAll(args.selectorAll)).map((element) => {
    const style = getComputedStyle(element);
    const values = {};
    for (const property of args.properties) {
      values[property] = style.getPropertyValue(property);
    }
    return values;
  });
}
"""

READ_ONE_JS = """
(args) => {
  const element = document.querySelector(args.selector);
  if (!element) return null;
  const style = getComputedStyle(element);
  const values = {};
  for (const property of args.properties) {
    values[property] = style.getPropertyValue(property);
  }
  return values;
}
"""

MARKER_STATE_JS = """
(selector) => {
  const elements = Array.from(document.querySelectorAll(selector));
  const visible = elements.some((element) => {
    if (element.hidden) return false;
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return element.getClientRects().length > 0;
  });
  return { count: elements.length, visible };
}
"""

MARKER_VISIBLE_JS = """
(selector) => {
  return Array.from(document.querySelectorAll(selector)).some((element) => {
    if (element.hidden) return false;
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return element.getClientRects().length > 0;
  });
}
"""

THEME_TOGGLE_JS = """
(args) => {
  const root = document.documentElement;
  const read = () => {
    const element = document.querySelector(args.selector);
    return element ? getComputedStyle(element).getPropertyValue(args.property) : null;
  };
  root.removeAttribute(args.attribute);
  const light = read();
  root.setAttribute(args.attribute, "dark");
  const dark = read();
  root.removeAttribute(args.attribute);
  const restored = read();
  return {
    present: document.querySelector(args.selector) !== null,
    light,
    dark,
    restored,
  };
}
"""

DIRECTION_MIRROR_JS = """
(args) => {
  const root = document.documentElement;
  const read = () => {
    const element = document.querySelector(args.selector);
    if (!element) return null;
    const style = getComputedStyle(element);
    const values = {};
    for (const property of args.properties) {
      values[property] = style.getPropertyValue(property);
    }
    return values;
  };
  root.setAttribute("dir", "ltr");
  const ltr = read();
  root.setAttribute("dir", "rtl");
  const rtl = read();
  root.removeAttribute("dir");
  return { ltr, rtl };
}
"""

FOCUS_IN_SCOPE_JS = """
() => {
  const active = document.activeElement;
  return !!active && active !== document.body && !!active.closest(".moo-ui");
}
"""

FOCUS_MATCHES_JS = """
(selector) => {
  const active = document.activeElement;
  return !!active && active.matches(selector);
}
"""

FOCUS_INSIDE_OVERLAY_JS = """
(selector) => {
  const overlay = document.querySelector(selector);
  const active = document.activeElement;
  return !!overlay && !!active && active !== document.body && overlay.contains(active);
}
"""

Z_INDEX_JS = """
(selector) => {
  const element = document.querySelector(selector);
  return element ? getComputedStyle(element).zIndex : null;
}
"""

ACTIVE_IS_TRIGGER_JS = """
(selector) => document.activeElement === document.querySelector(selector)
"""

FOCUS_TREATMENT_JS = """
(selector) => {
  const element = document.querySelector(selector);
  if (!element) return null;
  const style = getComputedStyle(element);
  return { outlineStyle: style.outlineStyle, boxShadow: style.boxShadow };
}
"""

SCRIPT_SRCS_JS = "() => Array.from(document.scripts).map((s) => s.src).filter(Boolean)"

STYLESHEET_HREFS_JS = (
    "() => Array.from(document.styleSheets).map((s) => s.href).filter(Boolean)"
)

BOOTSTRAP_VERSION_JS = (
    "() => (window.bootstrap && window.bootstrap.Tooltip"
    " && window.bootstrap.Tooltip.VERSION) || null"
)

IDEMPOTENT_INIT_JS = """
(args) => {
  const api = window.__mooConformance;
  if (!api || !api[args.className]) return { ready: false };
  const root = document.querySelector(args.rootSelector);
  if (!root) return { ready: false, rootMissing: true };
  const first = api[args.className].getOrCreateInstance(root);
  const second = api[args.className].getOrCreateInstance(root);
  return { ready: true, identical: first === second };
}
"""

INVALID_ROOT_JS = """
(className) => {
  const api = window.__mooConformance;
  if (!api || !api[className]) return { ready: false };
  try {
    new api[className](document.createElement("div"));
    return { ready: true, threw: false };
  } catch (error) {
    return { ready: true, threw: true, errorName: error.name };
  }
}
"""

MODULE_CLASS_NAMES = {"combobox.js": "Combobox", "sidebar.js": "Sidebar"}

READY_MARKER_JS = {
    "moo-esm": MOO_ESM_READY_JS,
    "overlays": "() => document.body.dataset.overlaysReady === 'true'",
}


class Outcome:
    def __init__(self, status, evidence=None, reason=None):
        self.status = status
        self.evidence = evidence
        self.reason = reason


def _basename(url):
    return urlsplit(url).path.rsplit("/", 1)[-1]


def _is_favicon(url):
    return urlsplit(url).path == FAVICON_PATH


class FixtureState:
    """Everything the checks need for one fixture's run."""

    def __init__(self, browser, base_url, contract, fixture_meta, csp_policy):
        self.browser = browser
        self.base_url = base_url.rstrip("/")
        self.contract = contract
        self.fixture_meta = fixture_meta
        self.url = f"{self.base_url}/{fixture_meta['path']}"
        self.csp_policy = csp_policy
        recipe = next(
            entry
            for entry in contract["cssRecipes"]
            if entry["name"] == fixture_meta["cssRecipe"]
        )
        self.recipe_stylesheets = list(recipe["stylesheets"])
        self.console = []
        self.page_errors = []
        self.bad_responses = []
        self.failed_requests = []
        self.request_order = []
        self.page = None
        self.primary_context = None
        self.loaded = False
        self.load_status = None
        self.stylesheet_basenames = None
        self.discrete_recipe = False
        self.bootstrap_version = None
        self.pre_init_facts = None
        self._blocked_context = None
        self._blocked_page = None

    # -- context helpers -------------------------------------------------

    def _new_context(self):
        return self.browser.new_context(
            viewport=VIEWPORT,
            reduced_motion="reduce",
            locale="en-US",
        )

    def _install_csp(self, context):
        policy = self.csp_policy

        def handle(route: Route) -> None:
            response = route.fetch()
            headers = {**response.headers, "content-security-policy": policy}
            route.fulfill(response=response, headers=headers)

        context.route("**/*", handle)

    def _attach_listeners(self, page: Page) -> None:
        page.on("console", lambda m: self.console.append((m.type, m.text)))
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        page.on(
            "response",
            lambda r: self.bad_responses.append({"url": r.url, "status": r.status})
            if r.status >= 400 and not _is_favicon(r.url)
            else None,
        )
        page.on(
            "requestfailed",
            lambda req: self.failed_requests.append(
                {"url": req.url, "failure": req.failure}
            )
            if not _is_favicon(req.url)
            else None,
        )
        page.on("request", lambda req: self.request_order.append(req.url))

    # -- loads -----------------------------------------------------------

    def run_pre_init_pass(self, trigger_selector, opened_marker):
        """Load with the external init script blocked and interact.

        The bounded poll *expects to time out*: the opened marker must stay
        invisible while the component is inert.
        """
        context = self._new_context()
        context.route("**/init-moo-esm.js", lambda route: route.abort())
        page = context.new_page()
        facts = {"markerCount": 0, "markerVisible": False, "ariaExpanded": None}
        try:
            response = page.goto(self.url, wait_until="networkidle",
                                 timeout=NAVIGATION_TIMEOUT_MS)
            if response is None or not response.ok:
                facts["loadError"] = (
                    None if response is None else response.status
                )
                self.pre_init_facts = facts
                return
            page.locator(trigger_selector).first.click()
            try:
                page.wait_for_function(
                    MARKER_VISIBLE_JS,
                    arg=opened_marker,
                    timeout=INERT_POLL_TIMEOUT_MS,
                )
                opened = True
            except PlaywrightTimeoutError:
                opened = False
            marker = page.evaluate(MARKER_STATE_JS, opened_marker)
            facts = {
                "opened": opened,
                "markerCount": marker["count"],
                "markerVisible": marker["visible"],
                "ariaExpanded": page.locator(trigger_selector).first.get_attribute(
                    "aria-expanded"
                ),
            }
        finally:
            context.close()
        self.pre_init_facts = facts

    def load_primary(self):
        self.primary_context = self._new_context()
        self._install_csp(self.primary_context)
        self.page = self.primary_context.new_page()
        self._attach_listeners(self.page)
        try:
            response = self.page.goto(
                self.url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT_MS
            )
        except PlaywrightTimeoutError:
            self.loaded = False
            self.load_status = "navigation timeout"
            return
        if response is None:
            self.load_status = "no response"
            return
        self.load_status = response.status
        if not response.ok:
            return
        self.loaded = True
        hrefs = self.page.evaluate(STYLESHEET_HREFS_JS)
        self.stylesheet_basenames = {_basename(href) for href in hrefs}
        self.discrete_recipe = all(
            name in self.stylesheet_basenames for name in self.recipe_stylesheets
        )
        ready_js = READY_MARKER_JS.get(self.fixture_meta["name"])
        if ready_js:
            try:
                self.page.wait_for_function(ready_js, timeout=SCENARIO_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                pass  # dependent checks fail with their own evidence
        if self.fixture_meta.get("bootstrapJs"):
            self.bootstrap_version = self.page.evaluate(BOOTSTRAP_VERSION_JS)

    def blocked_page(self) -> Page:
        """A second load of the same fixture with moo.css route-blocked."""
        if self._blocked_page is None:
            self._blocked_context = self._new_context()
            self._blocked_context.route("**/moo.css", lambda route: route.abort())
            self._blocked_page = self._blocked_context.new_page()
            self._blocked_page.goto(
                self.url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT_MS
            )
        return self._blocked_page

    # -- scenario helpers --------------------------------------------------

    def locator_visible(self, selector):
        return self.page.locator(selector).first.is_visible()

    def ensure_overlay_open(self, trigger, overlay):
        if not self.locator_visible(overlay):
            self.page.locator(trigger).first.click()
        self.page.locator(overlay).first.wait_for(
            state="visible", timeout=SCENARIO_TIMEOUT_MS
        )

    def ensure_overlay_closed(self, trigger, overlay):
        if self.locator_visible(overlay):
            self.page.locator(trigger).first.click()
            self.page.locator(overlay).first.wait_for(
                state="hidden", timeout=SCENARIO_TIMEOUT_MS
            )

    def focus_body(self):
        self.page.evaluate("() => document.body.focus()")

    def close(self):
        for context in (self._blocked_context, self.primary_context):
            if context is not None:
                context.close()
        self._blocked_page = None
        self.page = None


# -- checks ----------------------------------------------------------------


def check_computed_equals(state, params):
    if "selectorAll" in params:
        exclude = params.get("excludeSelector")
        values = state.page.evaluate(
            """
            (args) => {
              const matches = Array.from(
                document.querySelectorAll(args.selectorAll)
              );
              const kept = args.exclude
                ? matches.filter((el) => !el.matches(args.exclude))
                : matches;
              return kept.map((el) =>
                getComputedStyle(el).getPropertyValue(args.property)
              );
            }
            """,
            {
                "selectorAll": params["selectorAll"],
                "exclude": exclude,
                "property": params["property"],
            },
        )
        if not values:
            return Outcome(
                "fail",
                evidence={"matched": 0},
                reason=f"no elements matched {params['selectorAll']}",
            )
        mismatches = [value for value in values if value != params["expected"]]
        status = "pass" if not mismatches else "fail"
        return Outcome(
            status,
            evidence={
                "matched": len(values),
                "mismatchCount": len(mismatches),
                "mismatches": mismatches[:5],
            },
            reason=None if status == "pass"
            else f"{len(mismatches)} of {len(values)} elements did not compute "
            f"{params['property']} to {params['expected']}",
        )
    value = state.page.evaluate(
        "(args) => { const el = document.querySelector(args.selector);"
        " return el ? getComputedStyle(el).getPropertyValue(args.property) : null; }",
        {"selector": params["selector"], "property": params["property"]},
    )
    if value is None:
        return Outcome(
            "fail",
            evidence={"selector": params["selector"]},
            reason=f"selector {params['selector']} matched no element",
        )
    status = "pass" if value == params["expected"] else "fail"
    return Outcome(
        status,
        evidence={"actual": value, "expected": params["expected"]},
        reason=None if status == "pass"
        else f"computed {params['property']} is {value}, expected {params['expected']}",
    )


def check_stylesheets_loaded(state, params):
    present = [
        name for name in state.recipe_stylesheets
        if name in state.stylesheet_basenames
    ]
    if not present:
        return Outcome(
            "skipped",
            evidence={"observed": sorted(state.stylesheet_basenames)},
            reason="host concatenates or inlines styles; no discrete recipe "
            "stylesheets observable",
        )
    missing = [name for name in state.recipe_stylesheets if name not in present]
    if missing:
        return Outcome(
            "fail",
            evidence={"observed": sorted(state.stylesheet_basenames), "missing": missing},
            reason=f"recipe stylesheets missing from the served document: {missing}",
        )
    return Outcome(
        "pass", evidence={"loaded": sorted(state.stylesheet_basenames)}
    )


def check_request_order(state, params):
    if not state.discrete_recipe:
        return Outcome(
            "skipped",
            reason="host concatenates or inlines styles; no request order to check",
        )
    first_index = {}
    for index, url in enumerate(state.request_order):
        name = _basename(url)
        if name in state.recipe_stylesheets and name not in first_index:
            first_index[name] = index
    expected_order = [
        name for name in state.recipe_stylesheets if name in first_index
    ]
    ordered = sorted(expected_order, key=lambda name: first_index[name])
    status = "pass" if ordered == state.recipe_stylesheets else "fail"
    return Outcome(
        status,
        evidence={"requestOrder": ordered},
        reason=None if status == "pass"
        else f"stylesheets requested as {ordered}, recipe requires "
        f"{state.recipe_stylesheets}",
    )


def check_scoped_style_diff(state, params):
    if not state.discrete_recipe:
        return Outcome(
            "skipped",
            reason="moo.css is not served as a discrete stylesheet, so the "
            "two-pass block cannot isolate it",
        )
    blocked = state.blocked_page()
    if params["expect"] == "identical":
        args = {
            "selectorAll": params["selectorAll"],
            "properties": params["properties"],
        }
        with_styles = state.page.evaluate(READ_MANY_JS, args)
        without_styles = blocked.evaluate(READ_MANY_JS, args)
        if not with_styles:
            return Outcome(
                "fail",
                evidence={"probeCount": 0},
                reason=f"no probe elements matched {params['selectorAll']}",
            )
        differences = [
            {"index": index, "loaded": loaded, "blocked": blocked_values}
            for index, (loaded, blocked_values) in enumerate(
                zip(with_styles, without_styles)
            )
            if loaded != blocked_values
        ]
        if len(with_styles) != len(without_styles):
            differences.append(
                {"elementCountLoaded": len(with_styles),
                 "elementCountBlocked": len(without_styles)}
            )
        status = "pass" if not differences else "fail"
        return Outcome(
            status,
            evidence={"probeCount": len(with_styles),
                      "differences": differences[:5]},
            reason=None if status == "pass"
            else "out-of-scope probe styles changed when moo.css was blocked",
        )
    args = {"selector": params["selector"], "properties": params["properties"]}
    with_styles = state.page.evaluate(READ_ONE_JS, args)
    without_styles = blocked.evaluate(READ_ONE_JS, args)
    if with_styles is None or without_styles is None:
        return Outcome(
            "fail",
            evidence={"loaded": with_styles, "blocked": without_styles},
            reason=f"control element {params['selector']} missing on one of "
            "the two passes",
        )
    status = "pass" if with_styles != without_styles else "fail"
    return Outcome(
        status,
        evidence={"loaded": with_styles, "blocked": without_styles},
        reason=None if status == "pass"
        else "blocking moo.css changed nothing in scope; the scoped layer "
        "does not appear to apply",
    )


def check_theme_toggle(state, params):
    readings = state.page.evaluate(THEME_TOGGLE_JS, params)
    if not readings["present"]:
        return Outcome(
            "fail",
            evidence=readings,
            reason=f"themed surface {params['selector']} matched no element",
        )
    problems = []
    if readings["light"] != params["lightValue"]:
        problems.append(
            f"light value {readings['light']} != {params['lightValue']}"
        )
    if readings["dark"] != params["darkValue"]:
        problems.append(f"dark value {readings['dark']} != {params['darkValue']}")
    if readings["restored"] != params["lightValue"]:
        problems.append(f"restored value {readings['restored']} != light value")
    status = "pass" if not problems else "fail"
    return Outcome(
        status,
        evidence=readings,
        reason=None if status == "pass" else "; ".join(problems),
    )


def check_direction_mirror(state, params):
    readings = state.page.evaluate(DIRECTION_MIRROR_JS, params)
    if readings["ltr"] is None or readings["rtl"] is None:
        return Outcome(
            "fail",
            evidence=readings,
            reason=f"asymmetric probe {params['selector']} matched no element",
        )
    ltr, rtl = readings["ltr"], readings["rtl"]
    problems = []
    left, right = "padding-left", "padding-right"
    if ltr[left] == ltr[right]:
        problems.append(
            f"probe is symmetric under ltr ({ltr[left]}); it cannot prove mirroring"
        )
    if ltr[left] != rtl[right] or ltr[right] != rtl[left]:
        problems.append(f"physical spacing did not swap: ltr={ltr}, rtl={rtl}")
    status = "pass" if not problems else "fail"
    return Outcome(
        status,
        evidence=readings,
        reason=None if status == "pass" else "; ".join(problems),
    )


def check_tab_reaches_scope(state, params):
    state.focus_body()
    max_tabs = params.get("maxTabs", 20)
    tabs = 0
    reached = False
    for _ in range(max_tabs):
        state.page.keyboard.press("Tab")
        tabs += 1
        reached = state.page.evaluate(FOCUS_IN_SCOPE_JS)
        if reached:
            break
    status = "pass" if reached else "fail"
    return Outcome(
        status,
        evidence={"tabs": tabs, "maxTabs": max_tabs},
        reason=None if status == "pass"
        else f"focus never entered .moo-ui within {max_tabs} Tab presses",
    )


def check_focus_treatment(state, params):
    selector = params["selector"]
    state.focus_body()
    found = False
    tabs = 0
    for _ in range(MAX_TAB_FALLBACK):
        state.page.keyboard.press("Tab")
        tabs += 1
        found = state.page.evaluate(FOCUS_MATCHES_JS, selector)
        if found:
            break
    if not found:
        return Outcome(
            "fail",
            evidence={"tabs": tabs},
            reason=f"keyboard never reached {selector}",
        )
    treatment = state.page.evaluate(FOCUS_TREATMENT_JS, selector)
    visible = (
        treatment["outlineStyle"] != "none" or treatment["boxShadow"] != "none"
    )
    status = "pass" if visible else "fail"
    return Outcome(
        status,
        evidence={"tabs": tabs, "treatment": treatment},
        reason=None if status == "pass"
        else "focused element computes neither an outline nor a box-shadow",
    )


def check_overlay_open(state, params):
    trigger, overlay = params["trigger"], params["overlay"]
    try:
        state.ensure_overlay_closed(trigger, overlay)
        state.page.locator(trigger).first.click()
        state.page.locator(overlay).first.wait_for(
            state="visible", timeout=SCENARIO_TIMEOUT_MS
        )
    except PlaywrightTimeoutError:
        return Outcome(
            "fail",
            evidence={"trigger": trigger},
            reason="overlay did not become visible after activating the trigger",
        )
    z_value = state.page.evaluate(Z_INDEX_JS, overlay)
    try:
        z_index = int(z_value)
    except (TypeError, ValueError):
        z_index = None
    if z_index is None:
        return Outcome(
            "fail",
            evidence={"zIndex": z_value},
            reason=f"overlay {overlay} computes no numeric z-index",
        )
    status = "pass" if z_index >= params["minZIndex"] else "fail"
    return Outcome(
        status,
        evidence={"zIndex": z_index, "minZIndex": params["minZIndex"]},
        reason=None if status == "pass"
        else f"z-index {z_index} is below the overlay floor {params['minZIndex']}",
    )


def check_overlay_focus_moved(state, params):
    overlay = params["overlay"]
    state.ensure_overlay_open(params.get("trigger", "[data-conformance-overlay-trigger]"), overlay)
    try:
        state.page.wait_for_function(
            FOCUS_INSIDE_OVERLAY_JS, arg=overlay, timeout=SCENARIO_TIMEOUT_MS
        )
        moved = True
    except PlaywrightTimeoutError:
        moved = False
    active = state.page.evaluate(
        "() => { const a = document.activeElement;"
        " return a ? (a.id ? '#' + a.id : a.tagName.toLowerCase()) : null; }"
    )
    status = "pass" if moved else "fail"
    return Outcome(
        status,
        evidence={"activeElement": active},
        reason=None if status == "pass"
        else "focus did not move inside the overlay while it was open",
    )


def check_overlay_close_restore(state, params):
    trigger, overlay = params["trigger"], params["overlay"]
    state.ensure_overlay_open(trigger, overlay)
    try:
        state.page.wait_for_function(
            FOCUS_INSIDE_OVERLAY_JS, arg=overlay, timeout=SCENARIO_TIMEOUT_MS
        )
    except PlaywrightTimeoutError:
        pass
    state.page.keyboard.press("Escape")
    try:
        state.page.locator(overlay).first.wait_for(
            state="hidden", timeout=SCENARIO_TIMEOUT_MS
        )
    except PlaywrightTimeoutError:
        return Outcome(
            "fail",
            reason="Escape did not hide the overlay",
        )
    restored = state.page.evaluate(ACTIVE_IS_TRIGGER_JS, trigger)
    status = "pass" if restored else "fail"
    return Outcome(
        status,
        evidence={"focusRestoredToTrigger": restored},
        reason=None if status == "pass"
        else "focus did not return to the trigger after Escape closed the overlay",
    )


def check_esm_inert_before_init(state, params):
    facts = state.pre_init_facts or {}
    inert = (
        facts.get("opened") is False
        and facts.get("markerVisible") is False
        and facts.get("ariaExpanded") != "true"
    )
    try:
        state.page.wait_for_function(MOO_ESM_READY_JS, timeout=SCENARIO_TIMEOUT_MS)
        ready = True
    except PlaywrightTimeoutError:
        ready = False
    opens_after = False
    if ready:
        state.page.locator(params["trigger"]).first.click()
        try:
            state.page.wait_for_function(
                MARKER_VISIBLE_JS,
                arg=params["openedMarker"],
                timeout=SCENARIO_TIMEOUT_MS,
            )
            opens_after = True
        except PlaywrightTimeoutError:
            opens_after = False
    status = "pass" if inert and opens_after else "fail"
    problems = []
    if not inert:
        problems.append(f"fixture was not inert before init ({facts})")
    if not opens_after:
        problems.append("interaction did not open the marker after init")
    return Outcome(
        status,
        evidence={"preInit": facts, "opensAfterInit": opens_after},
        reason=None if status == "pass" else "; ".join(problems),
    )


def check_esm_idempotent_init(state, params):
    class_name = MODULE_CLASS_NAMES.get(params["module"], params["module"])
    result = state.page.evaluate(
        IDEMPOTENT_INIT_JS,
        {"className": class_name, "rootSelector": params["rootSelector"]},
    )
    if not result.get("ready"):
        return Outcome(
            "fail",
            evidence=result,
            reason="init API was not exposed; the fixture's init script did "
            "not run",
        )
    status = "pass" if result["identical"] else "fail"
    return Outcome(
        status,
        evidence=result,
        reason=None if status == "pass"
        else "getOrCreateInstance returned different instances for the same root",
    )


def check_esm_invalid_root_throws(state, params):
    class_name = MODULE_CLASS_NAMES.get(params["module"], params["module"])
    result = state.page.evaluate(INVALID_ROOT_JS, class_name)
    if not result.get("ready"):
        return Outcome(
            "fail",
            evidence=result,
            reason="init API was not exposed; the fixture's init script did "
            "not run",
        )
    status = (
        "pass"
        if result["threw"] and result.get("errorName") == params["errorName"]
        else "fail"
    )
    return Outcome(
        status,
        evidence=result,
        reason=None if status == "pass"
        else f"expected {params['errorName']} for an invalid root, got {result}",
    )


def check_bootstrap_data_api_works(state, params):
    trigger, panel = params["trigger"], params["panel"]
    script_srcs = state.page.evaluate(SCRIPT_SRCS_JS)
    moo_scripts = [
        src for src in script_srcs
        if re.search(r"(combobox|sidebar)\.js$|init-moo-esm\.js$", urlsplit(src).path)
    ]
    try:
        state.ensure_overlay_closed(trigger, panel)
        state.page.locator(trigger).first.click()
        state.page.locator(panel).first.wait_for(
            state="visible", timeout=SCENARIO_TIMEOUT_MS
        )
        opened = True
    except PlaywrightTimeoutError:
        opened = False
    status = "pass" if opened and not moo_scripts else "fail"
    problems = []
    if moo_scripts:
        problems.append(f"Moo ESM scripts present: {moo_scripts}")
    if not opened:
        problems.append("Data API trigger did not open its panel")
    return Outcome(
        status,
        evidence={"opened": opened, "mooScripts": moo_scripts},
        reason=None if status == "pass" else "; ".join(problems),
    )


def check_csp_injection_clean(state, params):
    violations = [
        text
        for message_type, text in state.console
        if message_type == "error"
        and (text.startswith("Refused to") or "Content-Security-Policy" in text)
    ]
    status = "pass" if not violations else "fail"
    return Outcome(
        status,
        evidence={"policy": params["policy"], "violations": violations},
        reason=None if status == "pass"
        else f"{len(violations)} CSP violation message(s) recorded",
    )


def check_console_errors(state, params):
    errors = [text for message_type, text in state.console if message_type == "error"]
    problems = errors + state.page_errors
    status = "pass" if not problems else "fail"
    return Outcome(
        status,
        evidence={"consoleErrors": errors[:10], "pageErrors": state.page_errors[:10]},
        reason=None if status == "pass"
        else f"{len(problems)} console error(s) or uncaught exception(s)",
    )


def check_failed_requests(state, params):
    problems = state.bad_responses + state.failed_requests
    status = "pass" if not problems else "fail"
    return Outcome(
        status,
        evidence={
            "badResponses": state.bad_responses[:10],
            "failedRequests": state.failed_requests[:10],
            "note": "browser-internal favicon requests are excluded",
        },
        reason=None if status == "pass"
        else f"{len(problems)} resource(s) failed to load",
    )


CHECKS = {
    "computed-equals": check_computed_equals,
    "stylesheets-loaded": check_stylesheets_loaded,
    "request-order": check_request_order,
    "scoped-style-diff": check_scoped_style_diff,
    "theme-toggle": check_theme_toggle,
    "direction-mirror": check_direction_mirror,
    "tab-reaches-scope": check_tab_reaches_scope,
    "focus-treatment": check_focus_treatment,
    "overlay-open": check_overlay_open,
    "overlay-focus-moved": check_overlay_focus_moved,
    "overlay-close-restore": check_overlay_close_restore,
    "esm-inert-before-init": check_esm_inert_before_init,
    "esm-idempotent-init": check_esm_idempotent_init,
    "esm-invalid-root-throws": check_esm_invalid_root_throws,
    "bootstrap-data-api-works": check_bootstrap_data_api_works,
    "csp-injection-clean": check_csp_injection_clean,
    "console-errors": check_console_errors,
    "failed-requests": check_failed_requests,
}


def run_fixture_state(state):
    """Drive one fixture's contract checks; the caller closes the state."""
    contract = state.contract
    fixture_meta = state.fixture_meta
    inert_assertion = next(
        (
            assertion
            for category in contract["categories"]
            for assertion in category["assertions"]
            if assertion["check"] == "esm-inert-before-init"
            and fixture_meta["name"] in assertion["fixtures"]
        ),
        None,
    )
    if inert_assertion is not None:
        state.run_pre_init_pass(
            inert_assertion["params"]["trigger"],
            inert_assertion["params"]["openedMarker"],
        )
    state.load_primary()

    categories = []
    for category in contract["categories"]:
        applied = [
            assertion
            for assertion in category["assertions"]
            if fixture_meta["name"] in assertion["fixtures"]
        ]
        if not applied:
            continue
        assertion_results = []
        for assertion in applied:
            if not state.loaded:
                outcome = Outcome(
                    "fail",
                    reason=f"fixture did not load ({state.load_status})",
                )
            else:
                check = CHECKS.get(assertion["check"])
                if check is None:
                    outcome = Outcome(
                        "fail",
                        reason=f"runner has no implementation for check "
                        f"{assertion['check']}",
                    )
                else:
                    try:
                        outcome = check(state, assertion["params"])
                    except Exception as error:  # noqa: BLE001 - report it
                        outcome = Outcome(
                            "fail",
                            evidence=repr(error),
                            reason=f"check raised {type(error).__name__}",
                        )
            entry = {"id": assertion["id"], "status": outcome.status}
            if outcome.evidence is not None:
                entry["evidence"] = outcome.evidence
            if outcome.reason is not None:
                entry["reason"] = outcome.reason
            assertion_results.append(entry)
        statuses = {entry["status"] for entry in assertion_results}
        if "fail" in statuses:
            category_status = "fail"
            reason = None
        elif statuses == {"skipped"}:
            category_status = "skipped"
            reason = "; ".join(
                entry["reason"] for entry in assertion_results if entry["reason"]
            )
        else:
            category_status = "pass"
            reason = None
        category_result = {
            "id": category["id"],
            "status": category_status,
            "assertions": assertion_results,
        }
        if reason is not None:
            category_result["reason"] = reason
        categories.append(category_result)
    return {
        "name": fixture_meta["name"],
        "url": state.url,
        "categories": categories,
    }


def fixture_error_result(state, error):
    """Every applied assertion fails when the runner itself breaks mid-run."""
    categories = []
    for category in state.contract["categories"]:
        applied = [
            assertion
            for assertion in category["assertions"]
            if state.fixture_meta["name"] in assertion["fixtures"]
        ]
        if not applied:
            continue
        categories.append(
            {
                "id": category["id"],
                "status": "fail",
                "assertions": [
                    {
                        "id": assertion["id"],
                        "status": "fail",
                        "reason": f"runner error: {type(error).__name__}: {error}",
                    }
                    for assertion in applied
                ],
            }
        )
    return {"name": state.fixture_meta["name"], "url": state.url, "categories": categories}


def run_contract(browser, base_url, contract, csp_policy):
    fixture_results = []
    served_bootstrap = None
    recipe_detected = None
    for fixture_meta in contract["kit"]["fixtures"]:
        state = FixtureState(browser, base_url, contract, fixture_meta, csp_policy)
        try:
            try:
                result = run_fixture_state(state)
            except Exception as error:  # noqa: BLE001 - report it
                result = fixture_error_result(state, error)
        finally:
            if served_bootstrap is None and state.bootstrap_version:
                served_bootstrap = state.bootstrap_version
            if recipe_detected is None and state.discrete_recipe:
                recipe_detected = fixture_meta["cssRecipe"]
            state.close()
        fixture_results.append(result)

    host = {"baseUrl": base_url, "servedBootstrapVersion": served_bootstrap}
    if recipe_detected:
        host["cssRecipeDetected"] = recipe_detected
    bootstrap_range = contract["kit"].get("bootstrapRange", "")
    if served_bootstrap and not served_bootstrap.startswith("5.3."):
        host["notes"] = (
            f"served Bootstrap {served_bootstrap} is outside the contract "
            f"range {bootstrap_range}"
        )

    passed = failed = skipped = 0
    for fixture in fixture_results:
        for category in fixture["categories"]:
            for assertion in category["assertions"]:
                if assertion["status"] == "pass":
                    passed += 1
                elif assertion["status"] == "fail":
                    failed += 1
                else:
                    skipped += 1

    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "contractVersion": contract["schemaVersion"],
        "generatedAt": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "runner": {"name": RUNNER_NAME, "version": RUNNER_VERSION},
        "host": host,
        "fixtures": fixture_results,
        "summary": {
            "assertionsPassed": passed,
            "assertionsFailed": failed,
            "assertionsSkipped": skipped,
            "result": "pass" if failed == 0 else "fail",
        },
    }


def find_csp_policy(contract):
    for category in contract["categories"]:
        for assertion in category["assertions"]:
            if assertion["check"] == "csp-injection-clean":
                return assertion["params"]["policy"]
    raise ValueError("contract defines no csp-injection-clean assertion")


def launch_browser(playwright: Playwright) -> Browser:
    channel = os.environ.get("MOO_UI_BROWSER_CHANNEL")
    if channel:
        return playwright.chromium.launch(channel=channel)
    if LOCAL_CHROME.is_file():
        return playwright.chromium.launch(channel="chrome")
    return playwright.chromium.launch()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the Moo UI Generic Host Conformance Kit against a host."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL serving the kit fixtures (fixture paths resolve "
        "relative to it).",
    )
    parser.add_argument(
        "--report-out",
        default=None,
        help="Path to write the JSON report; defaults to stdout.",
    )
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT),
        help="Path to the conformance contract (defaults to the kit's own).",
    )
    args = parser.parse_args(argv)

    contract_path = Path(args.contract)
    if not contract_path.is_file():
        parser.exit(2, f"contract not found: {contract_path}\n")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    csp_policy = find_csp_policy(contract)

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        try:
            report = run_contract(browser, args.base_url, contract, csp_policy)
        finally:
            browser.close()

    text = json.dumps(report, indent=2) + "\n"
    if args.report_out:
        Path(args.report_out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    summary = report["summary"]
    print(
        f"conformance {summary['result']}: "
        f"passed={summary['assertionsPassed']} "
        f"failed={summary['assertionsFailed']} "
        f"skipped={summary['assertionsSkipped']}",
        file=sys.stderr,
    )
    return 0 if summary["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
