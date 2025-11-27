import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const MAX_INPUTS = 8;

const syncDynamicInputs = (node) => {
    if (!node.inputs) node.inputs = [];
    if (!node.widgets) node.widgets = [];

    const getLibraryIndex = (name) => {
        const match = name && name.match(/library_(\d+)/);
        return match ? parseInt(match[1], 10) : null;
    };

    const ensureInputCount = () => {
        let highestConnected = 0;
        for (const input of node.inputs) {
            const idx = getLibraryIndex(input?.name);
            if (!idx) continue;
            if (input.link != null && idx > highestConnected) {
                highestConnected = idx;
            }
        }

        const desired = Math.min(MAX_INPUTS, Math.max(1, highestConnected + 1));

        while (node.inputs.length < desired) {
            const nextIdx = node.inputs.length + 1;
            node.addInput(`library_${nextIdx}`, "STRING");
        }

        for (let i = node.inputs.length - 1; i >= desired; i--) {
            const input = node.inputs[i];
            if (input && input.link == null) {
                node.removeInput(i);
            }
        }
    };

    const ensureWeightWidgets = () => {
        const connectedLibraries = node.inputs
            .map((input) => {
                if (!input || input.link == null) return null;
                const idx = getLibraryIndex(input.name);
                return Number.isFinite(idx) ? idx : null;
            })
            .filter((idx) => idx !== null);

        const highestIndex = connectedLibraries.length
            ? Math.max(...connectedLibraries)
            : 1;

        const neededWeights = Math.max(1, connectedLibraries.length, highestIndex);

        const weightWidgets = node.widgets
            .map((widget, idx) => ({ widget, idx }))
            .filter(({ widget }) => widget?.name?.startsWith("weight_"));

        // remove extra
        weightWidgets
            .filter(({ widget }) => {
                const match = widget.name.match(/^weight_(\d+)$/);
                return match ? parseInt(match[1], 10) > neededWeights : false;
            })
            .sort((a, b) => b.idx - a.idx)
            .forEach(({ widget, idx }) => {
                widget.onRemove?.();
                node.widgets.splice(idx, 1);
            });

        // add missing
        for (let i = 1; i <= neededWeights; i++) {
            const name = `weight_${i}`;
            let widget = node.widgets.find((w) => w?.name === name);
            if (!widget) {
                widget = ComfyWidgets.FLOAT(
                    node,
                    name,
                    [
                        "FLOAT",
                        {
                            default: 1.0,
                            min: 0.0,
                            max: 2.0,
                            step: 0.1,
                        },
                    ],
                    app
                ).widget;
            }
        }

        // sort widgets: weights ascending
        node.widgets.sort((a, b) => {
            if (!a?.name || !b?.name) return 0;

            const aMatch = a.name.match(/^weight_(\d+)$/);
            const bMatch = b.name.match(/^weight_(\d+)$/);
            if (aMatch && bMatch) {
                return parseInt(aMatch[1], 10) - parseInt(bMatch[1], 10);
            }
            if (aMatch) return -1;
            if (bMatch) return 1;
            return 0;
        });

        return neededWeights;
    };

    ensureInputCount();
    const visibleWeights = ensureWeightWidgets();

    const widgetHeight = 28;
    const inputHeight = 20;
    const padding = 16;

    const weightsHeight = visibleWeights * widgetHeight;
    const inputsHeight = node.inputs.length * inputHeight;
    const contentHeight = 60 + weightsHeight + inputsHeight + padding;

    const minWidth = 320;
    const minHeight = Math.max(160, contentHeight);

    const currentWidth = node.size?.[0] || minWidth;
    const currentHeight = node.size?.[1] || minHeight;

    node.size = [Math.max(minWidth, currentWidth), Math.max(minHeight, currentHeight)];
    node.minSize = node.minSize || [minWidth, minHeight];
    node.minSize[0] = minWidth;
    node.minSize[1] = minHeight;

    node.setDirtyCanvas(true, true);
};

app.registerExtension({
    name: "comicverse.prompt_queue",
    async nodeCreated(node) {
        if (node.comfyClass !== "PromptQueueNode") return;

        syncDynamicInputs(node);

        const originalConnectionsChange = node.onConnectionsChange;
        node.onConnectionsChange = function (type, slot, connected, link_info) {
            const result = originalConnectionsChange ? originalConnectionsChange.apply(this, arguments) : undefined;

            if (type === LiteGraph.INPUT) {
                syncDynamicInputs(this);
                this.setDirtyCanvas(true, true);
            }

            return result;
        };

        const originalOnConfigure = node.onConfigure;
        node.onConfigure = function (info) {
            const r = originalOnConfigure ? originalOnConfigure.apply(this, arguments) : undefined;
            syncDynamicInputs(this);
            return r;
        };

        const originalOnResize = node.onResize;
        node.onResize = function (size) {
            if (this.minSize) {
                size[0] = Math.max(size[0], this.minSize[0]);
                size[1] = Math.max(size[1], this.minSize[1]);
            }
            if (originalOnResize) {
                return originalOnResize.apply(this, arguments);
            }
        };

        node.setSize([320, 160]);
        syncDynamicInputs(node);
    },
});
