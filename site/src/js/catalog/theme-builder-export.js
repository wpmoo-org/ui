import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./theme-builder-schema.js";

const DEFAULT_MOO_UI_VERSION = "1.0.0-rc.3";

function orderedTokens(tokens) {
  return PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST.filter((token) =>
    Object.hasOwn(tokens, token)
  ).map((token) => [token, tokens[token]]);
}

function cssBlock(selector, tokens) {
  const declarations = orderedTokens(tokens);
  if (!declarations.length) {
    return "";
  }
  return [
    `${selector} {`,
    ...declarations.map(([token, value]) => `  ${token}: ${value};`),
    "}",
  ].join("\n");
}

export function createThemeBuilderPreset(
  candidate = {},
  { mooUiVersion = DEFAULT_MOO_UI_VERSION } = {}
) {
  const state = normalizeThemeBuilderState(candidate);
  return {
    schemaVersion: state.schemaVersion,
    mooUiVersion,
    baseColor: state.baseColor,
    themeColor: state.themeColor,
    chartColor: state.chartColor,
    headingFont: state.headingFont,
    bodyFont: state.bodyFont,
    radius: state.radius,
  };
}

export function serializeThemeBuilderPresetJson(candidate = {}, options = {}) {
  return `${JSON.stringify(createThemeBuilderPreset(candidate, options), null, 2)}\n`;
}

function ownerSelector(ownerMarker) {
  if (
    typeof ownerMarker !== "string" ||
    !/^[A-Za-z][A-Za-z0-9_-]{0,127}$/.test(ownerMarker)
  ) {
    throw new TypeError(
      "Owner-scoped Theme Builder CSS requires a generated owner marker."
    );
  }
  return `[data-moo-theme-builder-owner="${ownerMarker}"]`;
}

export function serializeThemeBuilderPresetCss(
  candidate = {},
  { scope = "standalone", ownerMarker } = {}
) {
  if (scope !== "owner" && scope !== "standalone") {
    throw new TypeError("Theme Builder CSS scope must be owner or standalone.");
  }

  const state = normalizeThemeBuilderState(candidate);
  const lightTokens = resolveThemeBuilderTokens(state, { theme: "light" });
  const darkTokens = resolveThemeBuilderTokens(state, { theme: "dark" });
  if (scope === "owner") {
    const selector = ownerSelector(ownerMarker);
    return [
      cssBlock(selector, lightTokens),
      cssBlock(`${selector}[data-bs-theme="dark"]`, darkTokens),
    ]
      .filter(Boolean)
      .join("\n\n")
      .concat("\n");
  }

  return [
    cssBlock(':root,\n[data-bs-theme="light"]', lightTokens),
    cssBlock('[data-bs-theme="dark"]', darkTokens),
  ]
    .filter(Boolean)
    .join("\n\n")
    .concat("\n");
}
