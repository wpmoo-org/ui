import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const DESKTOP_QUERY = "(min-width: 992px)";
const COMPACT_CLASS = "o_moo_ui_sidebar_layout_compact";
const GROUP_SELECTOR = "[data-moo-ui-sidebar-group]";
const GROUP_TRIGGER_SELECTOR = "[data-moo-ui-sidebar-group-trigger]";
const GROUP_CONTENT_SELECTOR = "[data-moo-ui-sidebar-group-content]";

export class MooUiSidebar extends Interaction {
    static selector = "[data-moo-ui-sidebar-layout]";

    dynamicContent = {
        "[data-moo-ui-sidebar-compact-toggle]": {
            "t-on-click": this.onCompactToggle,
        },
        [GROUP_TRIGGER_SELECTOR]: {
            "t-on-click": this.onGroupTrigger,
        },
        _document: {
            "t-on-click": this.onDocumentClick,
            "t-on-keydown": this.onDocumentKeydown,
        },
    };

    setup() {
        this.storageKey = this.el.dataset.mooUiSidebarStorageKey || "moo.ui.sidebar.compact";
        this.cookieKey = this.el.dataset.mooUiSidebarCookieKey || "moo_ui_sidebar_compact";
        this.desktopMedia = browser.matchMedia(DESKTOP_QUERY);
    }

    start() {
        this.applyCompactState(this.readCompactState());
        this.addListener(this.desktopMedia, "change", this.onViewportChange);
    }

    readCompactState() {
        const cookieValue = cookie.get(this.cookieKey);
        if (cookieValue === "1" || cookieValue === "0") {
            return cookieValue === "1";
        }
        const stored = browser.localStorage.getItem(this.storageKey);
        return stored === "1";
    }

    writeCompactState(compact) {
        browser.localStorage.setItem(this.storageKey, compact ? "1" : "0");
        cookie.set(this.cookieKey, compact ? "1" : "0");
    }

    applyCompactState(compact) {
        const active = this.desktopMedia.matches && compact;
        this.el.classList.toggle(COMPACT_CLASS, active);
        if (active) {
            this.closeFlyouts();
        } else {
            this.openActiveGroups();
        }
        this.el.querySelectorAll("[data-moo-ui-sidebar-compact-toggle]").forEach((button) => {
            const label = active ? "Expand sidebar" : "Collapse sidebar";
            button.setAttribute("aria-label", label);
            button.setAttribute("aria-pressed", active ? "true" : "false");
            button.setAttribute("title", label);
        });
    }

    onCompactToggle(ev) {
        if (!this.desktopMedia.matches) {
            return;
        }
        ev.preventDefault();
        const compact = !this.el.classList.contains(COMPACT_CLASS);
        this.applyCompactState(compact);
        this.writeCompactState(compact);
    }

    onGroupTrigger(ev) {
        const button = ev.currentTarget;
        if (!this.isCompactDesktop() || !this.el.contains(button)) {
            return;
        }
        const content = this.getGroupContent(button);
        if (!content) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        const open = !content.classList.contains("show");
        this.closeFlyouts(button);
        this.setGroupOpen(button, content, open);
    }

    onDocumentClick(ev) {
        if (!this.isCompactDesktop()) {
            return;
        }
        const target = ev.target;
        if (target.closest?.(GROUP_SELECTOR)) {
            return;
        }
        this.closeFlyouts();
    }

    onDocumentKeydown(ev) {
        if (ev.key === "Escape") {
            this.closeFlyouts();
        }
    }

    onViewportChange() {
        this.applyCompactState(this.readCompactState());
    }

    isCompactDesktop() {
        return this.desktopMedia.matches && this.el.classList.contains(COMPACT_CLASS);
    }

    openActiveGroups() {
        this.el.querySelectorAll(`${GROUP_SELECTOR}.active`).forEach((group) => {
            const button = group.querySelector(GROUP_TRIGGER_SELECTOR);
            const content = button ? this.getGroupContent(button) : null;
            if (button && content) {
                this.setGroupOpen(button, content, true);
            }
        });
    }

    getGroupContent(button) {
        const group = button.closest(GROUP_SELECTOR);
        const groupContent = group?.querySelector(GROUP_CONTENT_SELECTOR);
        if (groupContent) {
            return groupContent;
        }
        const selector = button.getAttribute("data-bs-target");
        if (!selector) {
            return null;
        }
        try {
            return this.el.querySelector(selector);
        } catch {
            return null;
        }
    }

    setGroupOpen(button, content, open) {
        button.classList.toggle("collapsed", !open);
        button.setAttribute("aria-expanded", open ? "true" : "false");
        content.classList.toggle("show", open);
        content.classList.remove("collapsing");
        content.style.height = "";
        if (open) {
            this.hideTooltip(button);
        } else {
            this.restoreTooltip(button);
        }
    }

    closeFlyouts(exceptButton) {
        this.el.querySelectorAll(GROUP_TRIGGER_SELECTOR).forEach((button) => {
            if (button === exceptButton) {
                return;
            }
            const content = this.getGroupContent(button);
            if (content) {
                this.setGroupOpen(button, content, false);
            }
        });
    }

    hideTooltip(button) {
        if (button.dataset.mooUiTooltipStored !== "1") {
            button.dataset.mooUiTooltipStored = "1";
            button.dataset.mooUiTooltipValue = button.getAttribute("data-tooltip") || "";
            button.dataset.mooUiTooltipDelay = button.getAttribute("data-tooltip-delay") || "";
            button.dataset.mooUiTooltipPosition = button.getAttribute("data-tooltip-position") || "";
        }
        button.removeAttribute("data-tooltip");
        button.removeAttribute("data-tooltip-delay");
        button.removeAttribute("data-tooltip-position");
        button.blur();
    }

    restoreTooltip(button) {
        if (button.dataset.mooUiTooltipStored !== "1") {
            return;
        }
        this.restoreOptionalAttribute(button, "data-tooltip", button.dataset.mooUiTooltipValue);
        this.restoreOptionalAttribute(button, "data-tooltip-delay", button.dataset.mooUiTooltipDelay);
        this.restoreOptionalAttribute(button, "data-tooltip-position", button.dataset.mooUiTooltipPosition);
        delete button.dataset.mooUiTooltipStored;
        delete button.dataset.mooUiTooltipValue;
        delete button.dataset.mooUiTooltipDelay;
        delete button.dataset.mooUiTooltipPosition;
    }

    restoreOptionalAttribute(button, attribute, value) {
        if (value) {
            button.setAttribute(attribute, value);
        }
    }
}

registry.category("public.interactions").add("moo_ui.sidebar", MooUiSidebar);
