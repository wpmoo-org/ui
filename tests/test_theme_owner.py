from __future__ import annotations

import json
import subprocess
import unittest

from tests.helpers import ROOT
from tests.helpers.node_harness import NODE_TEST_TIMEOUT


class ThemeOwnerTests(unittest.TestCase):
    def run_case(self, script: str) -> dict[str, object]:
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=NODE_TEST_TIMEOUT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertTrue(lines, f"No report emitted; stderr: {result.stderr}")
        return json.loads(lines[-1])

    def test_resolver_uses_only_resolved_owners_and_explicit_portal_hosts(self) -> None:
        case = self.run_case(
            """
import assert from "node:assert/strict";
import {
  findThemeOwner,
  findThemeOwners,
  isDocumentOwner,
  resolveThemeElement,
  ownerPortalRoot,
  ownerStorageKey,
  readOwnerPreference,
  resolveOwnerTheme,
  resolveOwnerDirection,
  setOwnerTheme,
  setOwnerDirection,
} from "./src/js/theme-owner.js";

function makeElement({ classes = [], dataset = {}, dir = "" } = {}) {
  const classSet = new Set(classes);
  const element = {
    nodeType: 1,
    tagName: "DIV",
    dataset: { ...dataset },
    dir,
    children: [],
    parentElement: null,
    ownerDocument: null,
    classList: {
      contains(name) { return classSet.has(name); },
    },
    append(child) {
      child.parentElement = this;
      this.children.push(child);
      return child;
    },
    get firstElementChild() { return this.children[0] || null; },
    matches(selector) {
      if (
        selector.includes(".moo-ui") &&
        selector.includes("data-bs-theme")
      ) {
        return classSet.has("moo-ui") && ["light", "dark"].includes(this.dataset.bsTheme);
      }
      if (selector.includes("[data-moo-overlay-portal-host]")) {
        return Object.hasOwn(this.dataset, "mooOverlayPortalHost");
      }
      return false;
    },
    closest(selector) {
      let current = this;
      while (current) {
        if (current.matches?.(selector)) return current;
        current = current.parentElement;
      }
      return null;
    },
    querySelectorAll(selector) {
      const matches = [];
      const visit = (node) => {
        for (const child of node.children || []) {
          if (child.matches?.(selector)) matches.push(child);
          visit(child);
        }
      };
      visit(this);
      return matches;
    },
  };
  return element;
}

const html = makeElement();
const body = makeElement();
html.append(body);
const storage = new Map([
  ["outer", "system"],
  ["moo:theme", "dark"],
  ["moo:direction", "rtl"],
]);
const view = {
  localStorage: {
    getItem(key) { return storage.get(key) || null; },
    setItem(key, value) { storage.set(key, String(value)); },
  },
  matchMedia() { return { matches: true }; },
};
const documentNode = {
  nodeType: 9,
  body,
  documentElement: html,
  defaultView: view,
  querySelectorAll(selector) { return body.querySelectorAll(selector); },
};
const adopt = (node) => {
  node.ownerDocument = documentNode;
  for (const child of node.children || []) adopt(child);
};

const outer = makeElement({
  classes: ["moo-ui"],
  dataset: {
    bsTheme: "dark",
    mooThemeKey: "outer",
    mooDocumentOwner: "true",
  },
});
const outerTrigger = makeElement();
const inner = makeElement({
  classes: ["moo-ui"],
  dataset: { bsTheme: "light" },
});
const innerTrigger = makeElement();
const innerHost = makeElement({ dataset: { mooOverlayPortalHost: "" } });
const outerHost = makeElement({
  classes: ["moo-ui"],
  dataset: { mooOverlayPortalHost: "" },
});
const sibling = makeElement({
  classes: ["moo-ui"],
  dataset: { bsTheme: "light" },
});
const orphan = makeElement();

inner.append(innerTrigger);
inner.append(innerHost);
outer.append(outerTrigger);
outer.append(inner);
outer.append(outerHost);
body.append(outer);
body.append(sibling);
adopt(html);
orphan.ownerDocument = documentNode;

assert.equal(findThemeOwner(html), null);
assert.equal(findThemeOwner(body), outer);
assert.equal(findThemeOwner(innerTrigger), inner);
assert.equal(findThemeOwner(outerHost), outer);
assert.equal(findThemeOwner(orphan), null);
assert.deepEqual(findThemeOwners(documentNode), [outer, inner, sibling]);
assert.deepEqual(findThemeOwners(outer), [outer, inner]);
assert.equal(isDocumentOwner(outer), true);
assert.equal(ownerPortalRoot(outer), outerHost);
assert.equal(ownerPortalRoot(inner), innerHost);
assert.equal(ownerPortalRoot(null), null);
assert.equal(ownerStorageKey(outer, "theme"), "outer");
assert.equal(ownerStorageKey(inner, "theme"), null);
assert.equal(ownerStorageKey(sibling, "direction"), null);
assert.equal(readOwnerPreference(outer, "theme"), "system");
assert.equal(resolveOwnerTheme(outer, "system", view), "dark");
assert.equal(resolveOwnerTheme(inner, null, view), "light");
assert.equal(resolveOwnerDirection(inner, "rtl"), "rtl");
assert.equal(resolveThemeElement(innerTrigger), inner);
assert.equal(resolveThemeElement(orphan), body);

setOwnerTheme(inner, "dark");
assert.equal(inner.dataset.bsTheme, "dark");
body.children = [outer];
sibling.parentElement = null;
assert.equal(ownerStorageKey(outer, "direction"), "moo:direction");
setOwnerDirection(outer, "rtl");
assert.equal(html.dir, "rtl");

console.log(JSON.stringify({
  name: "resolved-owner-contract",
  ok: true,
  owners: findThemeOwners(documentNode).length,
  documentDirection: html.dir,
}));
"""
        )

        self.assertEqual(
            case,
            {
                "name": "resolved-owner-contract",
                "ok": True,
                "owners": 2,
                "documentDirection": "rtl",
            },
        )

    def test_prepaint_resolves_owner_preferences_without_html_theme_state(self) -> None:
        case = self.run_case(
            """
import assert from "node:assert/strict";

function owner({ theme, themeKey, directionKey, documentOwner = false } = {}) {
  return {
    dataset: {
      ...(theme ? { bsTheme: theme } : {}),
      ...(themeKey ? { mooThemeKey: themeKey } : {}),
      ...(directionKey ? { mooDirectionKey: directionKey } : {}),
      ...(documentOwner ? { mooDocumentOwner: "true" } : {}),
    },
    dir: "",
    parentElement: null,
    matches(selector) {
      return selector.includes(".moo-ui") && ["light", "dark"].includes(this.dataset.bsTheme);
    },
  };
}

const documentElement = { dataset: {}, dir: "ltr" };
const body = {
  children: [],
  get firstElementChild() { return this.children[0] || null; },
};
const storage = new Map([
  ["moo:theme", "system"],
  ["moo:direction", "rtl"],
  ["embedded-direction", "rtl"],
]);
globalThis.window = {
  localStorage: { getItem(key) { return storage.get(key) || null; } },
  matchMedia() { return { matches: true }; },
};
globalThis.document = {
  body,
  documentElement,
  currentScript: null,
};

const documentOwner = owner({ theme: "light", documentOwner: true });
documentOwner.parentElement = body;
body.children = [documentOwner];
document.currentScript = { parentElement: documentOwner };
await import("./src/js/theme-prepaint.js?document-owner");
assert.equal(documentOwner.dataset.bsTheme, "dark");
assert.equal(documentOwner.dataset.mooPrepaint, "ready");
assert.equal(documentElement.dir, "rtl");
assert.equal(documentElement.dataset.bsTheme, undefined);
assert.deepEqual(documentOwner.__mooPrepaintBaseline, {
  theme: "light",
  direction: "ltr",
});

const documentSibling = owner({ theme: "light" });
documentSibling.parentElement = body;
body.children = [documentOwner, documentSibling];
assert.equal(documentElement.dir, "rtl");
assert.equal(documentOwner.dataset.bsTheme, "dark");

const embedded = owner({
  theme: "dark",
  directionKey: "embedded-direction",
});
embedded.parentElement = body;
const sibling = owner({ theme: "light" });
sibling.parentElement = body;
body.children = [documentOwner, embedded, sibling];
documentElement.dir = "ltr";
document.currentScript = { parentElement: embedded };
await import("./src/js/theme-prepaint.js?embedded-owner");
assert.equal(embedded.dataset.bsTheme, "dark");
assert.equal(embedded.dataset.mooPrepaint, "ready");
assert.equal(embedded.dir, "rtl");
assert.equal(documentElement.dir, "ltr");
assert.deepEqual(embedded.__mooPrepaintBaseline, {
  theme: "dark",
  direction: null,
});

const classOnlyHost = {
  dataset: {},
  matches() { return false; },
  parentElement: body,
};
document.currentScript = { parentElement: classOnlyHost };
await import("./src/js/theme-prepaint.js?class-only-host");
assert.equal(classOnlyHost.dataset.mooPrepaint, undefined);

const unmarkedBodyOwner = owner({
  theme: "light",
  directionKey: "embedded-direction",
});
unmarkedBodyOwner.parentElement = body;
body.children = [unmarkedBodyOwner];
documentElement.dir = "ltr";
document.currentScript = { parentElement: unmarkedBodyOwner };
await import("./src/js/theme-prepaint.js?unmarked-body-owner");
assert.equal(unmarkedBodyOwner.dir, "rtl");
assert.equal(documentElement.dir, "ltr");
assert.equal(unmarkedBodyOwner.dataset.mooPrepaint, "ready");

const throwingSystemOwner = owner({ theme: "light", documentOwner: true });
throwingSystemOwner.parentElement = body;
body.children = [throwingSystemOwner];
documentElement.dir = "ltr";
window.matchMedia = () => { throw new Error("unavailable"); };
document.currentScript = { parentElement: throwingSystemOwner };
await import("./src/js/theme-prepaint.js?match-media-throws");
assert.equal(throwingSystemOwner.dataset.bsTheme, "light");
assert.equal(throwingSystemOwner.dataset.mooPrepaint, "ready");
assert.deepEqual(throwingSystemOwner.__mooPrepaintBaseline, {
  theme: "light",
  direction: "ltr",
});

console.log(JSON.stringify({
  name: "owner-prepaint-contract",
  ok: true,
  documentTheme: documentOwner.dataset.bsTheme,
  embeddedDirection: embedded.dir,
  fallbackTheme: throwingSystemOwner.dataset.bsTheme,
}));
"""
        )

        self.assertEqual(
            case,
            {
                "name": "owner-prepaint-contract",
                "ok": True,
                "documentTheme": "dark",
                "embeddedDirection": "rtl",
                "fallbackTheme": "light",
            },
        )

    def test_embedded_owner_never_infers_document_scope_from_streamed_siblings(self) -> None:
        case = self.run_case(
            """
import assert from "node:assert/strict";

function owner({ theme = "light", directionKey = "embedded-direction" } = {}) {
  return {
    dataset: {
      bsTheme: theme,
      mooDirectionKey: directionKey,
    },
    dir: "",
    parentElement: null,
    matches(selector) {
      return selector.includes(".moo-ui") &&
        ["light", "dark"].includes(this.dataset.bsTheme);
    },
    getAttribute(name) {
      return name === "dir" ? this.dir || null : null;
    },
  };
}

const documentElement = { dir: "ltr" };
const body = {
  children: [],
  get firstElementChild() { return this.children[0] || null; },
};
const storage = new Map([["embedded-direction", "rtl"]]);
globalThis.window = {
  localStorage: { getItem(key) { return storage.get(key) || null; } },
};
globalThis.document = {
  body,
  documentElement,
  currentScript: null,
};

const embedded = owner();
embedded.parentElement = body;
body.children = [embedded];
document.currentScript = { parentElement: embedded };
await import("./src/js/theme-prepaint.js?streaming-embedded");

const laterSibling = owner({ theme: "dark" });
laterSibling.parentElement = body;
body.children = [embedded, laterSibling];

assert.equal(embedded.dir, "rtl");
assert.equal(documentElement.dir, "ltr");
assert.equal(embedded.dataset.mooPrepaint, "ready");

console.log(JSON.stringify({
  name: "streaming-embedded-owner",
  ok: true,
  documentDirection: documentElement.dir,
  ownerDirection: embedded.dir,
}));
"""
        )

        self.assertEqual(
            case,
            {
                "name": "streaming-embedded-owner",
                "ok": True,
                "documentDirection": "ltr",
                "ownerDirection": "rtl",
            },
        )

    def test_owner_baseline_direction_and_system_theme_recovery_are_safe(self) -> None:
        case = self.run_case(
            """
import assert from "node:assert/strict";
import {
  effectiveOwnerDirection,
  ownerPrepaintBaseline,
  resolveOwnerTheme,
  restoreOwnerDirection,
  safeColorSchemeMedia,
} from "./src/js/theme-owner.js";

function element({ classes = [], dataset = {}, dir = null } = {}) {
  const classSet = new Set(classes);
  const attributes = dir ? { dir } : {};
  return {
    nodeType: 1,
    dataset: { ...dataset },
    children: [],
    parentElement: null,
    ownerDocument: null,
    get dir() { return attributes.dir || ""; },
    set dir(value) {
      if (value) attributes.dir = value;
      else delete attributes.dir;
    },
    getAttribute(name) { return attributes[name] ?? null; },
    setAttribute(name, value) { attributes[name] = String(value); },
    removeAttribute(name) { delete attributes[name]; },
    matches(selector) {
      return selector.includes(".moo-ui") &&
        classSet.has("moo-ui") &&
        ["light", "dark"].includes(this.dataset.bsTheme);
    },
  };
}

const html = element({ dir: "rtl" });
const body = element();
body.parentElement = html;
const sibling = element({ classes: ["moo-ui"], dataset: { bsTheme: "light" } });
const embedded = element({ classes: ["moo-ui"], dataset: { bsTheme: "dark" } });
sibling.parentElement = body;
embedded.parentElement = body;
body.children = [sibling, embedded];
body.firstElementChild = sibling;
const ownerDocument = { nodeType: 9, body, documentElement: html, defaultView: {} };
[html, body, sibling, embedded].forEach((node) => { node.ownerDocument = ownerDocument; });

embedded.__mooPrepaintBaseline = { theme: "light", direction: null };
assert.deepEqual(ownerPrepaintBaseline(embedded), {
  theme: "light",
  direction: null,
});
assert.equal(effectiveOwnerDirection(embedded), "rtl");
embedded.dir = "ltr";
restoreOwnerDirection(embedded, null);
assert.equal(embedded.getAttribute("dir"), null);
assert.equal(effectiveOwnerDirection(embedded), "rtl");

const throwingView = {
  get matchMedia() { throw new Error("unavailable"); },
};
assert.equal(safeColorSchemeMedia(throwingView), null);
assert.equal(resolveOwnerTheme(embedded, "system", throwingView), "light");

console.log(JSON.stringify({
  name: "owner-baseline-and-safe-media",
  ok: true,
  effectiveDirection: effectiveOwnerDirection(embedded),
  resolvedSystemTheme: resolveOwnerTheme(embedded, "system", throwingView),
}));
"""
        )

        self.assertEqual(
            case,
            {
                "name": "owner-baseline-and-safe-media",
                "ok": True,
                "effectiveDirection": "rtl",
                "resolvedSystemTheme": "light",
            },
        )
