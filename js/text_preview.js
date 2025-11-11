import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "comicverse.textpreview",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "TextPreviewNode") return;

        // Node Created - exactly like AlekPet's PreviewTextNode
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated
                ? onNodeCreated.apply(this, arguments)
                : undefined;

            let TextPreviewNodes = app.graph._nodes.filter(
                (wi) => wi.type == nodeData.name
            );
            let nodeName = `${nodeData.name}_${TextPreviewNodes.length}`;

            console.log(`[TextPreview] Create ${nodeData.name}: ${nodeName}`);

            const wi = ComfyWidgets.STRING(
                this,
                nodeName,
                [
                    "STRING",
                    {
                        default: "",
                        placeholder: "Text message output...",
                multiline: true,
                    },
                ],
                app
            );
            wi.widget.inputEl.readOnly = true;
            wi.widget.inputEl.style.opacity = 0.6;
            wi.widget.inputEl.style.fontFamily = "monospace";

            this.setSize(this.computeSize(this.size));
            app.graph.setDirtyCanvas(true, false);

            return ret;
        };

        // Function set value - exactly like AlekPet
        const outSet = function (texts) {
            if (!texts || texts.length === 0) return;

            let widget_id = this?.widgets.findIndex(
                (w) => w.type == "customtext"
            );

            if (widget_id < 0) {
                console.warn("[TextPreview] No customtext widget found!");
                return;
            }

            let formatted = texts;

            if (Array.isArray(texts)) {
                formatted = texts.map((v) =>
                    typeof v === "object" ? JSON.stringify(v) : v.toString()
                );
                formatted = formatted
                    .filter((word) => word.trim() !== "")
                    .map((word) => word.trim())
                    .join(" ");
            }

            console.log("[TextPreview] Setting value:", formatted);
            this.widgets[widget_id].value = formatted;
            app.graph.setDirtyCanvas(true);
        };

        // onExecuted - exactly like AlekPet
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            onExecuted?.apply(this, arguments);
            
            console.log("[TextPreview] onExecuted message:", message);
            
            // Try different possible message formats
            let texts = null;
            if (message?.string) {
                texts = message.string;
            } else if (message?.text) {
                texts = message.text;
                }
                
            if (texts) {
                outSet.call(this, texts);
                }
        };
    },
});
