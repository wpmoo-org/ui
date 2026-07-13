import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const DESKTOP_QUERY = "(min-width: 992px)";
const COMPACT_CLASS = "o_moo_ui_sidebar_layout_compact";

export class MooUiSidebar extends Interaction {
    static selector = "[data-moo-ui-sidebar-layout]";

    dynamicContent = {
        "[data-moo-ui-sidebar-compact-toggle]": {
            "t-on-click": this.onCompactToggle,
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
        return browser.localStorage.getItem(this.storageKey) === "1";
    }

    writeCompactState(compact) {
        browser.localStorage.setItem(this.storageKey, compact ? "1" : "0");
        cookie.set(this.cookieKey, compact ? "1" : "0");
    }

    applyCompactState(compact) {
        const active = this.desktopMedia.matches && compact;
        this.el.classList.toggle(COMPACT_CLASS, active);
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

    onViewportChange() {
        this.applyCompactState(this.readCompactState());
    }
}

registry.category("public.interactions").add("moo_ui.sidebar", MooUiSidebar);
