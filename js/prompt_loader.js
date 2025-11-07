import { app } from "../../scripts/app.js";

const hardHide = (widget) => {
    if (!widget) return;
    widget.hidden = true;
    widget.type = "hidden";
    widget.label = "";
    widget.computeSize = () => [0, -4];
    widget.size = [0, -4];
    widget.height = 0;
    widget.disabled = true;
    widget.serialize = true;
    widget.flags = widget.flags || {};
    widget.flags.skipDraw = true;
    widget.flags.collapsed = true;
    widget.flags.no_focus = true;
};

const parseSpecs = (value) => {
    if (!value) return [];
    try {
        const arr = JSON.parse(value);
        if (Array.isArray(arr)) {
            return arr.filter((item) => item && typeof item === "object" && typeof item.path === "string");
        }
    } catch (err) {
        console.warn("PromptLoader: failed to parse specs", err);
    }
    return [];
};

const serializeSpecs = (node, specs) => {
    const widget = node.promptLoader?.hiddenWidget;
    if (!widget) return;
    widget.value = JSON.stringify(specs);
    if (typeof widget.callback === "function") {
        widget.callback(widget.value);
    }
    app.graph?.setDirtyCanvas(true, true);
};

const rebuildSpecWidgets = (node) => {
    const state = node.promptLoader;
    if (!state) return;

    // Remove previous dynamic widgets
    node.widgets = (node.widgets || []).filter((w) => !w?.promptLoaderItem);

    state.specs.forEach((spec, index) => {
        const label = spec.name?.trim() || `File ${index + 1}`;
        const display = node.addWidget("text", label, spec.path, () => {}, {
            multiline: false,
            serialize: false,
        });
        display.promptLoaderItem = true;
        display.disabled = true;
        display.readOnly = true;
        display.size = [250, 26];
        display.computeSize = () => [Math.max(250, (label.length + spec.path.length) * 6), 26];

        const editBtn = node.addWidget("button", `Edit ${label}`, null, () => {
            const newPath = window.prompt(`Update path for ${label}`, spec.path || "");
            if (typeof newPath === "string" && newPath.trim()) {
                const trimmed = newPath.trim();
                const newName = window.prompt(`Display name for ${trimmed}`, spec.name || label) ?? spec.name;
                spec.path = trimmed;
                spec.name = newName ? newName.trim() : spec.name;
                serializeSpecs(node, state.specs);
                rebuildSpecWidgets(node);
                app.graph?.setDirtyCanvas(true, true);
            }
        }, { serialize: false });
        editBtn.promptLoaderItem = true;
        editBtn.computeSize = () => [120, 20];

        const removeBtn = node.addWidget("button", `Remove ${label}`, null, () => {
            state.specs.splice(index, 1);
            serializeSpecs(node, state.specs);
            rebuildSpecWidgets(node);
            app.graph?.setDirtyCanvas(true, true);
        }, { serialize: false });
        removeBtn.promptLoaderItem = true;
        removeBtn.computeSize = () => [120, 20];
    });

    // Ensure node size accommodates widgets
    if (node.promptLoader?.addButton) {
        const totalHeight = (node.widgets || []).reduce((acc, w) => acc + (w.size?.[1] || 26) + 4, 60);
        node.size = node.size || [320, totalHeight];
        node.size[1] = Math.max(node.size[1], totalHeight);
    }
};

app.registerExtension({
    name: "comicverse.prompt_loader",
    async nodeCreated(node) {
        if (node.comfyClass !== "PromptLibraryLoaderNode") return;

        if (!node.widgets) node.widgets = [];
        const hidden = node.widgets.find((w) => w.name === "file_specs_json");
        if (!hidden) return;

        const specs = parseSpecs(hidden.value);
        node.promptLoader = {
            specs,
            hiddenWidget: hidden,
            addButton: null,
        };

        hardHide(hidden);

        const addButton = node.addWidget("button", "Add Prompt File", null, () => {
            const path = window.prompt("Enter JSON file path", "");
            if (!path) return;
            const trimmedPath = path.trim();
            if (!trimmedPath) return;
            const name = window.prompt("Display name (optional)", "") || "";
            node.promptLoader.specs.push({
                path: trimmedPath,
                name: name.trim() || undefined,
            });
            serializeSpecs(node, node.promptLoader.specs);
            rebuildSpecWidgets(node);
            app.graph?.setDirtyCanvas(true, true);
        }, { serialize: false });
        addButton.promptLoaderControl = true;
        addButton.computeSize = () => [160, 24];
        node.promptLoader.addButton = addButton;

        const summaryWidget = node.addWidget("text", "Summary", "", () => {}, {
            multiline: true,
            serialize: false,
        });
        summaryWidget.promptLoaderSummary = true;
        summaryWidget.readOnly = true;
        summaryWidget.computeSize = function () {
            const lines = (this.value || "").split(/\r?\n/);
            const height = Math.max(60, lines.length * 18 + 20);
            const width = Math.max(260, ...lines.map((line) => line.length * 7 + 40));
            return [Math.min(Math.max(width, 260), 480), Math.min(Math.max(height, 60), 400)];
        };
        node.promptLoader.summaryWidget = summaryWidget;

        rebuildSpecWidgets(node);

        const originalOnConfigure = node.onConfigure;
        node.onConfigure = function (info) {
            const r = typeof originalOnConfigure === "function" ? originalOnConfigure.apply(this, arguments) : undefined;
            const widget = this.widgets?.find((w) => w.name === "file_specs_json");
            if (widget) {
                this.promptLoader.specs = parseSpecs(widget.value);
                serializeSpecs(this, this.promptLoader.specs);
                rebuildSpecWidgets(this);
            }
            return r;
        };

        const originalOnExecuted = node.onExecuted;
        node.onExecuted = function () {
            const r = typeof originalOnExecuted === "function" ? originalOnExecuted.apply(this, arguments) : undefined;
            const state = this.promptLoader;
            if (!state?.summaryWidget) return r;

            // Attempt to derive summary from execution outputs (arguments[0])
            const output = arguments[0];
            let summary = "";
            if (output) {
                if (Array.isArray(output)) {
                    const maybe = output[1];
                    if (typeof maybe === "string") summary = maybe;
                } else if (typeof output === "object") {
                    const values = output.summary || output["summary"];
                    if (Array.isArray(values) && typeof values[0] === "string") {
                        summary = values[0];
                    } else if (typeof values === "string") {
                        summary = values;
                    }
                }
            }

            if (summary) {
                state.summaryWidget.value = summary;
            }
            state.summaryWidget.computeSize();
            app.graph?.setDirtyCanvas(true, true);
            return r;
        };

        const originalOnRemoved = node.onRemoved;
        node.onRemoved = function () {
            delete this.promptLoader;
            if (typeof originalOnRemoved === "function") originalOnRemoved.apply(this, arguments);
        };
    },
});


