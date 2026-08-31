export const THEME_BUILDER_SCHEMA_VERSION = 1;

export const THEME_BUILDER_DEFAULTS = {
  schemaVersion: THEME_BUILDER_SCHEMA_VERSION,
  baseColor: "neutral",
  themeColor: "neutral",
  chartColor: "neutral",
  headingFont: "default",
  bodyFont: "default",
  radius: "default",
};

export const PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST = [
  "--bs-body-bg",
  "--bs-body-color",
  "--bs-body-font-family",
  "--bs-border-color",
  "--bs-border-radius",
  "--bs-border-radius-lg",
  "--bs-border-radius-sm",
  "--bs-border-radius-xl",
  "--bs-border-radius-xxl",
  "--bs-card-bg",
  "--bs-card-border-color",
  "--bs-focus-ring-color",
  "--bs-link-color",
  "--bs-link-hover-color",
  "--bs-primary",
  "--bs-primary-rgb",
  "--bs-secondary-bg",
  "--bs-secondary-color",
  "--bs-tertiary-bg",
  "--moo-border",
  "--moo-chart-1",
  "--moo-chart-2",
  "--moo-chart-3",
  "--moo-chart-4",
  "--moo-chart-5",
  "--moo-foreground",
  "--moo-heading-font-family",
  "--moo-muted-foreground",
  "--moo-muted-surface",
  "--moo-primary",
  "--moo-primary-foreground",
  "--moo-primary-foreground-dark",
  "--moo-ring",
  "--moo-sidebar",
  "--moo-sidebar-accent",
  "--moo-sidebar-border",
  "--moo-sidebar-foreground",
  "--moo-surface",
];

export const THEME_BUILDER_OPTIONS = {
  baseColor: ["neutral", "stone", "zinc", "mauve", "olive", "mist", "taupe"],
  themeColor: [
    "neutral",
    "blue",
    "azure",
    "indigo",
    "purple",
    "orange",
    "pink",
    "red",
    "yellow",
    "lime",
    "green",
    "teal",
    "cyan",
  ],
  chartColor: [
    "neutral",
    "blue",
    "azure",
    "indigo",
    "purple",
    "orange",
    "pink",
    "red",
    "yellow",
    "lime",
    "green",
    "teal",
    "cyan",
  ],
  headingFont: ["default", "geist", "system"],
  bodyFont: ["default", "geist", "system"],
  radius: ["default", "none", "small", "medium", "large"],
};

const OPTION_SETS = Object.fromEntries(
  Object.entries(THEME_BUILDER_OPTIONS).map(([key, values]) => [key, new Set(values)])
);

const LEGACY_ACTION_BASE_COLORS = new Set(["blue", "emerald", "violet"]);
const BASE_COLOR_ALIASES = {
  slate: "mist",
};
const ACTION_COLOR_ALIASES = {
  emerald: "green",
  violet: "purple",
  amber: "yellow",
  rose: "pink",
};
const RADIUS_ALIASES = {
  compact: "small",
};

const NEUTRAL_BASE_BORDER_TOKENS = {
  light: {
    "--moo-border": "#e4e4e7",
    "--bs-border-color": "var(--moo-border)",
    "--bs-card-border-color": "var(--moo-border)",
    "--moo-sidebar-border": "#e4e4e7",
  },
  dark: {
    "--moo-border": "oklch(1 0 0 / 10%)",
    "--bs-border-color": "var(--moo-border)",
    "--bs-card-border-color": "var(--moo-border)",
    "--moo-sidebar-border": "oklch(1 0 0 / 10%)",
  },
};

const BASE_COLOR_SCALES = {
  neutral: { light: null, dark: null },
  stone: {
    light: {
      surface: "oklch(1 0 0)",
      foreground: "oklch(0.147 0.004 49.25)",
      mutedSurface: "oklch(0.97 0.001 106.424)",
      mutedForeground: "oklch(0.553 0.013 58.071)",
      accent: "oklch(0.97 0.001 106.424)",
      border: "oklch(0.923 0.003 48.717)",
      card: "oklch(1 0 0)",
      sidebar: "oklch(0.985 0.001 106.423)",
      sidebarForeground: "oklch(0.147 0.004 49.25)",
      sidebarAccent: "oklch(0.97 0.001 106.424)",
      sidebarBorder: "oklch(0.923 0.003 48.717)",
    },
    dark: {
      surface: "oklch(0.147 0.004 49.25)",
      foreground: "oklch(0.985 0.001 106.423)",
      mutedSurface: "oklch(0.268 0.007 34.298)",
      mutedForeground: "oklch(0.709 0.01 56.259)",
      accent: "oklch(0.268 0.007 34.298)",
      border: "oklch(1 0 0 / 10%)",
      card: "oklch(0.216 0.006 56.043)",
      sidebar: "oklch(0.216 0.006 56.043)",
      sidebarForeground: "oklch(0.985 0.001 106.423)",
      sidebarAccent: "oklch(0.268 0.007 34.298)",
      sidebarBorder: "oklch(1 0 0 / 10%)",
    },
  },
  zinc: {
    light: {
      surface: "oklch(1 0 0)",
      foreground: "oklch(0.141 0.005 285.823)",
      mutedSurface: "oklch(0.967 0.001 286.375)",
      mutedForeground: "oklch(0.552 0.016 285.938)",
      accent: "oklch(0.967 0.001 286.375)",
      border: "oklch(0.92 0.004 286.32)",
      card: "oklch(1 0 0)",
      sidebar: "oklch(0.985 0 0)",
      sidebarForeground: "oklch(0.141 0.005 285.823)",
      sidebarAccent: "oklch(0.967 0.001 286.375)",
      sidebarBorder: "oklch(0.92 0.004 286.32)",
    },
    dark: {
      surface: "oklch(0.141 0.005 285.823)",
      foreground: "oklch(0.985 0 0)",
      mutedSurface: "oklch(0.274 0.006 286.033)",
      mutedForeground: "oklch(0.705 0.015 286.067)",
      accent: "oklch(0.274 0.006 286.033)",
      border: "oklch(1 0 0 / 10%)",
      card: "oklch(0.21 0.006 285.885)",
      sidebar: "oklch(0.21 0.006 285.885)",
      sidebarForeground: "oklch(0.985 0 0)",
      sidebarAccent: "oklch(0.274 0.006 286.033)",
      sidebarBorder: "oklch(1 0 0 / 10%)",
    },
  },
  mauve: {
    light: {
      surface: "oklch(1 0 0)",
      foreground: "oklch(0.145 0.008 326)",
      mutedSurface: "oklch(0.96 0.003 325.6)",
      mutedForeground: "oklch(0.542 0.034 322.5)",
      accent: "oklch(0.96 0.003 325.6)",
      border: "oklch(0.922 0.005 325.62)",
      card: "oklch(1 0 0)",
      sidebar: "oklch(0.985 0 0)",
      sidebarForeground: "oklch(0.145 0.008 326)",
      sidebarAccent: "oklch(0.96 0.003 325.6)",
      sidebarBorder: "oklch(0.922 0.005 325.62)",
    },
    dark: {
      surface: "oklch(0.145 0.008 326)",
      foreground: "oklch(0.985 0 0)",
      mutedSurface: "oklch(0.263 0.024 320.12)",
      mutedForeground: "oklch(0.711 0.019 323.02)",
      accent: "oklch(0.263 0.024 320.12)",
      border: "oklch(1 0 0 / 10%)",
      card: "oklch(0.212 0.019 322.12)",
      sidebar: "oklch(0.212 0.019 322.12)",
      sidebarForeground: "oklch(0.985 0 0)",
      sidebarAccent: "oklch(0.263 0.024 320.12)",
      sidebarBorder: "oklch(1 0 0 / 10%)",
    },
  },
  olive: {
    light: {
      surface: "oklch(1 0 0)",
      foreground: "oklch(0.153 0.006 107.1)",
      mutedSurface: "oklch(0.966 0.005 106.5)",
      mutedForeground: "oklch(0.58 0.031 107.3)",
      accent: "oklch(0.966 0.005 106.5)",
      border: "oklch(0.93 0.007 106.5)",
      card: "oklch(1 0 0)",
      sidebar: "oklch(0.988 0.003 106.5)",
      sidebarForeground: "oklch(0.153 0.006 107.1)",
      sidebarAccent: "oklch(0.966 0.005 106.5)",
      sidebarBorder: "oklch(0.93 0.007 106.5)",
    },
    dark: {
      surface: "oklch(0.153 0.006 107.1)",
      foreground: "oklch(0.988 0.003 106.5)",
      mutedSurface: "oklch(0.286 0.016 107.4)",
      mutedForeground: "oklch(0.737 0.021 106.9)",
      accent: "oklch(0.286 0.016 107.4)",
      border: "oklch(1 0 0 / 10%)",
      card: "oklch(0.228 0.013 107.4)",
      sidebar: "oklch(0.228 0.013 107.4)",
      sidebarForeground: "oklch(0.988 0.003 106.5)",
      sidebarAccent: "oklch(0.286 0.016 107.4)",
      sidebarBorder: "oklch(1 0 0 / 10%)",
    },
  },
  mist: {
    light: {
      surface: "oklch(1 0 0)",
      foreground: "oklch(0.148 0.004 228.8)",
      mutedSurface: "oklch(0.963 0.002 197.1)",
      mutedForeground: "oklch(0.56 0.021 213.5)",
      accent: "oklch(0.963 0.002 197.1)",
      border: "oklch(0.925 0.005 214.3)",
      card: "oklch(1 0 0)",
      sidebar: "oklch(0.987 0.002 197.1)",
      sidebarForeground: "oklch(0.148 0.004 228.8)",
      sidebarAccent: "oklch(0.963 0.002 197.1)",
      sidebarBorder: "oklch(0.925 0.005 214.3)",
    },
    dark: {
      surface: "oklch(0.148 0.004 228.8)",
      foreground: "oklch(0.987 0.002 197.1)",
      mutedSurface: "oklch(0.275 0.011 216.9)",
      mutedForeground: "oklch(0.723 0.014 214.4)",
      accent: "oklch(0.275 0.011 216.9)",
      border: "oklch(1 0 0 / 10%)",
      card: "oklch(0.218 0.008 223.9)",
      sidebar: "oklch(0.218 0.008 223.9)",
      sidebarForeground: "oklch(0.987 0.002 197.1)",
      sidebarAccent: "oklch(0.275 0.011 216.9)",
      sidebarBorder: "oklch(1 0 0 / 10%)",
    },
  },
  taupe: {
    light: {
      surface: "oklch(1 0 0)",
      foreground: "oklch(0.147 0.004 49.3)",
      mutedSurface: "oklch(0.96 0.002 17.2)",
      mutedForeground: "oklch(0.547 0.021 43.1)",
      accent: "oklch(0.96 0.002 17.2)",
      border: "oklch(0.922 0.005 34.3)",
      card: "oklch(1 0 0)",
      sidebar: "oklch(0.986 0.002 67.8)",
      sidebarForeground: "oklch(0.147 0.004 49.3)",
      sidebarAccent: "oklch(0.96 0.002 17.2)",
      sidebarBorder: "oklch(0.922 0.005 34.3)",
    },
    dark: {
      surface: "oklch(0.147 0.004 49.3)",
      foreground: "oklch(0.986 0.002 67.8)",
      mutedSurface: "oklch(0.268 0.011 36.5)",
      mutedForeground: "oklch(0.714 0.014 41.2)",
      accent: "oklch(0.268 0.011 36.5)",
      border: "oklch(1 0 0 / 10%)",
      card: "oklch(0.214 0.009 43.1)",
      sidebar: "oklch(0.214 0.009 43.1)",
      sidebarForeground: "oklch(0.986 0.002 67.8)",
      sidebarAccent: "oklch(0.268 0.011 36.5)",
      sidebarBorder: "oklch(1 0 0 / 10%)",
    },
  },
};

const ACTION_COLOR_SEEDS = {
  blue: "#066fd1",
  azure: "#4299e1",
  indigo: "#4263eb",
  purple: "#ae3ec9",
  pink: "#d6336c",
  red: "#d63939",
  orange: "#f76707",
  yellow: "#facc15",
  lime: "#74b816",
  green: "#2fb344",
  teal: "#0ca678",
  cyan: "#17a2b8",
};

const ACTION_PRIMARY_STEPS = [500, 600, 700, 800, 900];
const ACTION_PRIMARY_LIGHT_FOREGROUND = [255, 255, 255];
const ACTION_PRIMARY_DARK_FOREGROUND = [17, 24, 39];
const ACTION_PRIMARY_DARK_FOREGROUND_COLORS = new Set(["yellow"]);
const ACTION_PRIMARY_MIN_CONTRAST = 4.5;

const THEME_COLOR_TOKENS = {
  neutral: {},
  ...Object.fromEntries(
    Object.entries(ACTION_COLOR_SEEDS).map(([name, seed]) => [
      name,
      colorTokensFromSeed(name, seed),
    ])
  ),
};

const CHART_COLOR_TOKENS = {
  neutral: chartTokens([
    "rgb(82, 82, 91)",
    "rgb(113, 113, 122)",
    "rgb(161, 161, 170)",
    "rgb(63, 63, 70)",
    "rgb(39, 39, 42)",
  ]),
  ...Object.fromEntries(
    Object.entries(ACTION_COLOR_SEEDS).map(([name, seed]) => [
      name,
      chartTokensFromSeed(seed),
    ])
  ),
};

const RADIUS_TOKENS = {
  default: {},
  none: {
    "--bs-border-radius": "0",
    "--bs-border-radius-sm": "0",
    "--bs-border-radius-lg": "0",
    "--bs-border-radius-xl": "0",
    "--bs-border-radius-xxl": "0",
  },
  small: {
    "--bs-border-radius": "0.25rem",
    "--bs-border-radius-sm": "0.1875rem",
    "--bs-border-radius-lg": "0.375rem",
    "--bs-border-radius-xl": "0.5rem",
    "--bs-border-radius-xxl": "0.75rem",
  },
  medium: {
    "--bs-border-radius": "0.5rem",
    "--bs-border-radius-sm": "0.375rem",
    "--bs-border-radius-lg": "0.625rem",
    "--bs-border-radius-xl": "0.75rem",
    "--bs-border-radius-xxl": "1rem",
  },
  large: {
    "--bs-border-radius": "0.75rem",
    "--bs-border-radius-sm": "0.5rem",
    "--bs-border-radius-lg": "1rem",
    "--bs-border-radius-xl": "1.25rem",
    "--bs-border-radius-xxl": "1.5rem",
  },
};

const FONT_TOKENS = {
  headingFont: {
    default: {},
    geist: { "--moo-heading-font-family": '"Geist", var(--bs-body-font-family)' },
    system: { "--moo-heading-font-family": 'system-ui, -apple-system, "Segoe UI", sans-serif' },
  },
  bodyFont: {
    default: {},
    geist: {
      "--bs-body-font-family": '"Geist", system-ui, -apple-system, "Segoe UI", sans-serif',
    },
    system: {
      "--bs-body-font-family": 'system-ui, -apple-system, "Segoe UI", sans-serif',
    },
  },
};

const SIDEBAR_ACCENT_TOKENS = {
  light: {
    "--moo-sidebar-accent": "color-mix(in srgb, var(--moo-ring) 10%, var(--moo-sidebar))",
  },
  dark: {
    "--moo-sidebar-accent": "color-mix(in srgb, var(--moo-ring) 32%, var(--moo-sidebar))",
  },
};

// Keep both foreground tokens for preset compatibility; the action scale is
// mode-independent in RC.3, so dark foreground intentionally mirrors light.
function colorTokensFromSeed(name, seed) {
  const scale = colorScale(seed);
  const foregroundColor = actionPrimaryForeground(name);
  const primaryStep = actionPrimaryStep(scale, foregroundColor);
  const primary = scale[primaryStep];
  const hover = scale[Math.min(primaryStep + 100, 900)];
  const ring = scale[primaryStep > 600 ? primaryStep - 200 : 400];
  const foreground = rgbValue(foregroundColor);

  return {
    "--bs-primary": rgbValue(primary),
    "--bs-primary-rgb": rgbCsv(primary),
    "--bs-link-color": rgbValue(primary),
    "--bs-link-hover-color": rgbValue(hover),
    "--bs-focus-ring-color": `rgba(${rgbCsv(primary)}, 0.25)`,
    "--moo-primary": rgbValue(primary),
    "--moo-primary-foreground": foreground,
    "--moo-primary-foreground-dark": foreground,
    "--moo-ring": rgbValue(ring),
  };
}

function actionPrimaryForeground(name) {
  return ACTION_PRIMARY_DARK_FOREGROUND_COLORS.has(name)
    ? ACTION_PRIMARY_DARK_FOREGROUND
    : ACTION_PRIMARY_LIGHT_FOREGROUND;
}

function actionPrimaryStep(scale, foreground) {
  const accessibleStep = ACTION_PRIMARY_STEPS.find(
    (step) =>
      contrastRatio(scale[step], foreground) >=
      ACTION_PRIMARY_MIN_CONTRAST
  );
  if (accessibleStep !== undefined) {
    return accessibleStep;
  }

  return ACTION_PRIMARY_STEPS.reduce((best, step) => {
    const contrast = contrastRatio(scale[step], foreground);
    return contrast > best.contrast ? { step, contrast } : best;
  }, { step: ACTION_PRIMARY_STEPS[0], contrast: -Infinity }).step;
}

function chartTokens(values) {
  return Object.fromEntries(values.map((value, index) => [`--moo-chart-${index + 1}`, value]));
}

function chartTokensFromSeed(seed) {
  return chartTokenEntriesFromScale(colorScale(seed));
}

function chartTokenEntriesFromScale(scale) {
  return chartTokens([
    rgbValue(scale[500]),
    rgbValue(scale[400]),
    rgbValue(scale[300]),
    rgbValue(scale[600]),
    rgbValue(scale[700]),
  ]);
}

function colorScale(seed) {
  const rgb = hexToRgb(seed);
  return {
    100: tintRgb(rgb, 80),
    200: tintRgb(rgb, 60),
    300: tintRgb(rgb, 40),
    400: tintRgb(rgb, 20),
    500: rgb,
    600: shadeRgb(rgb, 20),
    700: shadeRgb(rgb, 40),
    800: shadeRgb(rgb, 60),
    900: shadeRgb(rgb, 80),
  };
}

function hexToRgb(hex) {
  const value = Number.parseInt(hex.replace("#", ""), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function tintRgb(rgb, weight) {
  return mixRgb([255, 255, 255], rgb, weight);
}

function shadeRgb(rgb, weight) {
  return mixRgb([0, 0, 0], rgb, weight);
}

function mixRgb(target, rgb, weight) {
  const ratio = weight / 100;
  return rgb.map((channel, index) =>
    Math.round(target[index] * ratio + channel * (1 - ratio))
  );
}

function rgbValue(rgb) {
  return `rgb(${rgbCsv(rgb)})`;
}

function rgbCsv(rgb) {
  return rgb.join(", ");
}

function contrastRatio(a, b) {
  const [lighter, darker] = [relativeLuminance(a), relativeLuminance(b)].sort(
    (left, right) => right - left
  );
  return (lighter + 0.05) / (darker + 0.05);
}

function relativeLuminance(rgb) {
  const [red, green, blue] = rgb.map((channel) => {
    const value = channel / 255;
    return value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function cleanObject(candidate) {
  return candidate && typeof candidate === "object" && !Array.isArray(candidate)
    ? candidate
    : {};
}

function enumValue(key, candidate) {
  const aliases =
    key === "baseColor"
      ? BASE_COLOR_ALIASES
      : key === "themeColor" || key === "chartColor"
        ? ACTION_COLOR_ALIASES
        : key === "radius"
          ? RADIUS_ALIASES
        : {};
  const value = Object.hasOwn(aliases, candidate) ? aliases[candidate] : candidate;
  return OPTION_SETS[key].has(value) ? value : THEME_BUILDER_DEFAULTS[key];
}

function colorMode(candidate) {
  return candidate === "dark" ? "dark" : "light";
}

export function normalizeThemeBuilderState(candidate = {}) {
  const source = cleanObject(candidate);
  const legacyThemeColor =
    source.themeColor === undefined && LEGACY_ACTION_BASE_COLORS.has(source.baseColor)
      ? source.baseColor
      : undefined;
  const chartColor = source.chartColor ?? source.chartPalette;

  return {
    schemaVersion: THEME_BUILDER_SCHEMA_VERSION,
    baseColor: enumValue("baseColor", source.baseColor),
    themeColor: enumValue("themeColor", source.themeColor ?? legacyThemeColor),
    chartColor: enumValue("chartColor", chartColor),
    headingFont: enumValue("headingFont", source.headingFont),
    bodyFont: enumValue("bodyFont", source.bodyFont),
    radius: enumValue("radius", source.radius),
  };
}

function fullBaseColorTokens(scale) {
  if (!scale) {
    return {};
  }
  return {
    "--moo-surface": scale.surface,
    "--moo-foreground": scale.foreground,
    "--moo-muted-surface": scale.mutedSurface,
    "--moo-muted-foreground": scale.mutedForeground,
    "--moo-border": scale.border,
    "--bs-body-bg": "var(--moo-surface)",
    "--bs-body-color": "var(--moo-foreground)",
    "--bs-secondary-color": "var(--moo-muted-foreground)",
    "--bs-secondary-bg": "var(--moo-muted-surface)",
    "--bs-tertiary-bg": scale.accent,
    "--bs-border-color": "var(--moo-border)",
    "--bs-card-bg": scale.card,
    "--bs-card-border-color": "var(--moo-border)",
    "--moo-sidebar": scale.sidebar,
    "--moo-sidebar-foreground": scale.sidebarForeground,
    "--moo-sidebar-accent": scale.sidebarAccent,
    "--moo-sidebar-border": scale.sidebarBorder,
  };
}

function catalogBaseColorTokens(scale) {
  if (!scale) {
    return {};
  }
  return {
    "--moo-surface": scale.surface,
    "--moo-muted-surface": scale.mutedSurface,
    "--moo-border": scale.border,
    "--bs-body-bg": "var(--moo-surface)",
    "--bs-secondary-bg": "var(--moo-muted-surface)",
    "--bs-tertiary-bg": scale.accent,
    "--bs-border-color": "var(--moo-border)",
    "--bs-card-bg": scale.card,
    "--bs-card-border-color": "var(--moo-border)",
    "--moo-sidebar": scale.sidebar,
    "--moo-sidebar-accent": scale.sidebarAccent,
    "--moo-sidebar-border": scale.sidebarBorder,
  };
}

// Catalog preview keeps Base color scoped to surfaces and borders so body,
// muted, and sidebar text stay neutral while cards, inputs, and shells move.
// The default public resolver surface remains the full preset token set.
function baseColorTokensFor(state, mode, surface) {
  if (state.baseColor === "neutral") {
    return { ...NEUTRAL_BASE_BORDER_TOKENS[mode] };
  }
  const scale = BASE_COLOR_SCALES[state.baseColor]?.[mode] || null;
  return surface === "catalog"
    ? catalogBaseColorTokens(scale)
    : fullBaseColorTokens(scale);
}

function sidebarAccentTokensFor(state, mode) {
  if (state.themeColor === THEME_BUILDER_DEFAULTS.themeColor) {
    return {};
  }
  return SIDEBAR_ACCENT_TOKENS[mode];
}

export function resolveThemeBuilderTokens(
  candidate = {},
  { theme = "light", surface = "export" } = {}
) {
  const state = normalizeThemeBuilderState(candidate);
  const mode = colorMode(theme);
  return {
    ...baseColorTokensFor(state, mode, surface),
    ...THEME_COLOR_TOKENS[state.themeColor],
    ...CHART_COLOR_TOKENS[state.chartColor],
    ...RADIUS_TOKENS[state.radius],
    ...FONT_TOKENS.headingFont[state.headingFont],
    ...FONT_TOKENS.bodyFont[state.bodyFont],
    ...sidebarAccentTokensFor(state, mode),
  };
}

function baseColorPayload() {
  return Object.fromEntries(
    THEME_BUILDER_OPTIONS.baseColor.map((baseColor) => [
      baseColor,
      {
        light: baseColorTokensFor({ baseColor }, "light", "catalog"),
        dark: baseColorTokensFor({ baseColor }, "dark", "catalog"),
      },
    ])
  );
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function createThemeBuilderFirstPaintPayload() {
  return cloneJson({
    schemaVersion: THEME_BUILDER_SCHEMA_VERSION,
    defaults: THEME_BUILDER_DEFAULTS,
    options: THEME_BUILDER_OPTIONS,
    aliases: {
      baseColor: BASE_COLOR_ALIASES,
      actionColor: ACTION_COLOR_ALIASES,
      radius: RADIUS_ALIASES,
    },
    legacyActionBaseColors: Array.from(LEGACY_ACTION_BASE_COLORS),
    tokens: {
      baseColor: baseColorPayload(),
      themeColor: THEME_COLOR_TOKENS,
      chartColor: CHART_COLOR_TOKENS,
      radius: RADIUS_TOKENS,
      headingFont: FONT_TOKENS.headingFont,
      bodyFont: FONT_TOKENS.bodyFont,
      sidebarAccent: SIDEBAR_ACCENT_TOKENS,
    },
  });
}
