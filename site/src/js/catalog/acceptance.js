const states = new WeakMap();

function storageKey(portal) {
  return `moo-acceptance:${portal.dataset.mooAcceptanceKey || "default"}`;
}

function readState(view, key) {
  try {
    return JSON.parse(view.localStorage.getItem(key) || "{}");
  } catch (_) {
    return {};
  }
}

function writeState(view, key, state) {
  try {
    view.localStorage.setItem(key, JSON.stringify(state));
  } catch (_) {
    /* localStorage is best-effort for this manual review helper. */
  }
}

export function initAcceptancePortal(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const portals = Array.from(root.querySelectorAll("[data-moo-acceptance-portal]"));
  const listeners = [];
  const listen = (target, type, handler) => {
    target?.addEventListener(type, handler);
    if (target) {
      listeners.push({ target, type, handler });
    }
  };

  portals.forEach((portal) => {
    const frame = portal.querySelector("[data-moo-acceptance-frame]");
    const title = portal.querySelector("[data-moo-acceptance-viewer-title]");
    const link = portal.querySelector("[data-moo-acceptance-link]");
    const instruction = portal.querySelector("[data-moo-acceptance-instruction-output]");
    const count = portal.querySelector("[data-moo-acceptance-count]");
    const exportButton = portal.querySelector("[data-moo-acceptance-export]");
    const exportPanel = portal.querySelector("[data-moo-acceptance-export-panel]");
    const exportOutput = portal.querySelector("[data-moo-acceptance-export-output]");
    const exportStatus = portal.querySelector("[data-moo-acceptance-export-status]");
    const checks = Array.from(portal.querySelectorAll("[data-moo-acceptance-check]"));
    const targets = Array.from(portal.querySelectorAll("[data-moo-acceptance-target]"));
    const viewportControls = Array.from(
      portal.querySelectorAll("[data-moo-acceptance-viewport]")
    );
    const key = storageKey(portal);

    const updateCount = () => {
      if (!count) {
        return;
      }
      const checked = checks.filter((check) => check.checked).length;
      count.textContent = `${checked}/${checks.length}`;
    };

    const loadChecks = () => {
      const stored = readState(view, key);
      checks.forEach((check) => {
        check.checked = stored[check.id] === true;
      });
      updateCount();
    };

    const labelForCheck = (check) => {
      const item = check.closest("[data-moo-acceptance-item]");
      return [
        item?.dataset.mooAcceptanceComponent,
        item?.dataset.mooAcceptanceDevice,
        item?.dataset.mooAcceptanceKind,
      ].filter(Boolean).join(" / ");
    };

    const buildSummary = () => {
      const stored = readState(view, key);
      const components = [];
      const componentMap = new Map();

      checks.forEach((check) => {
        const item = check.closest("[data-moo-acceptance-item]");
        const component = item?.dataset.mooAcceptanceComponent || "Unknown";
        const device = item?.dataset.mooAcceptanceDevice || "Unknown";
        const kind = item?.dataset.mooAcceptanceKind || "Unknown";
        if (!componentMap.has(component)) {
          const entry = {
            label: component,
            devices: [],
            deviceMap: new Map(),
          };
          componentMap.set(component, entry);
          components.push(entry);
        }
        const componentEntry = componentMap.get(component);
        if (!componentEntry.deviceMap.has(device)) {
          const deviceEntry = {
            label: device,
            Visual: "Missing",
            Fixture: "Missing",
            Voice: "Missing",
            Keyboard: "Missing",
          };
          componentEntry.deviceMap.set(device, deviceEntry);
          componentEntry.devices.push(deviceEntry);
        }
        componentEntry.deviceMap.get(device)[kind] = stored[check.id] === true
          ? "Done"
          : "Missing";
      });
      portal.querySelectorAll('[data-moo-acceptance-state="N/A"]').forEach((item) => {
        const component = item.dataset.mooAcceptanceComponent || "Unknown";
        const device = item.dataset.mooAcceptanceDevice || "Unknown";
        const kind = item.dataset.mooAcceptanceKind || "Unknown";
        if (!componentMap.has(component)) {
          const entry = {
            label: component,
            devices: [],
            deviceMap: new Map(),
          };
          componentMap.set(component, entry);
          components.push(entry);
        }
        const componentEntry = componentMap.get(component);
        if (!componentEntry.deviceMap.has(device)) {
          const deviceEntry = {
            label: device,
            Visual: "Missing",
            Fixture: "Missing",
            Voice: "Missing",
            Keyboard: "Missing",
          };
          componentEntry.deviceMap.set(device, deviceEntry);
          componentEntry.devices.push(deviceEntry);
        }
        componentEntry.deviceMap.get(device)[kind] = "N/A";
      });

      const checkedCount = checks.filter((check) => stored[check.id] === true).length;
      const lines = [
        "## Acceptance Portal Result",
        "",
        `Generated: ${new Date().toISOString()}`,
        `Result: ${checkedCount}/${checks.length}`,
        "",
      ];

      components.forEach((component) => {
        lines.push(`### ${component.label}`, "");
        lines.push("| Device | Visual | Fixture | Voice | Keyboard |");
        lines.push("| --- | --- | --- | --- | --- |");
        component.devices.forEach((device) => {
          lines.push(
            `| ${device.label} | ${device.Visual} | ${device.Fixture} | ${device.Voice} | ${device.Keyboard} |`
          );
        });
        lines.push("");
      });

      const unchecked = checks
        .filter((check) => stored[check.id] !== true)
        .map(labelForCheck);
      lines.push("## Unchecked", "");
      if (unchecked.length === 0) {
        lines.push("- none");
      } else {
        unchecked.forEach((label) => {
          lines.push(`- ${label}`);
        });
      }

      return `${lines.join("\n").trim()}\n`;
    };

    const exportSummary = async () => {
      const summary = buildSummary();
      if (exportPanel) {
        exportPanel.hidden = false;
      }
      if (exportOutput) {
        exportOutput.value = summary;
        exportOutput.focus();
        exportOutput.select();
      }

      let status = "Summary is ready.";
      try {
        await view.navigator.clipboard.writeText(summary);
        status = "Summary copied to clipboard.";
      } catch (_) {
        status = "Summary is ready. Select the text and copy it manually.";
      }

      if (exportStatus) {
        exportStatus.textContent = status;
      }
    };

    const selectTarget = (target) => {
      const nextUrl = target.dataset.mooAcceptanceTarget;
      if (!nextUrl) {
        return;
      }
      targets.forEach((candidate) => {
        candidate.setAttribute(
          "aria-current",
          candidate === target ? "true" : "false"
        );
      });
      if (frame) {
        frame.src = nextUrl;
      }
      if (title) {
        title.textContent = target.dataset.mooAcceptanceTitle || target.textContent.trim();
      }
      if (link) {
        link.href = nextUrl;
        link.textContent = nextUrl.replace(/^\.\.\//g, "");
      }
      if (instruction) {
        instruction.textContent = target.dataset.mooAcceptanceInstruction || "";
      }
    };

    const selectViewport = (control) => {
      const viewportName = control.dataset.mooAcceptanceViewportName || "desktop";
      const viewportWidth = control.dataset.mooAcceptanceViewportWidth || "100%";

      viewportControls.forEach((candidate) => {
        const isSelected = candidate === control;
        candidate.classList.toggle("active", isSelected);
        candidate.setAttribute("aria-pressed", String(isSelected));
      });
      portal.dataset.mooAcceptancePreview = viewportName;
      portal.style.setProperty("--moo-acceptance-frame-width", viewportWidth);
    };

    checks.forEach((check) => {
      listen(check, "change", () => {
        const next = { ...readState(view, key), [check.id]: check.checked };
        writeState(view, key, next);
        updateCount();
      });
    });

    targets.forEach((target) => {
      listen(target, "click", () => selectTarget(target));
    });

    viewportControls.forEach((control) => {
      listen(control, "click", () => selectViewport(control));
    });

    listen(exportButton, "click", exportSummary);

    listen(link, "click", (event) => {
      event.preventDefault();
      const active = targets.find(
        (target) => target.getAttribute("aria-current") === "true"
      );
      if (active) {
        selectTarget(active);
      }
    });

    if (targets[0]) {
      selectTarget(targets[0]);
    }
    if (viewportControls[0]) {
      selectViewport(viewportControls[0]);
    }
    loadChecks();
  });

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}
