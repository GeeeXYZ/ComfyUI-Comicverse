import { app } from "../../scripts/app.js";

const MAX_INPUTS = 8;

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

const parseWeights = (raw) => {
    if (!raw) return {};
    try {
        const data = JSON.parse(raw);
        if (data && typeof data === "object" && !Array.isArray(data)) {
            const result = {};
            for (const [key, value] of Object.entries(data)) {
                const num = Number(value);
                if (Number.isFinite(num) && num > 0) {
                    result[key] = num;
                }
            }
            return result;
        }
    } catch (err) {
        console.warn("PromptRolling: failed to parse weights", err);
    }
    return {};
};

const serializeWeights = (node) => {
    const state = node.promptRolling;
    if (!state?.hiddenWeights) return;
    state.hiddenWeights.value = JSON.stringify(state.weights);
    if (typeof state.hiddenWeights.callback === "function") {
        state.hiddenWeights.callback(state.hiddenWeights.value);
    }
    app.graph?.setDirtyCanvas(true, true);
};

const pruneWeights = (node) => {
    const state = node.promptRolling;
    if (!state) return;
    const validKeys = new Set((node.inputs || []).map((_, idx) => `input_${idx}`));
    Object.keys(state.weights).forEach((key) => {
        if (!validKeys.has(key)) delete state.weights[key];
    });
};

const syncInputSlots = (node) => {
    if (!node.inputs) node.inputs = [];
    let connected = 0;
    node.inputs.forEach((input) => {
        if (!input) return;
        const linkId = typeof input.link === "number" ? input.link : (Array.isArray(input.links) ? input.links[0] : null);
        if (linkId != null) connected += 1;
    });

    let desired = Math.min(MAX_INPUTS, connected + 1);
    if (desired < 1) desired = 1;

    while (node.inputs.length < desired) {
        node.addInput(`Library ${node.inputs.length + 1}`, "STRING");
    }

    for (let i = node.inputs.length - 1; i >= desired; i--) {
        const input = node.inputs[i];
        if (input) {
            const linkId = typeof input.link === "number" ? input.link : (Array.isArray(input.links) ? input.links[0] : null);
            if (linkId == null) {
                node.removeInput(i);
            }
        }
    }

    (node.inputs || []).forEach((input, idx) => {
        if (input) input.name = `Library ${idx + 1}`;
    });
};

const rebuildWeightWidgets = (node) => {
    const state = node.promptRolling;
    if (!state) return;

    pruneWeights(node);

    node.widgets = (node.widgets || []).filter((w) => !w?.promptRollingWeight);

    (node.inputs || []).forEach((input, idx) => {
        const key = `input_${idx}`;
        const current = state.weights[key] ?? 1.0;
        const widget = node.addWidget("number", `Weight ${idx + 1}`, current, (value) => {
            const numeric = Number(value);
            state.weights[key] = Number.isFinite(numeric) && numeric > 0 ? Number(numeric.toFixed(2)) : 1.0;
            serializeWeights(node);
        }, {
            min: 0.1,
            step: 0.1,
            precision: 2,
            serialize: false,
        });
        widget.promptRollingWeight = true;
        widget.size = [120, 20];
    });

    if (state.seedWidget) {
        state.seedWidget.computeSize = () => [120, 26];
    }

    node.setDirtyCanvas(true, true);
};

const ensureOutputWidgets = (node) => {
    const state = node.promptRolling;
    if (!state) return;

    if (!state.outputWidget) {
        const outputWidget = node.addWidget("text", "Last Prompt", "", () => {}, {
            multiline: true,
            serialize: false,
        });
        outputWidget.promptRollingOutput = true;
        outputWidget.readOnly = true;
        outputWidget.computeSize = function () {
            const lines = (this.value || "").split(/\r?\n/);
            const height = Math.max(50, lines.length * 18 + 20);
            const width = Math.max(220, ...lines.map((line) => line.length * 7 + 40));
            return [Math.min(Math.max(width, 220), 480), Math.min(Math.max(height, 50), 220)];
        };
        state.outputWidget = outputWidget;
    }

    if (!state.detailsWidget) {
        const detailsWidget = node.addWidget("text", "Details", "", () => {}, {
            multiline: true,
            serialize: false,
        });
        detailsWidget.promptRollingOutput = true;
        detailsWidget.readOnly = true;
        detailsWidget.computeSize = function () {
            const lines = (this.value || "").split(/\r?\n/);
            const height = Math.max(60, lines.length * 18 + 20);
            const width = Math.max(220, ...lines.map((line) => line.length * 7 + 40));
            return [Math.min(Math.max(width, 220), 520), Math.min(Math.max(height, 60), 260)];
        };
        state.detailsWidget = detailsWidget;
    }
};

app.registerExtension({
    name: "comicverse.prompt_rolling",
    async nodeCreated(node) {
        if (node.comfyClass !== "PromptRollingNode") return;

        if (!node.widgets) node.widgets = [];

        const hiddenWeights = node.widgets.find((w) => w.name === "weights_json");
        const hiddenSeed = node.widgets.find((w) => w.name === "seed");

        if (!hiddenWeights) return;

        const state = {
            weights: parseWeights(hiddenWeights.value),
            hiddenWeights,
            seedHidden: hiddenSeed || null,
            seedWidget: null,
        };
        node.promptRolling = state;

        hardHide(hiddenWeights);
        if (hiddenSeed) {
            hardHide(hiddenSeed);
            const seedWidget = node.addWidget("number", "Seed", hiddenSeed.value ?? -1, (value) => {
                const numeric = Number(value);
                const clamped = Number.isFinite(numeric) ? Math.floor(numeric) : -1;
                hiddenSeed.value = clamped;
                if (typeof hiddenSeed.callback === "function") {
                    hiddenSeed.callback(hiddenSeed.value);
                }
            }, {
                step: 1,
                precision: 0,
                serialize: true,
            });
            state.seedWidget = seedWidget;
        }

        serializeWeights(node);
        syncInputSlots(node);
        rebuildWeightWidgets(node);
        ensureOutputWidgets(node);

        const originalConnectionsChange = node.onConnectionsChange;
        node.onConnectionsChange = function (type, slot, connected, link_info) {
            const result = typeof originalConnectionsChange === "function"
                ? originalConnectionsChange.apply(this, arguments)
                : undefined;
            if (type === LiteGraph.INPUT) {
                syncInputSlots(this);
                rebuildWeightWidgets(this);
            }
            return result;
        };

        const originalOnConfigure = node.onConfigure;
        node.onConfigure = function () {
            const r = typeof originalOnConfigure === "function" ? originalOnConfigure.apply(this, arguments) : undefined;
            const hidden = this.widgets?.find((w) => w.name === "weights_json");
            if (hidden) {
                this.promptRolling.weights = parseWeights(hidden.value);
            }
            syncInputSlots(this);
            rebuildWeightWidgets(this);
            ensureOutputWidgets(this);
            return r;
        };

        const originalExecuted = node.onExecuted;
        node.onExecuted = function () {
            const r = typeof originalExecuted === "function" ? originalExecuted.apply(this, arguments) : undefined;
            const state = this.promptRolling;
            if (!state) return r;

            ensureOutputWidgets(this);

            const output = arguments[0];
            let promptText = "";
            let detailsText = "";

            if (output) {
                const extract = (value) => {
                    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
                    if (typeof value === "string") return value;
                    return "";
                };

                if (Array.isArray(output)) {
                    promptText = extract(output[0]);
                    detailsText = extract(output[1]);
                } else if (typeof output === "object") {
                    promptText = extract(output.prompt ?? output["0"]);
                    detailsText = extract(output.details ?? output["1"]);
                }
            }

            if (state.outputWidget) {
                state.outputWidget.value = promptText || "";
            }
            if (state.detailsWidget) {
                state.detailsWidget.value = detailsText || "";
            }
            app.graph?.setDirtyCanvas(true, true);
            return r;
        };

        const originalRemoved = node.onRemoved;
        node.onRemoved = function () {
            delete this.promptRolling;
            if (typeof originalRemoved === "function") originalRemoved.apply(this, arguments);
        };
    },
});


