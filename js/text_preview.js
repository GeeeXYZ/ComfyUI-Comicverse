import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "comicverse.textpreview",
    async nodeCreated(node) {
        if (node.comfyClass !== "TextPreviewNode") return;

        // Hide the default text input widget (since it's forceInput)
        const textWidget = node.widgets?.find(w => w.name === "text");
        if (textWidget) {
            textWidget.type = "hidden";
            textWidget.computeSize = () => [0, -4];
        }

        // Create a display widget to show the text (multiline textarea)
        const displayWidget = node.addWidget(
            "text",
            "preview",
            "",
            () => {},
            {
                multiline: true,
                serialize: false,
            }
        );
        
        // Make it read-only and style it as a proper multiline textarea
        setTimeout(() => {
            if (displayWidget.inputEl) {
                // Replace the default input with a textarea for true multiline support
                const oldInput = displayWidget.inputEl;
                const textarea = document.createElement("textarea");
                textarea.value = oldInput.value || "";
                textarea.readOnly = true;
                textarea.style.opacity = "0.85";
                textarea.style.fontFamily = "monospace";
                textarea.style.fontSize = "12px";
                textarea.style.whiteSpace = "pre-wrap";
                textarea.style.overflow = "auto";
                textarea.style.resize = "vertical";
                textarea.rows = 6;

                oldInput.parentNode?.replaceChild(textarea, oldInput);
                displayWidget.inputEl = textarea;
            }
        }, 0);

        // Custom compute size for better display
        displayWidget.computeSize = function(width) {
            const lines = (this.value || "").split(/\r?\n/);
            const lineCount = Math.max(6, Math.min(lines.length + 1, 20));
            const height = lineCount * 20 + 40;
            return [width || 400, height];
        };

        // Store reference for later updates
        node.textPreviewWidget = displayWidget;

        // Update display when node is executed
        const originalOnExecuted = node.onExecuted;
        node.onExecuted = function(message) {
            if (originalOnExecuted) {
                originalOnExecuted.apply(this, arguments);
            }

            // The backend returns {"ui": {"text": [text_value]}}
            // ComfyUI passes this as the message parameter
            if (message && message.text) {
                let textValue = "";
                
                if (Array.isArray(message.text)) {
                    textValue = message.text[0] || "";
                } else if (typeof message.text === "string") {
                    textValue = message.text;
                }
                
                if (this.textPreviewWidget) {
                    const finalValue = String(textValue ?? "");
                    this.textPreviewWidget.value = finalValue;
                    if (this.textPreviewWidget.inputEl) {
                        this.textPreviewWidget.inputEl.value = finalValue;
                    }
                    // Trigger size recalculation
                    this.setSize(this.computeSize());
                }
            }

            app.graph?.setDirtyCanvas(true, true);
        };

        // Set initial size
        node.setSize([400, 150]);
    },
});

