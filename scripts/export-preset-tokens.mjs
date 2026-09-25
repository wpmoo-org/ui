// Build-time bridge for non-Catalog hosts.  The output is data, never a
// runtime import of the Catalog settings panel or its browser storage.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  THEME_BUILDER_DEFAULTS,
  THEME_BUILDER_OPTIONS,
  resolveThemeBuilderTokens,
} from "../site/src/js/catalog/theme-builder-schema.js";

const sourcePath = new URL("../site/src/js/catalog/theme-builder-schema.js", import.meta.url);
const packagePath = new URL("../package.json", import.meta.url);
const version = JSON.parse(readFileSync(packagePath, "utf8")).version;
const allowed = new Set(PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST);
const axes = ["baseColor", "themeColor", "chartColor", "radius"];
const modes = ["light", "dark"];
const defaults = Object.fromEntries(axes.map((axis) => [axis, THEME_BUILDER_DEFAULTS[axis]]));
const options = Object.fromEntries(axes.map((axis) => [axis, THEME_BUILDER_OPTIONS[axis]]));
const tokens = {};

for (const axis of axes) {
  tokens[axis] = {};
  for (const choice of options[axis]) {
    tokens[axis][choice] = {};
    for (const mode of modes) {
      const baseline = resolveThemeBuilderTokens(defaults, { theme: mode, surface: "export" });
      const selected = resolveThemeBuilderTokens(
        { ...defaults, [axis]: choice },
        { theme: mode, surface: "export" }
      );
      const delta = {};
      for (const [key, value] of Object.entries(selected)) {
        if (!allowed.has(key)) {
          throw new Error(`Unpublished theme token: ${key}`);
        }
        if (baseline[key] !== value) {
          delta[key] = value;
        }
      }
      tokens[axis][choice][mode] = delta;
    }
  }
}

process.stdout.write(`${JSON.stringify({
  schemaVersion: 1,
  mooUiVersion: version,
  sourcePath: "site/src/js/catalog/theme-builder-schema.js",
  sourceSha256: createHash("sha256").update(readFileSync(sourcePath)).digest("hex"),
  defaults,
  options,
  allowList: PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  tokens,
})}\n`);
