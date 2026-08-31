(function () {
  "use strict";

  var SITE_ORIGIN = "https://ui.wpmoo.org";

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
    if (name === "external-link") {
      return '<svg data-icon="inline-end" data-lucide="external-link" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6m-11 5L21 3m-3 10v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';
    }

    return '<svg data-icon="inline-start" data-lucide="blocks" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 22V7a1 1 0 0 0-1-1H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5a1 1 0 0 0-1-1H2"/><rect width="8" height="8" x="14" y="2" rx="1"/></svg>';
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
