// MooChart — the public Moo UI Chart component. A thin, theme-aware
// wrapper around Chart.js (bundled at build time through `chart.js/auto`).
//
// Markup contract (see api-freeze-1.0.0-rc.3.json):
//
//   <div class="moo-chart" data-moo-chart="line"
//        data-moo-chart-data='{"labels":[],"datasets":[]}'>
//     <canvas></canvas>
//   </div>
//
// `.moo-chart` is the public root class, `data-moo-chart` is the
// type/init attribute, and `data-moo-chart-data` carries the serialized
// chart data. The canvas is resolved deterministically as the first child
// <canvas>. Invalid elements, a missing canvas, and malformed JSON all fail
// with explicit errors rather than rendering an empty chart.
//
// Chart.js is imported as a module and bundled into the published ESM
// output; this wrapper never reads `window.Chart` and never loads a
// runtime CDN script.

import Chart from "chart.js/auto";

const instances = new WeakMap();

// Bootstrap semantic color tokens the chart palette is derived from.
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
];

// Dataset colors cycle through the semantic palette in this order.
const DATASET_COLOR_KEYS = ["primary", "success", "info", "warning", "danger"];

function readThemeColors(document, window) {
  const styles = window.getComputedStyle(document.documentElement);
  const colors = {};
  COLOR_TOKENS.forEach((token) => {
    colors[token] = styles.getPropertyValue(token).trim();
  });
  return colors;
}

// Build a Chart.js color palette from the current theme's CSS variables.
function buildChartTheme(colors, isDark = false) {
  // Use the same semantic chart palette in both themes. Bootstrap's primary
  // token is intentionally near-black in dark mode, so chart data uses blue
  // info tokens instead of switching to a grayscale series.
  const lightPalette = {
    primary: colors["--bs-info"] || colors["--bs-info-text-emphasis"],
    success: colors["--bs-success"],
    info: colors["--bs-info"],
    warning: colors["--bs-warning"],
    danger: colors["--bs-danger"],
  };
  const darkPalette = {
    primary: colors["--bs-info-text-emphasis"] || colors["--bs-info"],
    success: colors["--bs-success-text-emphasis"] || colors["--bs-success"],
    info: colors["--bs-info-text-emphasis"] || colors["--bs-info"],
    warning: colors["--bs-warning-text-emphasis"] || colors["--bs-warning"],
    danger: colors["--bs-danger-text-emphasis"] || colors["--bs-danger"],
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
    ...palette,
  };
}

// Apply themed colors to a dataset in place, keyed by its position.
function themeDataset(dataset, index, chartType, theme) {
  const colorKey = DATASET_COLOR_KEYS[index % DATASET_COLOR_KEYS.length];
  const color = theme[colorKey];
  // Keep both themes close to their semantic token so the hue remains
  // consistent when the user toggles the theme.
  const mutedColor = `color-mix(in srgb, ${color} 92%, ${theme.color})`;
  const pointColor = color;
  const datasetType = dataset.type || chartType;

  if (datasetType === "line") {
    dataset.borderColor = mutedColor;
    dataset.backgroundColor = `color-mix(in srgb, ${color} 22%, transparent)`;
    dataset.pointBackgroundColor = pointColor;
    dataset.pointBorderColor = theme.borderColor;
    dataset.pointBorderWidth = 2;
    dataset.pointRadius = 4;
    dataset.pointHoverRadius = 7;
    dataset.pointHoverBackgroundColor = pointColor;
    dataset.pointHoverBorderColor = theme.color;
    dataset.pointHoverBorderWidth = 3;
    if (dataset.tension === undefined) dataset.tension = 0.3;
    if (dataset.fill === undefined) dataset.fill = true;
  } else if (datasetType === "bar") {
    dataset.backgroundColor = `color-mix(in srgb, ${color} 78%, transparent)`;
    dataset.borderColor = mutedColor;
    dataset.borderWidth = 1;
    dataset.hoverBackgroundColor = color;
    dataset.hoverBorderColor = color;
    dataset.borderRadius = 4;
  }
  return dataset;
}

// Apply theme colors to an already-built Chart.js instance (re-theming).
function applyThemeToChart(chart, theme) {
  if (!chart) return;

  const chartType = chart.config.type;
  chart.data.datasets.forEach((dataset, index) => {
    themeDataset(dataset, index, dataset.type || chartType, theme);
  });

  // Update scale colors.
  if (chart.options.scales) {
    Object.values(chart.options.scales).forEach((scale) => {
      if (scale.grid) {
        scale.grid.color = `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`;
      }
      if (scale.ticks) {
        scale.ticks.color = theme.secondaryText;
      }
      if (scale.title) {
        scale.title.color = theme.textColor;
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

  chart.update();
}

// Build the Chart.js options object for the approved dashboard appearance.
function buildChartOptions(theme) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        labels: {
          color: theme.textColor,
          usePointStyle: true,
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
          size: 12,
        },
        bodySpacing: 6,
        usePointStyle: true,
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || "";
            const value = context.parsed.y || context.parsed;
            return `${label}: ${value.toLocaleString()}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`,
          drawBorder: false,
        },
        ticks: {
          color: theme.secondaryText,
          padding: 8,
        },
        border: {
          display: false,
        },
      },
      y: {
        grid: {
          color: `color-mix(in srgb, ${theme.gridColor} 35%, transparent)`,
          drawBorder: false,
        },
        ticks: {
          color: theme.secondaryText,
          padding: 8,
        },
        border: {
          display: false,
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
}

// Merge order: data-attribute defaults < constructor config < programmatic
// overrides. Later sources override earlier sources.
function resolveChartData(element, config) {
  const raw = element.getAttribute("data-moo-chart-data");
  let attributeData = null;
  if (raw !== null && raw.trim() !== "") {
    try {
      attributeData = JSON.parse(raw);
    } catch (error) {
      throw new SyntaxError(
        `MooChart could not parse data-moo-chart-data as JSON: ${error.message}`
      );
    }
  }
  if (!attributeData && !config.data) {
    attributeData = { labels: [], datasets: [] };
  }
  return config.data || attributeData;
}

function resolveChartType(element, config) {
  return (
    config.type ||
    element.getAttribute("data-moo-chart") ||
    "line"
  );
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

    const canvas = element.querySelector("canvas");
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

    const data = resolveChartData(element, this._config);
    const type = resolveChartType(element, this._config);
    this._type = type;

    const isDark = this._document?.documentElement?.dataset?.bsTheme === "dark";
    const colors = readThemeColors(this._document, this._window);
    this._theme = buildChartTheme(colors, isDark);

    const datasets = (data.datasets || []).map((dataset, index) =>
      themeDataset({ ...dataset }, index, type, this._theme)
    );

    this._chart = new Chart(canvas, {
      type,
      data: {
        labels: data.labels || [],
        datasets,
      },
      options: buildChartOptions(this._theme),
    });

    this._rethemeFrame = null;
    this._observer = null;
    const documentElement = this._document?.documentElement;
    if (documentElement && this._window?.MutationObserver) {
      this._observer = new this._window.MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.attributeName === "data-bs-theme") {
            this._scheduleRetheme();
          }
        });
      });
      this._observer.observe(documentElement, {
        attributes: true,
        attributeFilter: ["data-bs-theme"],
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
    const isDark = this._document?.documentElement?.dataset?.bsTheme === "dark";
    const colors = readThemeColors(this._document, this._window);
    this._theme = buildChartTheme(colors, isDark);
    applyThemeToChart(this._chart, this._theme);
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
    instances.delete(this._element);
  }
}
