import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class MooUiPopover extends Interaction {
    static selector = "[data-moo-ui-popover]";

    setup() {
        const container = this.el.closest(".o_moo_ui_scope") || false;
        this.popover = window.Popover?.getOrCreateInstance(this.el, { container });
        if (this.popover) {
            this.registerCleanup(() => this.popover.dispose());
        }
    }
}

registry.category("public.interactions").add("moo_ui.popover", MooUiPopover);
