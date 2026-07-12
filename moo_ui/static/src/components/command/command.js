import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class MooUiCommand extends Interaction {
    static selector = "[data-moo-ui-command]";
    dynamicContent = {
        "[data-moo-ui-command-input]": { "t-on-input": this.onInput },
    };

    setup() {
        this.input = this.el.querySelector("[data-moo-ui-command-input]");
        this.onNativeInput = (ev) => this.onInput(ev);
    }

    start() {
        if (this.input) {
            this.input.addEventListener("input", this.onNativeInput);
        }
    }

    destroy() {
        if (this.input) {
            this.input.removeEventListener("input", this.onNativeInput);
        }
    }

    onInput(ev) {
        const query = ev.currentTarget.value.trim().toLowerCase();
        for (const item of this.el.querySelectorAll("[data-moo-ui-command-item]")) {
            item.hidden = Boolean(query && !item.textContent.toLowerCase().includes(query));
        }
    }
}

registry.category("public.interactions").add("moo_ui.command", MooUiCommand);
