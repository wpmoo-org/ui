// Chart.js theming wrapper for dashboard examples. Reads Bootstrap's
// --bs-* custom properties and re-themes charts when the site's
// data-bs-theme attribute changes (light/dark toggle).
//
// Chart.js is loaded from CDN (jsdelivr) via a <script> tag -- it is a
// devDependency only, so it must not be bundled into the published
// package. The dynamic-import("chart.js/auto") approach does not work
// in the browser because bare module specifiers cannot be resolved
// without an import map.

const states = new WeakMap();
const CHART_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js";
const CHART_SRI = "sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ";

// Bootstrap semantic color tokens that Chart.js should read.
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

function readThemeColors(root) {
  const view = root.defaultView || root.ownerDocument?.defaultView;
  if (!view) return null;
  const styles = view.getComputedStyle(root.documentElement || root.ownerDocument?.documentElement);
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

// Apply theme colors to an existing Chart.js instance.
function applyThemeToChart(chart, theme) {
  if (!chart) return;

  // Update dataset colors for line/bar charts.
  chart.data.datasets.forEach((dataset, index) => {
    const colorKeys = ["primary", "success", "info", "warning", "danger"];
    const colorKey = colorKeys[index % colorKeys.length];
    const color = theme[colorKey];
    const mutedColor = `color-mix(in srgb, ${color} 92%, ${theme.color})`;
    const pointColor = color;
    const datasetType = dataset.type || chart.config.type;

    if (datasetType === "line") {
      dataset.borderColor = mutedColor;
      dataset.backgroundColor = `color-mix(in srgb, ${color} 22%, transparent)`;
      dataset.pointBackgroundColor = pointColor;
      dataset.pointBorderColor = theme.borderColor;
      dataset.pointHoverBackgroundColor = pointColor;
      dataset.pointHoverBorderColor = theme.color;
    } else if (datasetType === "bar") {
      dataset.backgroundColor = `color-mix(in srgb, ${color} 78%, transparent)`;
      dataset.borderColor = mutedColor;
      dataset.hoverBackgroundColor = color;
    }
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

// Load Chart.js from CDN. Returns a promise that resolves with the
// Chart constructor (window.Chart) once the script is ready.
function loadChartJs() {
  return new Promise((resolve, reject) => {
    if (window.Chart) {
      resolve(window.Chart);
      return;
    }
    const existing = document.querySelector(`script[src="${CHART_CDN}"]`);
    if (existing) {
      // Already loading -- wait for it.
      existing.addEventListener("load", () => resolve(window.Chart));
      existing.addEventListener("error", reject);
      return;
    }
    const script = document.createElement("script");
    script.src = CHART_CDN;
    script.integrity = CHART_SRI;
    script.crossOrigin = "anonymous";
    script.onload = () => resolve(window.Chart);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

// Initialize all charts on the page.
export function initExamplesChart(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const chartContainers = root.querySelectorAll("[data-moo-chart]");
  if (chartContainers.length === 0) {
    return () => {};
  }

  const documentElement = root.documentElement || root.ownerDocument?.documentElement;
  const pending = {
    disposed: false,
    complete: null,
  };

  const release = () => {
    pending.disposed = true;
    if (pending.complete) pending.complete();
  };

  states.set(root, release);

  loadChartJs().then((Chart) => {
    if (pending.disposed) return;

    const charts = [];
    const colors = readThemeColors(root);
    const theme = buildChartTheme(
      colors,
      documentElement.dataset.bsTheme === "dark",
    );

    chartContainers.forEach((container) => {
      const canvas = container.querySelector("canvas");
      if (!canvas) return;

      const chartType = container.dataset.mooChart || "line";
      const chartData = JSON.parse(container.dataset.mooChartData || "null");

      if (!chartData) return;

      // Build dataset configs.
      const datasets = chartData.datasets.map((dataset, index) => {
        const colorKeys = ["primary", "success", "info", "warning", "danger"];
        const colorKey = colorKeys[index % colorKeys.length];
        const color = theme[colorKey];
        // Keep both themes close to their semantic token so the hue remains
        // consistent when the user toggles the catalog theme.
        const mutedColor = `color-mix(in srgb, ${color} 92%, ${theme.color})`;
        const pointColor = color;

        if (chartType === "line") {
          return {
            ...dataset,
            borderColor: mutedColor,
            backgroundColor: `color-mix(in srgb, ${color} 22%, transparent)`,
            pointBackgroundColor: pointColor,
            pointBorderColor: theme.borderColor,
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 7,
            pointHoverBackgroundColor: pointColor,
            pointHoverBorderColor: theme.color,
            pointHoverBorderWidth: 3,
            tension: 0.3,
            fill: true,
          };
        }
        if (chartType === "bar") {
          return {
            ...dataset,
            backgroundColor: `color-mix(in srgb, ${color} 78%, transparent)`,
            borderColor: mutedColor,
            borderWidth: 1,
            hoverBackgroundColor: color,
            hoverBorderColor: color,
            borderRadius: 4,
          };
        }
        return dataset;
      });

      const chart = new Chart(canvas, {
        type: chartType,
        data: {
          labels: chartData.labels,
          datasets,
        },
        options: {
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
        },
      });

      charts.push(chart);
    });

    if (pending.disposed) {
      charts.forEach((chart) => chart.destroy());
      return;
    }

    // Watch for theme changes and re-theme all charts.
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "data-bs-theme") {
          const newColors = readThemeColors(root);
          const newTheme = buildChartTheme(
            newColors,
            documentElement.dataset.bsTheme === "dark",
          );
          charts.forEach((chart) => applyThemeToChart(chart, newTheme));
        }
      });
    });

    observer.observe(documentElement, {
      attributes: true,
      attributeFilter: ["data-bs-theme"],
    });

    const dispose = () => {
      observer.disconnect();
      charts.forEach((chart) => chart.destroy());
      if (states.get(root) === release) states.delete(root);
    };

    pending.complete = dispose;
    if (pending.disposed) dispose();
  }).catch((err) => {
    // Chart.js failed to load (CDN unreachable, network error, etc.).
    // The page degrades gracefully — stat cards still render, only the
    // chart containers remain empty. Log for debugging but don't throw.
    console.warn("[moo-chart] Chart.js failed to load:", err.message || err);
    if (states.get(root) === release) states.delete(root);
  });

  return release;
}
