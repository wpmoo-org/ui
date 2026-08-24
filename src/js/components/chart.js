// MooChart — the public Moo UI Chart component. A thin, theme-aware
// wrapper around Chart.js (bundled at build time through `chart.js/auto`).
//
// Markup contract (see api-freeze-1.0.0-rc.3.json):
//
//   <div class="moo-chart" data-chart="line"
//        data-chart-data='{"labels":[],"datasets":[]}'
//        data-chart-options='{"plugins":{"legend":{"display":false}}}'>
//     <canvas></canvas>
//   </div>
//
// `.moo-chart` is the public root class, `data-chart` is the
// type/init attribute, and `data-chart-data` carries the serialized
// chart data. `data-chart-options` is an optional JSON-object Chart.js
// options pass-through for copyable HTML examples. The canvas is resolved
// deterministically as the first child <canvas>. Invalid elements, a missing
// canvas, and malformed JSON all fail with explicit errors rather than
// rendering an empty chart.
//
// Chart.js is imported as a module and bundled into the published ESM
// output; this wrapper never reads `window.Chart` and never loads a
// runtime CDN script.

import Chart from "chart.js/auto";

const instances = new WeakMap();
const CHART_TYPES = new Map([
  [
    "area",
    {
      chartType: "line",
      family: "cartesian",
      fillByDefault: true,
      pointRadiusDefault: 0,
    },
  ],
  ["line", { chartType: "line", family: "cartesian", fillByDefault: true }],
  ["bar", { chartType: "bar", family: "cartesian" }],
  ["pie", { chartType: "pie", family: "arc" }],
  ["doughnut", { chartType: "doughnut", family: "arc" }],
  ["polarArea", { chartType: "polarArea", family: "radial" }],
  ["radar", { chartType: "radar", family: "radial" }],
  ["scatter", { chartType: "scatter", family: "point" }],
  ["bubble", { chartType: "bubble", family: "point" }],
]);
const SUPPORTED_TYPE_LIST = Array.from(CHART_TYPES.keys());
const UNSAFE_OPTION_KEYS = new Set(["__proto__", "constructor", "prototype"]);
const POINT_MARKER_SIZE = 6;
const POINT_MARKER_RADIUS = POINT_MARKER_SIZE / 2;
const POINT_HOVER_RADIUS = 5;
const CHART_LABEL_FONT_SIZE = 12;
const LINE_STROKE_WIDTH = 1.5;
const RADAR_STROKE_WIDTH = 1.5;
const MARKER_BORDER_WIDTH = 1;
const POINT_MARKER_STYLE = "circle";
const TOOLTIP_MARKER_SIZE = POINT_MARKER_SIZE * Math.SQRT2;
const TOOLTIP_MARKER_BOX_PADDING =
  POINT_MARKER_SIZE + CHART_LABEL_FONT_SIZE / 2 - TOOLTIP_MARKER_SIZE - 2;
const THEMED_DATASET_STATE = Symbol("mooChartThemeState");
const DATASET_COLOR_FIELDS = [
  "backgroundColor",
  "borderColor",
  "hoverBackgroundColor",
  "hoverBorderColor",
  "pointBackgroundColor",
  "pointBorderColor",
  "pointHoverBackgroundColor",
  "pointHoverBorderColor",
];

// Bootstrap semantic color tokens plus optional Moo chart palette tokens the
// chart palette is derived from.
const COLOR_TOKENS = [
  "--bs-body-color",
  "--bs-body-bg",
  "--bs-secondary-color",
  "--bs-secondary-bg",
  "--bs-tertiary-color",
  "--bs-tertiary-bg",
  "--bs-border-color",
  "--bs-primary",
  "--bs-success",
  "--bs-info",
  "--bs-warning",
  "--bs-danger",
  "--bs-emphasis-color",
  "--bs-info-text-emphasis",
  "--bs-success-text-emphasis",
  "--bs-warning-text-emphasis",
  "--bs-danger-text-emphasis",
  "--moo-chart-1",
  "--moo-chart-2",
  "--moo-chart-3",
  "--moo-chart-4",
  "--moo-chart-5",
];

// Dataset colors cycle through the chart palette in this order.
const DATASET_COLOR_KEYS = ["primary", "success", "info", "warning", "danger"];

function readThemeColors(themeElement, window) {
  const styles = window?.getComputedStyle?.(themeElement);
  const colors = {};
  if (!styles) return colors;
  COLOR_TOKENS.forEach((token) => {
    colors[token] = styles.getPropertyValue(token).trim();
  });
  return colors;
}

function resolveThemeElement(element) {
  return (
    element?.closest?.("[data-bs-theme]") ||
    element?.ownerDocument?.documentElement ||
    null
  );
}

function themeElementIsDark(element) {
  const theme =
    element?.getAttribute?.("data-bs-theme") ||
    element?.dataset?.bsTheme;
  return theme === "dark";
}

function resolveCanvasColor(document, window, value, fallback, themeElement) {
  const createElement = document?.createElement;
  const getComputedStyle = window?.getComputedStyle;
  const root = document?.documentElement;
  if (!createElement || !getComputedStyle || !root) return fallback;

  const probe = createElement.call(document, "span");
  probe.style.color = value;
  if (!probe.style.color) return fallback;
  probe.hidden = true;
  const parent = themeElement?.appendChild ? themeElement : root;
  parent.appendChild(probe);
  try {
    const resolved = getComputedStyle.call(window, probe).color;
    return resolved || fallback;
  } finally {
    probe.remove();
  }
}

// Build a Chart.js color palette from the current theme's CSS variables.
function buildChartTheme(colors, isDark = false, resolveColor = (value) => value) {
  // Use the same semantic chart palette in both themes. Bootstrap's primary
  // token is intentionally near-black in dark mode, so chart data uses blue
  // info tokens instead of switching to a grayscale series.
  const lightPalette = {
    primary:
      colors["--moo-chart-1"] ||
      colors["--bs-info"] ||
      colors["--bs-info-text-emphasis"],
    success: colors["--moo-chart-2"] || colors["--bs-success"],
    info: colors["--moo-chart-3"] || colors["--bs-info"],
    warning: colors["--moo-chart-4"] || colors["--bs-warning"],
    danger: colors["--moo-chart-5"] || colors["--bs-danger"],
  };
  const darkPalette = {
    primary:
      colors["--moo-chart-1"] ||
      colors["--bs-info-text-emphasis"] ||
      colors["--bs-info"],
    success:
      colors["--moo-chart-2"] ||
      colors["--bs-success-text-emphasis"] ||
      colors["--bs-success"],
    info:
      colors["--moo-chart-3"] ||
      colors["--bs-info-text-emphasis"] ||
      colors["--bs-info"],
    warning:
      colors["--moo-chart-4"] ||
      colors["--bs-warning-text-emphasis"] ||
      colors["--bs-warning"],
    danger:
      colors["--moo-chart-5"] ||
      colors["--bs-danger-text-emphasis"] ||
      colors["--bs-danger"],
  };
  const palette = isDark ? darkPalette : lightPalette;

  return {
    color: colors["--bs-body-color"],
    backgroundColor: colors["--bs-body-bg"],
    borderColor: colors["--bs-border-color"],
    // Grid lines use secondary-color (text) instead of border-color so they
    // remain visible in both light and dark modes. Border-color is too dark
    // in dark mode; secondary-color adapts better to the theme.
    gridColor: colors["--bs-secondary-color"],
    tickColor: colors["--bs-secondary-color"],
    textColor: colors["--bs-body-color"],
    secondaryText: colors["--bs-secondary-color"],
    resolveColor,
    ...palette,
  };
}

function translucentColor(theme, color, amount = 22) {
  return theme.resolveColor(
    `color-mix(in srgb, ${color} ${amount}%, transparent)`,
    color,
  );
}

function mutedSeriesColor(theme, color) {
  return theme.resolveColor(
    `color-mix(in srgb, ${color} 92%, ${theme.color})`,
    color,
  );
}

function datasetColors(theme, count) {
  return Array.from({ length: Math.max(count, 1) }, (_, itemIndex) => {
    const colorKey = DATASET_COLOR_KEYS[itemIndex % DATASET_COLOR_KEYS.length];
    return theme[colorKey];
  });
}

function datasetThemeState(dataset) {
  if (!dataset[THEMED_DATASET_STATE]) {
    const explicitColorFields = new Set(
      DATASET_COLOR_FIELDS.filter((field) =>
        Object.prototype.hasOwnProperty.call(dataset, field)
      )
    );
    Object.defineProperty(dataset, THEMED_DATASET_STATE, {
      value: { explicitColorFields },
    });
  }
  return dataset[THEMED_DATASET_STATE];
}

function setThemedColor(dataset, field, value, themeState) {
  if (!themeState.explicitColorFields.has(field)) {
    dataset[field] = value;
  }
}

function tooltipPointStyle() {
  return {
    pointStyle: POINT_MARKER_STYLE,
    rotation: 0,
  };
}

function tooltipLabelColor(context) {
  const meta = context.chart.getDatasetMeta(context.datasetIndex);
  const options = meta.controller.getStyle(context.dataIndex);
  return {
    borderColor: options.borderColor,
    backgroundColor: options.backgroundColor,
    borderWidth: MARKER_BORDER_WIDTH,
    borderDash: options.borderDash,
    borderDashOffset: options.borderDashOffset,
    borderRadius: 0,
  };
}

function legendLabels(chart) {
  return Chart.defaults.plugins.legend.labels.generateLabels(chart).map((item) => ({
    ...item,
    lineWidth: MARKER_BORDER_WIDTH,
  }));
}

function datasetMetadata(dataset, metadata) {
  return dataset.type && CHART_TYPES.has(dataset.type)
    ? CHART_TYPES.get(dataset.type)
    : metadata;
}

// Apply themed colors to a dataset in place, keyed by its position.
function themeDataset(dataset, index, metadata, theme) {
  const colorKey = DATASET_COLOR_KEYS[index % DATASET_COLOR_KEYS.length];
  const color = theme[colorKey];
  // Keep both themes close to their semantic token so the hue remains
  // consistent when the user toggles the theme.
  const mutedColor = mutedSeriesColor(theme, color);
  const pointColor = color;
  const effectiveMetadata = datasetMetadata(dataset, metadata);
  const datasetType = dataset.type || effectiveMetadata.chartType;
  const themeState = datasetThemeState(dataset);

  if (datasetType === "line") {
    setThemedColor(dataset, "borderColor", mutedColor, themeState);
    setThemedColor(
      dataset,
      "backgroundColor",
      translucentColor(theme, color),
      themeState,
    );
    setThemedColor(dataset, "pointBackgroundColor", pointColor, themeState);
    setThemedColor(dataset, "pointBorderColor", pointColor, themeState);
    dataset.pointBorderWidth = 0;
    if (dataset.borderWidth === undefined) {
      dataset.borderWidth = LINE_STROKE_WIDTH;
    }
    if (dataset.pointRadius === undefined) {
      dataset.pointRadius =
        effectiveMetadata.pointRadiusDefault ?? POINT_MARKER_RADIUS;
    }
    dataset.pointHoverRadius = POINT_HOVER_RADIUS;
    setThemedColor(
      dataset,
      "pointHoverBackgroundColor",
      pointColor,
      themeState,
    );
    setThemedColor(dataset, "pointHoverBorderColor", pointColor, themeState);
    dataset.pointHoverBorderWidth = 0;
    if (dataset.tension === undefined) dataset.tension = 0.3;
    if (effectiveMetadata.fillByDefault && dataset.fill === undefined) {
      dataset.fill = true;
    }
  } else if (datasetType === "bar") {
    setThemedColor(
      dataset,
      "backgroundColor",
      theme.resolveColor(
        `color-mix(in srgb, ${color} 78%, transparent)`,
        color,
      ),
      themeState,
    );
    setThemedColor(dataset, "borderColor", mutedColor, themeState);
    dataset.borderWidth = 1;
    setThemedColor(dataset, "hoverBackgroundColor", color, themeState);
    setThemedColor(dataset, "hoverBorderColor", color, themeState);
    dataset.borderRadius = 4;
  } else if (
    datasetType === "pie" ||
    datasetType === "doughnut" ||
    datasetType === "polarArea"
  ) {
    const colors = datasetColors(theme, dataset.data?.length || 0);
    setThemedColor(
      dataset,
      "backgroundColor",
      colors.map((seriesColor) =>
        translucentColor(theme, seriesColor, 78)
      ),
      themeState,
    );
    setThemedColor(
      dataset,
      "borderColor",
      colors.map((seriesColor) =>
        mutedSeriesColor(theme, seriesColor)
      ),
      themeState,
    );
    setThemedColor(dataset, "hoverBackgroundColor", colors, themeState);
    setThemedColor(dataset, "hoverBorderColor", colors, themeState);
    if (dataset.borderWidth === undefined) dataset.borderWidth = 1;
  } else if (datasetType === "radar") {
    setThemedColor(dataset, "borderColor", mutedColor, themeState);
    setThemedColor(
      dataset,
      "backgroundColor",
      translucentColor(theme, color, 18),
      themeState,
    );
    setThemedColor(dataset, "pointBackgroundColor", pointColor, themeState);
    setThemedColor(dataset, "pointBorderColor", pointColor, themeState);
    setThemedColor(
      dataset,
      "pointHoverBackgroundColor",
      pointColor,
      themeState,
    );
    setThemedColor(dataset, "pointHoverBorderColor", pointColor, themeState);
    if (dataset.borderWidth === undefined) {
      dataset.borderWidth = RADAR_STROKE_WIDTH;
    }
    if (dataset.pointRadius === undefined) dataset.pointRadius = POINT_MARKER_RADIUS;
    if (dataset.pointHoverRadius === undefined) {
      dataset.pointHoverRadius = POINT_HOVER_RADIUS;
    }
    if (dataset.pointHoverBorderWidth === undefined) {
      dataset.pointHoverBorderWidth = 0;
    }
    if (dataset.fill === undefined) dataset.fill = true;
  } else if (datasetType === "scatter" || datasetType === "bubble") {
    setThemedColor(
      dataset,
      "backgroundColor",
      translucentColor(theme, color, 72),
      themeState,
    );
    setThemedColor(dataset, "borderColor", mutedColor, themeState);
    setThemedColor(dataset, "hoverBackgroundColor", color, themeState);
    setThemedColor(dataset, "hoverBorderColor", color, themeState);
    if (dataset.borderWidth === undefined) dataset.borderWidth = 1;
    if (datasetType === "scatter") {
      if (dataset.pointRadius === undefined) {
        dataset.pointRadius = POINT_MARKER_RADIUS;
      }
      if (dataset.pointHoverRadius === undefined) {
        dataset.pointHoverRadius = POINT_HOVER_RADIUS;
      }
      if (dataset.pointHoverBorderWidth === undefined) {
        dataset.pointHoverBorderWidth = 0;
      }
    } else if (dataset.pointHoverRadius === undefined) {
      dataset.pointHoverRadius = 7;
    }
  }
  return dataset;
}

// Apply theme colors to an already-built Chart.js instance (re-theming).
function applyThemeToChart(chart, theme, metadata) {
  if (!chart) return;

  chart.data.datasets.forEach((dataset, index) => {
    themeDataset(dataset, index, metadata, theme);
  });

  // Update scale colors.
  if (chart.options.scales) {
    Object.values(chart.options.scales).forEach((scale) => {
      if (scale.grid) {
        scale.grid.color = theme.resolveColor(
          `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`,
          theme.gridColor,
        );
      }
      if (scale.ticks) {
        scale.ticks.color = theme.secondaryText;
      }
      if (scale.title) {
        scale.title.color = theme.textColor;
      }
      if (scale.angleLines) {
        scale.angleLines.color = theme.resolveColor(
          `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`,
          theme.gridColor,
        );
      }
      if (scale.pointLabels) {
        scale.pointLabels.color = theme.secondaryText;
      }
    });
  }

  // Update legend colors.
  if (chart.options.plugins?.legend?.labels) {
    chart.options.plugins.legend.labels.color = theme.textColor;
  }

  // Update tooltip colors.
  if (chart.options.plugins?.tooltip) {
    chart.options.plugins.tooltip.backgroundColor = theme.backgroundColor;
    chart.options.plugins.tooltip.titleColor = theme.textColor;
    chart.options.plugins.tooltip.bodyColor = theme.secondaryText;
    chart.options.plugins.tooltip.borderColor = theme.borderColor;
  }

  chart.update("none");
}

function themedGrid(theme) {
  return {
    color: theme.resolveColor(
      `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`,
      theme.gridColor,
    ),
  };
}

function themedTicks(theme, extra = {}) {
  return {
    color: theme.secondaryText,
    padding: 8,
    ...extra,
  };
}

function cartesianScales(theme, metadata) {
  const scaleType = metadata.family === "point" ? "linear" : undefined;
  return {
    x: {
      ...(scaleType ? { type: scaleType } : {}),
      grid: themedGrid(theme),
      ticks: themedTicks(theme),
      border: {
        display: false,
      },
    },
    y: {
      ...(scaleType ? { type: scaleType } : {}),
      grid: themedGrid(theme),
      ticks: themedTicks(theme),
      border: {
        display: false,
      },
    },
  };
}

function radialScale(theme) {
  return {
    r: {
      angleLines: {
        color: theme.resolveColor(
          `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`,
          theme.gridColor,
        ),
      },
      grid: themedGrid(theme),
      pointLabels: {
        color: theme.secondaryText,
      },
      ticks: themedTicks(theme, {
        backdropColor: "transparent",
      }),
    },
  };
}

function defaultInteraction(metadata) {
  if (metadata.family === "point" || metadata.family === "arc" || metadata.family === "radial") {
    return {
      mode: "nearest",
      intersect: true,
    };
  }
  return {
    mode: "index",
    intersect: false,
  };
}

function prefersReducedMotion(window) {
  return !!window?.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
}

function formatNumber(value) {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString()
    : "";
}

function tooltipLabel(context) {
  const label = context.dataset.label || context.label || "";
  const parsed = context.parsed;
  const raw = context.raw;

  if (parsed !== null && typeof parsed === "object") {
    const values = [];
    if (typeof parsed.x === "number" && Number.isFinite(parsed.x)) {
      values.push(`X: ${formatNumber(parsed.x)}`);
    }
    if (typeof parsed.y === "number" && Number.isFinite(parsed.y)) {
      values.push(`Y: ${formatNumber(parsed.y)}`);
    }
    if (raw && typeof raw === "object" && typeof raw.r === "number") {
      values.push(`Radius: ${formatNumber(raw.r)}`);
    }
    if (!values.length) return label;
    return label ? `${label}: ${values.join(", ")}` : values.join(", ");
  }

  const value = formatNumber(parsed);
  if (!value) return label;
  return label ? `${label}: ${value}` : value;
}

// Build the Chart.js options object for the approved dashboard appearance.
function buildChartOptions(theme, metadata, window) {
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: defaultInteraction(metadata),
    plugins: {
      legend: {
        labels: {
          color: theme.textColor,
          usePointStyle: true,
          pointStyle: POINT_MARKER_STYLE,
          boxWidth: POINT_MARKER_SIZE,
          boxHeight: POINT_MARKER_SIZE,
          generateLabels: legendLabels,
          font: {
            size: CHART_LABEL_FONT_SIZE,
          },
          padding: 20,
        },
      },
      tooltip: {
        backgroundColor: theme.backgroundColor,
        titleColor: theme.textColor,
        bodyColor: theme.secondaryText,
        borderColor: theme.borderColor,
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        titleFont: {
          size: 13,
          weight: "600",
        },
        bodyFont: {
          size: CHART_LABEL_FONT_SIZE,
        },
        bodySpacing: 6,
        usePointStyle: true,
        boxWidth: TOOLTIP_MARKER_SIZE,
        boxHeight: TOOLTIP_MARKER_SIZE,
        boxPadding: TOOLTIP_MARKER_BOX_PADDING,
        callbacks: {
          label: tooltipLabel,
          labelColor: tooltipLabelColor,
          labelPointStyle: tooltipPointStyle,
        },
      },
    },
    animation: {
      duration: 600,
      easing: "easeOutQuart",
    },
    hover: {
      animationDuration: 200,
    },
  };

  if (metadata.family === "cartesian" || metadata.family === "point") {
    options.scales = cartesianScales(theme, metadata);
  } else if (metadata.family === "radial") {
    options.scales = radialScale(theme);
  }

  if (prefersReducedMotion(window)) {
    options.animation = false;
    options.hover.animationDuration = 0;
  }

  return options;
}

// Resolve data-attribute defaults first; an explicit constructor data value
// replaces them. The component does not merge arbitrary dataset payloads.
function resolveChartData(element, config) {
  const raw = element.getAttribute("data-chart-data");
  let attributeData = null;
  let hasAttributeData = false;
  if (raw !== null && raw.trim() !== "") {
    hasAttributeData = true;
    try {
      attributeData = JSON.parse(raw);
    } catch (error) {
      throw new SyntaxError(
        `MooChart could not parse data-chart-data as JSON: ${error.message}`
      );
    }
  }
  const hasConfigData = Object.prototype.hasOwnProperty.call(config, "data");
  if (!hasConfigData && !hasAttributeData) {
    throw new TypeError(
      "MooChart data-chart-data is required unless config.data is provided.",
    );
  }
  const data = hasConfigData ? config.data : attributeData;
  if (
    data === null ||
    data === undefined ||
    typeof data !== "object" ||
    Array.isArray(data) ||
    !Array.isArray(data.labels) ||
    !Array.isArray(data.datasets)
  ) {
    const source = hasConfigData ? "config.data" : "data-chart-data";
    throw new TypeError(
      `MooChart ${source} must contain labels and datasets arrays.`,
    );
  }
  return data;
}

function readOptionsAttribute(element) {
  const raw = element.getAttribute("data-chart-options");
  if (raw === null || raw.trim() === "") return {};
  try {
    const value = JSON.parse(raw);
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
      throw new TypeError("MooChart data-chart-options must be a JSON object.");
    }
    return value;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new SyntaxError(
        `MooChart could not parse data-chart-options as JSON: ${error.message}`,
      );
    }
    throw error;
  }
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function optionEntries(value) {
  return Object.entries(value || {}).filter(
    ([key]) => !UNSAFE_OPTION_KEYS.has(key),
  );
}

function mergeChartOptions(defaults = {}, overrides = {}) {
  const merged = { ...defaults };
  optionEntries(overrides).forEach(([key, value]) => {
    merged[key] =
      isPlainObject(value) && isPlainObject(defaults[key])
        ? mergeChartOptions(defaults[key], value)
        : value;
  });
  return merged;
}

function supportedTypesMessage() {
  return SUPPORTED_TYPE_LIST.slice(0, -1).join(", ")
    + ", and "
    + SUPPORTED_TYPE_LIST[SUPPORTED_TYPE_LIST.length - 1];
}

function resolveChartType(element, config) {
  const publicType =
    config.type ||
    element.getAttribute("data-chart") ||
    "line";
  const metadata = CHART_TYPES.get(publicType);
  if (!metadata) {
    throw new TypeError(
      `MooChart supports ${supportedTypesMessage()} charts; received "${publicType}".`,
    );
  }
  return { publicType, ...metadata };
}

export default class MooChart {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return MooChart.getInstance(element) || new MooChart(element, config);
  }

  constructor(element, config = {}) {
    if (element?.nodeType !== 1 || !element.matches(".moo-chart")) {
      throw new TypeError("MooChart requires a .moo-chart root element.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    const canvas = element.querySelector(":scope > canvas");
    if (!canvas) {
      throw new TypeError(
        "MooChart requires a child <canvas> element inside the .moo-chart root."
      );
    }

    this._element = element;
    this._canvas = canvas;
    this._document = element.ownerDocument;
    this._window = this._document?.defaultView;
    this._config = config || {};
    this._themeElement = resolveThemeElement(element);

    const metadata = resolveChartType(element, this._config);
    const data = resolveChartData(element, this._config);
    const attributeOptions = readOptionsAttribute(element);
    this._type = metadata.publicType;
    this._metadata = metadata;

    const isDark = themeElementIsDark(this._themeElement);
    const colors = readThemeColors(this._themeElement, this._window);
    const resolveColor = (value, fallback) =>
      resolveCanvasColor(
        this._document,
        this._window,
        value,
        fallback,
        this._themeElement,
      );
    this._theme = buildChartTheme(colors, isDark, resolveColor);

    const datasets = (data.datasets || []).map((dataset, index) =>
      themeDataset({ ...dataset }, index, metadata, this._theme)
    );

    const options = mergeChartOptions(
      mergeChartOptions(
        buildChartOptions(this._theme, metadata, this._window),
        attributeOptions,
      ),
      this._config.options,
    );
    this._chart = new Chart(canvas, {
      ...this._config,
      type: metadata.chartType,
      data: {
        labels: data.labels || [],
        datasets,
      },
      options,
    });

    this._rethemeFrame = null;
    this._observer = null;
    if (this._themeElement && this._window?.MutationObserver) {
      this._observer = new this._window.MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (
            mutation.attributeName === "data-bs-theme" ||
            mutation.attributeName === "style"
          ) {
            this._scheduleRetheme();
          }
        });
      });
      this._observer.observe(this._themeElement, {
        attributes: true,
        attributeFilter: ["data-bs-theme", "style"],
      });
    }

    instances.set(element, this);
  }

  // The underlying Chart.js instance, exposed for advanced consumers and
  // lifecycle assertions.
  get chart() {
    return this._chart;
  }

  get element() {
    return this._element;
  }

  _scheduleRetheme() {
    if (this._rethemeFrame !== null) return;
    const schedule = this._window?.requestAnimationFrame;
    if (!schedule) {
      this._applyTheme();
      return;
    }
    this._rethemeFrame = schedule.call(this._window, () => {
      this._rethemeFrame = null;
      this._applyTheme();
    });
  }

  _applyTheme() {
    if (!this._chart) return;
    const isDark = themeElementIsDark(this._themeElement);
    const colors = readThemeColors(this._themeElement, this._window);
    const resolveColor = (value, fallback) =>
      resolveCanvasColor(
        this._document,
        this._window,
        value,
        fallback,
        this._themeElement,
      );
    this._theme = buildChartTheme(colors, isDark, resolveColor);
    applyThemeToChart(this._chart, this._theme, this._metadata);
  }

  dispose() {
    // Cancel any pending re-theme before tearing the chart down.
    if (this._rethemeFrame !== null && this._window?.cancelAnimationFrame) {
      this._window.cancelAnimationFrame(this._rethemeFrame);
    }
    this._rethemeFrame = null;
    // Disconnect the theme observer before destroying the Chart.js instance.
    this._observer?.disconnect();
    this._observer = null;
    this._chart?.destroy();
    this._chart = null;
    if (instances.get(this._element) === this) {
      instances.delete(this._element);
    }
  }
}
