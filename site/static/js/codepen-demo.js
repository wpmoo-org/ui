(function () {
  "use strict";

  var SITE_ORIGIN = "https://ui.wpmoo.org";
  var THEME_STORAGE_KEY = "moo:theme";

  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }

    callback();
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalizeComponent(component) {
    var slug = String(component && component.slug ? component.slug : "").trim();
    var label = String(component && component.label ? component.label : slug).trim();
    var href = String(component && component.href ? component.href : "").trim();
    var previewSrc = String(component && component.previewSrc ? component.previewSrc : "").trim();

    if (!href && slug) {
      href = SITE_ORIGIN + "/components/" + slug + "/";
    }

    if (!previewSrc && slug) {
      previewSrc = SITE_ORIGIN + "/assets/images/components/" + slug + ".webp";
    }

    return {
      slug: slug,
      label: label || "Component",
      description: String(component && component.description ? component.description : "").trim(),
      href: href || SITE_ORIGIN + "/components/",
      previewSrc: previewSrc
    };
  }

  function normalizeConfig(config) {
    var source = config || window.MooCodePen || {};
    var components = Array.isArray(source.components) ? source.components : [];

    return {
      kind: source.kind || "",
      components: components.map(normalizeComponent).filter(function (component) {
        return component.slug || component.label;
      })
    };
  }

  function iconSvg(name) {
    if (name === "github") {
      return '<svg data-icon="inline-start" viewBox="0 0 438.549 438.549" fill="currentColor" aria-hidden="true"><path d="M409.132 114.573c-19.608-33.596-46.205-60.194-79.798-79.8-33.598-19.607-70.277-29.408-110.063-29.408-39.781 0-76.472 9.804-110.063 29.408-33.596 19.605-60.192 46.204-79.8 79.8C9.803 148.168 0 184.854 0 224.63c0 47.78 13.94 90.745 41.827 128.906 27.884 38.164 63.906 64.572 108.063 79.227 5.14.954 8.945.283 11.419-1.996 2.475-2.282 3.711-5.14 3.711-8.562 0-.571-.049-5.708-.144-15.417a2549.81 2549.81 0 01-.144-25.406l-6.567 1.136c-4.187.767-9.469 1.092-15.846 1-6.374-.089-12.991-.757-19.842-1.999-6.854-1.231-13.229-4.086-19.13-8.559-5.898-4.473-10.085-10.328-12.56-17.556l-2.855-6.57c-1.903-4.374-4.899-9.233-8.992-14.559-4.093-5.331-8.232-8.945-12.419-10.848l-1.999-1.431c-1.332-.951-2.568-2.098-3.711-3.429-1.142-1.331-1.997-2.663-2.568-3.997-.572-1.335-.098-2.43 1.427-3.289 1.525-.859 4.281-1.276 8.28-1.276l5.708.853c3.807.763 8.516 3.042 14.133 6.851 5.614 3.806 10.229 8.754 13.846 14.842 4.38 7.806 9.657 13.754 15.846 17.847 6.184 4.093 12.419 6.136 18.699 6.136 6.28 0 11.704-.476 16.274-1.423 4.565-.952 8.848-2.383 12.847-4.285 1.713-12.758 6.377-22.559 13.988-29.41-10.848-1.14-20.601-2.857-29.264-5.14-8.658-2.286-17.605-5.996-26.835-11.14-9.235-5.137-16.896-11.516-22.985-19.126-6.09-7.614-11.088-17.61-14.987-29.979-3.901-12.374-5.852-26.648-5.852-42.826 0-23.035 7.52-42.637 22.557-58.817-7.044-17.318-6.379-36.732 1.997-58.24 5.52-1.715 13.706-.428 24.554 3.853 10.85 4.283 18.794 7.952 23.84 10.994 5.046 3.041 9.089 5.618 12.135 7.708 17.705-4.947 35.976-7.421 54.818-7.421s37.117 2.474 54.823 7.421l10.849-6.849c7.419-4.57 16.18-8.758 26.262-12.565 10.088-3.805 17.802-4.853 23.134-3.138 8.562 21.509 9.325 40.922 2.279 58.24 15.036 16.18 22.559 35.787 22.559 58.817 0 16.178-1.958 30.497-5.853 42.966-3.9 12.471-8.941 22.457-15.125 29.979-6.191 7.521-13.901 13.85-23.131 18.986-9.232 5.14-18.182 8.85-26.84 11.136-8.662 2.286-18.415 4.004-29.263 5.146 9.894 8.562 14.842 22.077 14.842 40.539v60.237c0 3.422 1.19 6.279 3.572 8.562 2.379 2.279 6.136 2.95 11.276 1.995 44.163-14.653 80.185-41.062 108.068-79.226 27.88-38.161 41.825-81.126 41.825-128.906-.01-39.771-9.818-76.454-29.414-110.049z"/></svg>';
    }

    if (name === "moon") {
      return '<svg data-icon="inline-start" data-lucide="moon-star" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9"/><path d="M19 3v4"/><path d="M21 5h-4"/></svg>';
    }

    if (name === "sun") {
      return '<svg data-icon="inline-start" data-lucide="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>';
    }

    if (name === "external-link") {
      return '<svg data-icon="inline-end" data-lucide="external-link" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6m-11 5L21 3m-3 10v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';
    }

    return '<svg data-icon="inline-start" data-lucide="blocks" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 22V7a1 1 0 0 0-1-1H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5a1 1 0 0 0-1-1H2"/><rect width="8" height="8" x="14" y="2" rx="1"/></svg>';
  }

  function storageGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (_) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (_) {
      /* Storage is best-effort inside embedded demo contexts. */
    }
  }

  function currentTheme() {
    var theme = document.documentElement.getAttribute("data-bs-theme");
    return theme === "dark" ? "dark" : "light";
  }

  function syncThemeToggle() {
    var theme = currentTheme();
    document.querySelectorAll("[data-moo-codepen-theme-toggle]").forEach(function (toggle) {
      toggle.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
      toggle.querySelectorAll("[data-moo-codepen-theme-icon]").forEach(function (icon) {
        icon.hidden = icon.dataset.mooCodepenThemeIcon !== theme;
      });
    });
  }

  function setTheme(theme) {
    var normalized = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-bs-theme", normalized);
    storageSet(THEME_STORAGE_KEY, normalized);
    syncThemeToggle();
  }

  function createActions() {
    var actions;
    var themeToggle;
    var storedTheme;

    if (document.querySelector(".moo-codepen-actions")) {
      syncThemeToggle();
      return;
    }

    actions = document.createElement("div");
    actions.className = "moo-codepen-actions";
    actions.setAttribute("role", "group");
    actions.setAttribute("aria-label", "Demo controls");
    actions.innerHTML = [
      '<button class="btn btn-ghost btn-icon moo-codepen-actions__theme-toggle" type="button" data-moo-codepen-theme-toggle>',
      '<span data-moo-codepen-theme-icon="light">' + iconSvg("sun") + "</span>",
      '<span data-moo-codepen-theme-icon="dark">' + iconSvg("moon") + "</span>",
      "</button>",
      '<a class="btn btn-primary moo-codepen-actions__github-link" role="button" href="https://github.com/wpmoo-org/ui" target="_blank" rel="noopener noreferrer" aria-label="Open Moo UI on GitHub">',
      iconSvg("github"),
      '<span class="moo-codepen-actions__github-label">wpmoo-org/ui</span>',
      "</a>"
    ].join("\n");

    document.body.appendChild(actions);
    themeToggle = actions.querySelector("[data-moo-codepen-theme-toggle]");
    if (themeToggle) {
      themeToggle.addEventListener("click", function () {
        setTheme(currentTheme() === "dark" ? "light" : "dark");
      });
    }

    storedTheme = storageGet(THEME_STORAGE_KEY);
    if (storedTheme === "dark" || storedTheme === "light") {
      setTheme(storedTheme);
      return;
    }

    syncThemeToggle();
  }

  function createSignature() {
    if (document.querySelector(".moo-codepen-signature")) {
      return;
    }

    var signature = document.createElement("aside");
    signature.className = "moo-codepen-signature";
    signature.setAttribute("aria-label", "Moo UI");
    signature.innerHTML = [
      '<div class="moo-codepen-signature__lockup">',
      '  <span class="moo-codepen-signature__mark">' + iconSvg("blocks") + "</span>",
      '  <span class="moo-codepen-signature__text">',
      '    <span class="moo-codepen-signature__brand">Moo UI</span>',
      '    <span class="moo-codepen-signature__tagline">Bootstrap markup. shadcn feel.</span>',
      "  </span>",
      "</div>",
      '<p class="moo-codepen-signature__note">',
      '  <span class="moo-codepen-signature__note-line">Moo UI is not another shadcn clone.</span>',
      '  <span class="moo-codepen-signature__note-line">It brings the shadcn/ui feel to</span>',
      '  <span class="moo-codepen-signature__note-line">Bootstrap-native HTML.</span>',
      '  <a class="moo-codepen-signature__learn-more" href="' + SITE_ORIGIN + '/" target="_blank" rel="noopener noreferrer">Learn more ' + iconSvg("external-link") + "</a>",
      "</p>"
    ].join("\n");

    document.body.appendChild(signature);
  }

  function componentPopoverContent(component) {
    var href = escapeHtml(component.href);
    var label = escapeHtml(component.label);
    var description = escapeHtml(component.description);
    var preview = component.previewSrc
      ? '<a href="' + href + '" target="_blank" rel="noopener noreferrer" class="moo-examples-footer__preview"><img src="' + escapeHtml(component.previewSrc) + '" alt="" class="moo-catalog__showcase-image w-100" loading="lazy"></a>'
      : "";

    return [
      preview,
      '<strong class="d-block mb-1">' + label + "</strong>",
      description,
      '<a href="' + href + '" target="_blank" rel="noopener noreferrer" class="d-block mt-1">Learn more</a>'
    ].filter(Boolean).join("\n");
  }

  function createComponentTrigger(component) {
    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "btn btn-outline-secondary moo-examples-footer__component-trigger";
    trigger.textContent = component.label;
    trigger.setAttribute("data-bs-toggle", "popover");
    trigger.setAttribute("data-bs-trigger", "focus");
    trigger.setAttribute("data-bs-container", "body");
    trigger.setAttribute("data-bs-placement", "top");
    trigger.setAttribute("data-bs-html", "true");
    trigger.setAttribute("data-bs-content", componentPopoverContent(component));
    return trigger;
  }

  function appendComponentList(parent, components) {
    components.forEach(function (component, index) {
      if (index > 0 && components.length === 2) {
        parent.appendChild(document.createTextNode(" and "));
      } else if (index > 0 && index === components.length - 1) {
        parent.appendChild(document.createTextNode(", and "));
      } else if (index > 0) {
        parent.appendChild(document.createTextNode(", "));
      }

      parent.appendChild(createComponentTrigger(component));
    });
  }

  function createFooter(components) {
    if (!components.length || document.querySelector(".moo-codepen-footer")) {
      return;
    }

    var footer = document.createElement("footer");
    var text = document.createElement("p");
    footer.className = "moo-codepen-footer text-body-secondary small";
    text.className = "mb-0";
    text.appendChild(document.createTextNode("This demo is composed from the "));
    appendComponentList(text, components);
    text.appendChild(document.createTextNode(components.length === 1 ? " component." : " components."));
    footer.appendChild(text);
    document.body.appendChild(footer);
  }

  function initializePopovers(root) {
    var Popover = window.bootstrap && window.bootstrap.Popover;
    if (!Popover) {
      return;
    }

    root.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (element) {
      Popover.getOrCreateInstance(element);
    });
  }

  function initializeToasts(root) {
    var Toast = window.bootstrap && window.bootstrap.Toast;
    if (
      !Toast ||
      !root.body ||
      root.body.dataset.mooCodepenToastsReady === "true"
    ) {
      return;
    }

    root.body.dataset.mooCodepenToastsReady = "true";

    var toastSequence = 0;
    var toastStackVisibleLimit = 3;
    var sharedToastStacks = new Map();

    function isStackContainer(element) {
      return element instanceof window.HTMLElement &&
        element.matches('.toast-container--stacked[data-toast-stack="deck"]');
    }

    function getStackContainer(toast) {
      var container = toast && toast.closest
        ? toast.closest('.toast-container--stacked[data-toast-stack="deck"]')
        : null;
      return isStackContainer(container) ? container : null;
    }

    function getSharedToastStack(sourceContainer) {
      if (!isStackContainer(sourceContainer)) {
        return sourceContainer;
      }

      var key = sourceContainer.dataset.toastStack || "deck";
      var existing = sharedToastStacks.get(key);
      if (existing && existing.isConnected) {
        return existing;
      }

      var container = root.createElement("div");
      container.className = sourceContainer.className;
      container.dataset.toastStack = key;
      container.dataset.mooCodepenToastStack = "shared";
      root.body.appendChild(container);
      sharedToastStacks.set(key, container);
      return container;
    }

    function readNumber(value, fallback) {
      var number = Number.parseFloat(value);
      return Number.isFinite(number) ? number : fallback;
    }

    function readPixels(value, computed) {
      var number = readNumber(value, 0);
      var normalized = value.trim();
      if (normalized.endsWith("rem")) {
        return number * readNumber(window.getComputedStyle(root.documentElement).fontSize, 16);
      }
      if (normalized.endsWith("em")) {
        return number * readNumber(computed.fontSize, 16);
      }
      return number;
    }

    function clearToastStackState(toast) {
      toast.removeAttribute("data-toast-stack-index");
      toast.removeAttribute("data-toast-stack-limited");
      toast.removeAttribute("data-toast-stack-entering");
      toast.removeAttribute("inert");
      toast.style.removeProperty("--moo-toast-stack-collapsed-y");
      toast.style.removeProperty("--moo-toast-stack-expanded-y");
      toast.style.removeProperty("--moo-toast-stack-scale");
      toast.style.removeProperty("--moo-toast-stack-z");
    }

    function updateToastStack(container, pendingToast) {
      if (!isStackContainer(container)) {
        return;
      }

      var toasts = Array.from(container.children).filter(function (child) {
        return child instanceof window.HTMLElement &&
          child.classList.contains("toast") &&
          (
            child.classList.contains("show") ||
            child.classList.contains("showing") ||
            child === pendingToast
          );
      });

      if (toasts.length === 0) {
        container.removeAttribute("data-toast-stack-hovering");
        container.removeAttribute("data-toast-stack-active");
        return;
      }

      container.setAttribute("data-toast-stack-active", "");

      var spacingSource = toasts[0] || container;
      var computed = window.getComputedStyle(spacingSource);
      var gap = readPixels(computed.getPropertyValue("--moo-toast-stack-gap"), computed);
      var peek = readPixels(computed.getPropertyValue("--moo-toast-stack-peek"), computed);
      var scaleStep = readNumber(
        computed.getPropertyValue("--moo-toast-stack-scale-step"),
        0.1
      );
      var minScale = readNumber(
        computed.getPropertyValue("--moo-toast-stack-min-scale"),
        0.5
      );

      toasts.sort(function (left, right) {
        var leftSequence = Number.parseInt(left.dataset.toastStackSequence || "0", 10);
        var rightSequence = Number.parseInt(right.dataset.toastStackSequence || "0", 10);
        return (Number.isFinite(rightSequence) ? rightSequence : 0) -
          (Number.isFinite(leftSequence) ? leftSequence : 0);
      });

      var stackHeight = (toasts[0] && (
        toasts[0].offsetHeight ||
        toasts[0].getBoundingClientRect().height
      )) || 0;
      var expandedOffset = 0;

      toasts.forEach(function (toast, index) {
        var height = toast.offsetHeight || toast.getBoundingClientRect().height;
        var scale = Math.max(minScale, 1 - index * scaleStep);
        var collapsedOffset = -(index * peek + (1 - scale) * stackHeight);
        var limited = index >= toastStackVisibleLimit;

        toast.dataset.toastStackIndex = String(index);
        if (limited) {
          toast.setAttribute("data-toast-stack-limited", "");
          toast.setAttribute("inert", "");
        } else {
          toast.removeAttribute("data-toast-stack-limited");
          toast.removeAttribute("inert");
        }

        toast.style.setProperty("--moo-toast-stack-collapsed-y", collapsedOffset + "px");
        toast.style.setProperty("--moo-toast-stack-expanded-y", expandedOffset + "px");
        toast.style.setProperty("--moo-toast-stack-scale", String(scale));
        toast.style.setProperty("--moo-toast-stack-z", String(1000 - index));
        expandedOffset -= height + gap;
      });
    }

    function isPointerInsideToastStack(container, event) {
      if (!isStackContainer(container)) {
        return false;
      }

      return Array.from(container.children).some(function (child) {
        var rect;
        if (
          !(child instanceof window.HTMLElement) ||
          !child.classList.contains("toast") ||
          child.hasAttribute("data-toast-stack-limited")
        ) {
          return false;
        }

        rect = child.getBoundingClientRect();
        return event.clientX >= rect.left &&
          event.clientX <= rect.right &&
          event.clientY >= rect.top &&
          event.clientY <= rect.bottom;
      });
    }

    function markToastStackHovering(container) {
      if (!isStackContainer(container)) {
        return;
      }

      container.setAttribute("data-toast-stack-hovering", "");
      updateToastStack(container);
    }

    function releaseToastStackHovering(container) {
      if (!isStackContainer(container)) {
        return;
      }

      container.removeAttribute("data-toast-stack-hovering");
      updateToastStack(container);
    }

    function hideToastFromDismissControl(dismiss) {
      var target;
      var instance;
      if (
        !(dismiss instanceof window.HTMLElement) ||
        dismiss.matches(":disabled, [aria-disabled='true']")
      ) {
        return;
      }

      target = dismiss.closest(".toast");
      if (target) {
        instance = Toast.getOrCreateInstance(target);
        instance.hide();
      }
    }

    root.addEventListener("pointerover", function (event) {
      var toast = event.target instanceof window.Element
        ? event.target.closest(".toast")
        : null;
      var container = getStackContainer(toast);
      if (container && toast && toast.parentElement === container) {
        markToastStackHovering(container);
      }
    }, true);

    root.addEventListener("pointermove", function (event) {
      root
        .querySelectorAll(
          '.toast-container--stacked[data-toast-stack="deck"][data-toast-stack-hovering]'
        )
        .forEach(function (container) {
          if (
            isStackContainer(container) &&
            !isPointerInsideToastStack(container, event)
          ) {
            releaseToastStackHovering(container);
          }
        });
    }, true);

    root.addEventListener("click", function (event) {
      var trigger = event.target instanceof window.Element
        ? event.target.closest("[data-toast-target]")
        : null;
      var selector = trigger && trigger.dataset.toastTarget || "";
      var id = selector.charAt(0) === "#" ? selector.slice(1) : selector;
      var target = id ? root.getElementById(id) : null;
      var template;
      var sourceContainer;
      var fragment;
      var toast;
      var container;
      var sequence;
      var instance;

      if (!trigger) {
        return;
      }

      if (
        target instanceof window.HTMLTemplateElement &&
        target.dataset.toastTemplate === "toast"
      ) {
        event.preventDefault();
        template = target;
        sourceContainer = template.parentElement;
        fragment = template.content.cloneNode(true);
        toast = fragment.firstElementChild;
        if (
          !(sourceContainer instanceof window.HTMLElement) ||
          !(toast instanceof window.HTMLElement) ||
          !toast.classList.contains("toast")
        ) {
          return;
        }

        container = getSharedToastStack(sourceContainer);
        sequence = ++toastSequence;
        toast.id = template.id + "-" + sequence;
        toast.setAttribute("data-toast-generated", "true");
        toast.setAttribute("data-toast-stack-sequence", String(sequence));
        toast.setAttribute("data-toast-stack-entering", "");
        container.prepend(toast);
        updateToastStack(container, toast);
        instance = Toast.getOrCreateInstance(toast, { animation: false });
        instance.show();
        window.setTimeout(function () {
          window.requestAnimationFrame(function () {
            if (toast.isConnected) {
              toast.removeAttribute("data-toast-stack-entering");
            }
          });
        }, 80);
      } else if (target instanceof window.HTMLElement) {
        event.preventDefault();
        instance = Toast.getOrCreateInstance(target);
        instance.show();
      }
    });

    root.addEventListener("show.bs.toast", function (event) {
      var toast = event.target;
      var container = getStackContainer(toast);
      if (container) {
        updateToastStack(container, toast);
      }
    }, true);

    root.addEventListener("shown.bs.toast", function (event) {
      var toast = event.target;
      var container = getStackContainer(toast);
      if (container) {
        updateToastStack(container, toast);
      }
    }, true);

    root.addEventListener("hidden.bs.toast", function (event) {
      var toast = event.target;
      var container;
      var instance;
      if (!(toast instanceof window.HTMLElement) || !toast.classList.contains("toast")) {
        return;
      }

      container = getStackContainer(toast);
      clearToastStackState(toast);
      if (toast.dataset.toastGenerated === "true") {
        instance = Toast.getInstance(toast);
        if (instance) {
          instance.dispose();
        }
        toast.remove();
      }
      if (container) {
        updateToastStack(container);
      }
    }, true);

    root.addEventListener("keydown", function (event) {
      var dismiss = event.target instanceof window.Element
        ? event.target.closest('[data-bs-dismiss="toast"]')
        : null;
      if (
        !dismiss ||
        !event.ctrlKey ||
        !event.altKey ||
        (event.key !== " " && event.key !== "Spacebar")
      ) {
        return;
      }

      event.preventDefault();
      hideToastFromDismissControl(dismiss);
    });
  }

  function render(config) {
    var normalized = normalizeConfig(config);

    if (normalized.kind !== "component" && normalized.kind !== "example") {
      return;
    }

    document.body.classList.add("moo-codepen-demo");
    createActions();
    createSignature();

    if (normalized.kind === "component") {
      document.body.classList.add("moo-codepen-component-demo", "moo-codepen-has-branding");
      createFooter(normalized.components);
    } else {
      document.body.classList.add("moo-codepen-example-demo");
    }

    initializePopovers(document);
    initializeToasts(document);
  }

  window.MooCodePenDemo = {
    init: function (config) {
      onReady(function () {
        render(config);
      });
    }
  };

  onReady(function () {
    if (window.MooCodePen) {
      render(window.MooCodePen);
    }
  });
})();
