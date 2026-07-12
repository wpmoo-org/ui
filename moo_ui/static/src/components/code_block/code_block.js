import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class MooUiCodeBlock extends Interaction {
    static selector = "[data-moo-ui-code-block]";

    setup() {
        this.code = this.el.querySelector("[data-moo-ui-code-block-code]");
        this.lines = this.el.querySelector("[data-moo-ui-code-block-lines]");
        this.copyButton = this.el.querySelector("[data-moo-ui-code-block-copy]");
        this.onCopyClick = (ev) => this.onCopy(ev);
    }

    start() {
        this.el.dataset.mooUiCodeBlockReady = "1";
        if (this.code) {
            this.rawText = this.code.textContent;
            this.syncLineNumbers();
            this.highlightCode();
            this.observer = new MutationObserver(() => this.onCodeMutation());
            this.observer.observe(this.code, { childList: true, characterData: true, subtree: true });
        }
        if (this.copyButton) {
            this.copyButton.addEventListener("click", this.onCopyClick);
        }
    }

    destroy() {
        this.observer?.disconnect();
        if (this.copyButton) {
            this.copyButton.removeEventListener("click", this.onCopyClick);
        }
    }

    syncLineNumbers() {
        if (!this.lines) {
            return;
        }
        const count = Math.max(1, this.rawText.split("\n").length);
        this.lines.textContent = Array.from({ length: count }, (_, index) => index + 1).join("\n");
    }

    highlightCode() {
        window.Prism?.highlightElement(this.code);
    }

    onCodeMutation() {
        const text = this.code.textContent;
        if (text === this.rawText) {
            return;
        }
        this.rawText = text;
        this.syncLineNumbers();
        this.highlightCode();
    }

    copyText(text) {
        if (navigator.clipboard?.writeText) {
            return navigator.clipboard.writeText(text);
        }

        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();

        return Promise.resolve();
    }

    async onCopy() {
        const text = this.rawText;
        if (!text || !this.copyButton) {
            return;
        }

        const label = this.copyButton.textContent;
        try {
            await this.copyText(text);
            this.copyButton.textContent = this.copyButton.dataset.mooUiCopiedLabel || "Copied";
        } catch {
            this.copyButton.textContent = "Copy failed";
        }
        window.setTimeout(() => {
            this.copyButton.textContent = label;
        }, 1400);
    }
}

registry.category("public.interactions").add("moo_ui.code_block", MooUiCodeBlock);
