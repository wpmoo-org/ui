export const THEME_BUILDER_SCHEMA_VERSION = 1;

export const THEME_BUILDER_DEFAULTS = {
  schemaVersion: THEME_BUILDER_SCHEMA_VERSION,
  style: "default",
  baseColor: "neutral",
  themeColor: "neutral",
  chartColor: "default",
  headingFont: "default",
  bodyFont: "default",
  radius: "default",
};

export const PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST = [
  "--bs-body-bg",
  "--bs-body-bg-rgb",
  "--bs-body-color",
  "--bs-secondary-color",
  "--bs-secondary-bg",
  "--bs-secondary-bg-rgb",
  "--bs-tertiary-bg",
  "--bs-tertiary-bg-rgb",
  "--bs-border-color",
  "--bs-card-bg",
  "--bs-card-border-color",
  "--bs-primary",
  "--bs-primary-rgb",
  "--bs-link-color",
  "--bs-link-hover-color",
  "--bs-focus-ring-color",
  "--moo-primary",
  "--moo-primary-foreground",
  "--moo-primary-foreground-dark",
  "--moo-ring",
  "--moo-chart-1",
  "--moo-chart-2",
  "--moo-chart-3",
  "--moo-chart-4",
  "--moo-chart-5",
  "--bs-border-radius",
  "--bs-border-radius-sm",
  "--bs-border-radius-lg",
  "--bs-border-radius-xl",
  "--bs-border-radius-xxl",
  "--bs-body-font-family",
  "--moo-heading-font-family",
];

export const THEME_BUILDER_OPTIONS = {
  style: ["default", "soft", "solid", "nova"],
  baseColor: ["neutral", "zinc", "stone", "slate", "mauve"],
  themeColor: [
    "neutral",
    "blue",
    "emerald",
    "violet",
    "amber",
    "rose",
    "cyan",
    "orange",
    "pink",
    "red",
  ],
  chartColor: [
    "default",
    "pastel",
    "vivid",
    "blue",
    "emerald",
    "violet",
    "amber",
    "rose",
  ],
  headingFont: ["default", "geist", "system"],
  bodyFont: ["default", "geist", "system"],
  radius: ["default", "compact", "large"],
};

const OPTION_SETS = Object.fromEntries(
  Object.entries(THEME_BUILDER_OPTIONS).map(([key, values]) => [key, new Set(values)])
);

const LEGACY_ACTION_BASE_COLORS = new Set(["blue", "emerald", "violet"]);

const BASE_COLOR_TOKENS = {
  neutral: { light: {}, dark: {} },
  zinc: {
    light: {
      "--bs-body-bg": "rgb(250, 250, 250)",
      "--bs-body-bg-rgb": "250, 250, 250",
      "--bs-body-color": "rgb(24, 24, 27)",
      "--bs-secondary-color": "rgb(113, 113, 122)",
      "--bs-secondary-bg": "rgb(244, 244, 245)",
      "--bs-secondary-bg-rgb": "244, 244, 245",
      "--bs-tertiary-bg": "rgb(250, 250, 250)",
      "--bs-tertiary-bg-rgb": "250, 250, 250",
      "--bs-border-color": "rgb(228, 228, 231)",
      "--bs-card-bg": "rgb(255, 255, 255)",
      "--bs-card-border-color": "rgb(228, 228, 231)",
    },
    dark: {
      "--bs-body-bg": "rgb(9, 9, 11)",
      "--bs-body-bg-rgb": "9, 9, 11",
      "--bs-body-color": "rgb(244, 244, 245)",
      "--bs-secondary-color": "rgb(161, 161, 170)",
      "--bs-secondary-bg": "rgb(39, 39, 42)",
      "--bs-secondary-bg-rgb": "39, 39, 42",
      "--bs-tertiary-bg": "rgb(24, 24, 27)",
      "--bs-tertiary-bg-rgb": "24, 24, 27",
      "--bs-border-color": "rgb(63, 63, 70)",
      "--bs-card-bg": "rgb(12, 12, 14)",
      "--bs-card-border-color": "rgb(63, 63, 70)",
    },
  },
  stone: {
    light: {
      "--bs-body-bg": "rgb(250, 250, 249)",
      "--bs-body-bg-rgb": "250, 250, 249",
      "--bs-body-color": "rgb(28, 25, 23)",
      "--bs-secondary-color": "rgb(120, 113, 108)",
      "--bs-secondary-bg": "rgb(245, 245, 244)",
      "--bs-secondary-bg-rgb": "245, 245, 244",
      "--bs-tertiary-bg": "rgb(250, 250, 249)",
      "--bs-tertiary-bg-rgb": "250, 250, 249",
      "--bs-border-color": "rgb(231, 229, 228)",
      "--bs-card-bg": "rgb(255, 255, 255)",
      "--bs-card-border-color": "rgb(231, 229, 228)",
    },
    dark: {
      "--bs-body-bg": "rgb(12, 10, 9)",
      "--bs-body-bg-rgb": "12, 10, 9",
      "--bs-body-color": "rgb(245, 245, 244)",
      "--bs-secondary-color": "rgb(168, 162, 158)",
      "--bs-secondary-bg": "rgb(41, 37, 36)",
      "--bs-secondary-bg-rgb": "41, 37, 36",
      "--bs-tertiary-bg": "rgb(28, 25, 23)",
      "--bs-tertiary-bg-rgb": "28, 25, 23",
      "--bs-border-color": "rgb(68, 64, 60)",
      "--bs-card-bg": "rgb(15, 13, 12)",
      "--bs-card-border-color": "rgb(68, 64, 60)",
    },
  },
  slate: {
    light: {
      "--bs-body-bg": "rgb(248, 250, 252)",
      "--bs-body-bg-rgb": "248, 250, 252",
      "--bs-body-color": "rgb(15, 23, 42)",
      "--bs-secondary-color": "rgb(100, 116, 139)",
      "--bs-secondary-bg": "rgb(241, 245, 249)",
      "--bs-secondary-bg-rgb": "241, 245, 249",
      "--bs-tertiary-bg": "rgb(248, 250, 252)",
      "--bs-tertiary-bg-rgb": "248, 250, 252",
      "--bs-border-color": "rgb(226, 232, 240)",
      "--bs-card-bg": "rgb(255, 255, 255)",
      "--bs-card-border-color": "rgb(226, 232, 240)",
    },
    dark: {
      "--bs-body-bg": "rgb(2, 6, 23)",
      "--bs-body-bg-rgb": "2, 6, 23",
      "--bs-body-color": "rgb(248, 250, 252)",
      "--bs-secondary-color": "rgb(148, 163, 184)",
      "--bs-secondary-bg": "rgb(30, 41, 59)",
      "--bs-secondary-bg-rgb": "30, 41, 59",
      "--bs-tertiary-bg": "rgb(15, 23, 42)",
      "--bs-tertiary-bg-rgb": "15, 23, 42",
      "--bs-border-color": "rgb(51, 65, 85)",
      "--bs-card-bg": "rgb(8, 13, 25)",
      "--bs-card-border-color": "rgb(51, 65, 85)",
    },
  },
  mauve: {
    light: {
      "--bs-body-bg": "rgb(251, 250, 252)",
      "--bs-body-bg-rgb": "251, 250, 252",
      "--bs-body-color": "rgb(31, 28, 35)",
      "--bs-secondary-color": "rgb(116, 107, 124)",
      "--bs-secondary-bg": "rgb(246, 243, 248)",
      "--bs-secondary-bg-rgb": "246, 243, 248",
      "--bs-tertiary-bg": "rgb(251, 250, 252)",
      "--bs-tertiary-bg-rgb": "251, 250, 252",
      "--bs-border-color": "rgb(233, 228, 238)",
      "--bs-card-bg": "rgb(255, 255, 255)",
      "--bs-card-border-color": "rgb(233, 228, 238)",
    },
    dark: {
      "--bs-body-bg": "rgb(12, 10, 14)",
      "--bs-body-bg-rgb": "12, 10, 14",
      "--bs-body-color": "rgb(250, 247, 252)",
      "--bs-secondary-color": "rgb(168, 156, 177)",
      "--bs-secondary-bg": "rgb(42, 36, 48)",
      "--bs-secondary-bg-rgb": "42, 36, 48",
      "--bs-tertiary-bg": "rgb(31, 28, 35)",
      "--bs-tertiary-bg-rgb": "31, 28, 35",
      "--bs-border-color": "rgb(70, 62, 78)",
      "--bs-card-bg": "rgb(16, 14, 19)",
      "--bs-card-border-color": "rgb(70, 62, 78)",
    },
  },
};

const THEME_COLOR_TOKENS = {
  neutral: {},
  blue: colorTokens({
    primary: "rgb(37, 99, 235)",
    rgb: "37, 99, 235",
    hover: "rgb(29, 78, 216)",
    ring: "rgb(96, 165, 250)",
    foregroundDark: "rgb(30, 64, 175)",
  }),
  emerald: colorTokens({
    primary: "rgb(5, 150, 105)",
    rgb: "5, 150, 105",
    hover: "rgb(4, 120, 87)",
    ring: "rgb(52, 211, 153)",
    foregroundDark: "rgb(6, 78, 59)",
  }),
  violet: colorTokens({
    primary: "rgb(124, 58, 237)",
    rgb: "124, 58, 237",
    hover: "rgb(109, 40, 217)",
    ring: "rgb(167, 139, 250)",
    foregroundDark: "rgb(76, 29, 149)",
  }),
  amber: colorTokens({
    primary: "rgb(217, 119, 6)",
    rgb: "217, 119, 6",
    hover: "rgb(180, 83, 9)",
    ring: "rgb(251, 191, 36)",
    foregroundDark: "rgb(120, 53, 15)",
  }),
  rose: colorTokens({
    primary: "rgb(225, 29, 72)",
    rgb: "225, 29, 72",
    hover: "rgb(190, 18, 60)",
    ring: "rgb(251, 113, 133)",
    foregroundDark: "rgb(136, 19, 55)",
  }),
  cyan: colorTokens({
    primary: "rgb(8, 145, 178)",
    rgb: "8, 145, 178",
    hover: "rgb(14, 116, 144)",
    ring: "rgb(34, 211, 238)",
    foregroundDark: "rgb(21, 94, 117)",
  }),
  orange: colorTokens({
    primary: "rgb(234, 88, 12)",
    rgb: "234, 88, 12",
    hover: "rgb(194, 65, 12)",
    ring: "rgb(251, 146, 60)",
    foregroundDark: "rgb(124, 45, 18)",
  }),
  pink: colorTokens({
    primary: "rgb(219, 39, 119)",
    rgb: "219, 39, 119",
    hover: "rgb(190, 24, 93)",
    ring: "rgb(244, 114, 182)",
    foregroundDark: "rgb(131, 24, 67)",
  }),
  red: colorTokens({
    primary: "rgb(220, 38, 38)",
    rgb: "220, 38, 38",
    hover: "rgb(185, 28, 28)",
    ring: "rgb(248, 113, 113)",
    foregroundDark: "rgb(127, 29, 29)",
  }),
};

const CHART_COLOR_TOKENS = {
  default: {},
  pastel: chartTokens([
    "rgb(103, 169, 232)",
    "rgb(118, 187, 170)",
    "rgb(246, 198, 110)",
    "rgb(198, 157, 232)",
    "rgb(238, 135, 142)",
  ]),
  vivid: chartTokens([
    "rgb(37, 99, 235)",
    "rgb(5, 150, 105)",
    "rgb(217, 119, 6)",
    "rgb(124, 58, 237)",
    "rgb(225, 29, 72)",
  ]),
  blue: chartTokens([
    "rgb(37, 99, 235)",
    "rgb(96, 165, 250)",
    "rgb(147, 197, 253)",
    "rgb(29, 78, 216)",
    "rgb(30, 64, 175)",
  ]),
  emerald: chartTokens([
    "rgb(5, 150, 105)",
    "rgb(52, 211, 153)",
    "rgb(110, 231, 183)",
    "rgb(4, 120, 87)",
    "rgb(6, 95, 70)",
  ]),
  violet: chartTokens([
    "rgb(139, 92, 246)",
    "rgb(167, 139, 250)",
    "rgb(196, 181, 253)",
    "rgb(124, 58, 237)",
    "rgb(109, 40, 217)",
  ]),
  amber: chartTokens([
    "rgb(217, 119, 6)",
    "rgb(245, 158, 11)",
    "rgb(251, 191, 36)",
    "rgb(180, 83, 9)",
    "rgb(146, 64, 14)",
  ]),
  rose: chartTokens([
    "rgb(225, 29, 72)",
    "rgb(244, 63, 94)",
    "rgb(251, 113, 133)",
    "rgb(190, 18, 60)",
    "rgb(159, 18, 57)",
  ]),
};

const RADIUS_TOKENS = {
  default: {},
  compact: {
    "--bs-border-radius": "0.25rem",
    "--bs-border-radius-sm": "0.1875rem",
    "--bs-border-radius-lg": "0.375rem",
    "--bs-border-radius-xl": "0.5rem",
    "--bs-border-radius-xxl": "0.75rem",
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

function colorTokens({ primary, rgb, hover, ring, foregroundDark }) {
  return {
    "--bs-primary": primary,
    "--bs-primary-rgb": rgb,
    "--bs-link-color": primary,
    "--bs-link-hover-color": hover,
    "--bs-focus-ring-color": `rgba(${rgb}, 0.25)`,
    "--moo-primary": primary,
    "--moo-primary-foreground": "rgb(255, 255, 255)",
    "--moo-primary-foreground-dark": foregroundDark,
    "--moo-ring": ring,
  };
}

function chartTokens(values) {
  return Object.fromEntries(values.map((value, index) => [`--moo-chart-${index + 1}`, value]));
}

function cleanObject(candidate) {
  return candidate && typeof candidate === "object" && !Array.isArray(candidate)
    ? candidate
    : {};
}

function enumValue(key, candidate) {
  return OPTION_SETS[key].has(candidate) ? candidate : THEME_BUILDER_DEFAULTS[key];
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
    style: enumValue("style", source.style),
    baseColor: enumValue("baseColor", source.baseColor),
    themeColor: enumValue("themeColor", source.themeColor ?? legacyThemeColor),
    chartColor: enumValue("chartColor", chartColor),
    headingFont: enumValue("headingFont", source.headingFont),
    bodyFont: enumValue("bodyFont", source.bodyFont),
    radius: enumValue("radius", source.radius),
  };
}

export function resolveThemeBuilderTokens(candidate = {}, { theme = "light" } = {}) {
  const state = normalizeThemeBuilderState(candidate);
  const mode = colorMode(theme);
  return {
    ...BASE_COLOR_TOKENS[state.baseColor][mode],
    ...THEME_COLOR_TOKENS[state.themeColor],
    ...CHART_COLOR_TOKENS[state.chartColor],
    ...RADIUS_TOKENS[state.radius],
    ...FONT_TOKENS.headingFont[state.headingFont],
    ...FONT_TOKENS.bodyFont[state.bodyFont],
  };
}
