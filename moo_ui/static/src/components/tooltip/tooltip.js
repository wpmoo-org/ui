import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class MooUiTooltip extends Interaction {
    static selector = "[data-moo-ui-tooltip]";

    setup() {
        const container = this.el.closest(".o_moo_ui_scope") || false;
        this.tooltip = window.Tooltip?.getOrCreateInstance(this.el, { container });
        if (this.tooltip) {
            this.registerCleanup(() => this.tooltip.dispose());
        }
    }
}

registry.category("public.interactions").add("moo_ui.tooltip", MooUiTooltip);
