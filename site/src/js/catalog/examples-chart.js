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
const CHART_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js";

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
function buildChartTheme(colors) {
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
    primary: colors["--bs-primary"],
    success: colors["--bs-success"],
    info: colors["--bs-info"],
    warning: colors["--bs-warning"],
    danger: colors["--bs-danger"],
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
    const mutedColor = `color-mix(in srgb, ${color} 70%, ${theme.secondaryText})`;
    const isDark = chart.canvas.ownerDocument.documentElement.dataset.bsTheme === "dark";
    const pointColor = isDark
      ? `color-mix(in srgb, ${color} 65%, #ffffff)`
      : color;

    if (dataset.type === "line" || !dataset.type) {
      dataset.borderColor = mutedColor;
      dataset.backgroundColor = `color-mix(in srgb, ${color} 15%, transparent)`;
      dataset.pointBackgroundColor = pointColor;
      dataset.pointBorderColor = theme.borderColor;
      dataset.pointHoverBackgroundColor = pointColor;
      dataset.pointHoverBorderColor = theme.color;
    } else if (dataset.type === "bar") {
      dataset.backgroundColor = `color-mix(in srgb, ${color} 55%, transparent)`;
      dataset.borderColor = mutedColor;
      dataset.hoverBackgroundColor = color;
    }
  });

  // Update scale colors.
  if (chart.options.scales) {
    Object.values(chart.options.scales).forEach((scale) => {
      if (scale.grid) {
        scale.grid.color = theme.gridColor + "59"; // 35% opacity
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

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const documentElement = root.documentElement || root.ownerDocument?.documentElement;

  loadChartJs().then((Chart) => {
    const charts = [];
    const colors = readThemeColors(root);
    const theme = buildChartTheme(colors);

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
        // Mute the dataset color by mixing it with secondary-color (text).
        // This keeps the hue recognizable but reduces saturation so the
        // chart feels calmer and doesn't compete with the UI chrome.
        const mutedColor = `color-mix(in srgb, ${color} 70%, ${theme.secondaryText})`;
        // Point fill: in light mode use raw primary (already vibrant against
        // light bg). In dark mode, mix with white so points stay brighter
        // than the muted line — mirroring the light-mode relationship.
        const isDark = documentElement.dataset.bsTheme === "dark";
        const pointColor = isDark
          ? `color-mix(in srgb, ${color} 65%, #ffffff)`
          : color;

        if (chartType === "line") {
          return {
            ...dataset,
            borderColor: mutedColor,
            backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)`,
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
            backgroundColor: `color-mix(in srgb, ${color} 55%, transparent)`,
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
                color: theme.gridColor + "59", // 35% opacity
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
                color: theme.gridColor + "59", // 35% opacity
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

    // Watch for theme changes and re-theme all charts.
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "data-bs-theme") {
          const newColors = readThemeColors(root);
          const newTheme = buildChartTheme(newColors);
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
      states.delete(root);
    };

    states.set(root, dispose);
  }).catch((err) => {
    console.error("Failed to load Chart.js:", err);
  });

  return () => {
    const state = states.get(root);
    if (state) state();
  };
}
