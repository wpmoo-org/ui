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
