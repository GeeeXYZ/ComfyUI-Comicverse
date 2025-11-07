import { app } from "../../scripts/app.js";

const MAX_INPUTS = 8;

// Dynamically manage input/weight pairs and hide unused widgets
const syncDynamicInputs = (node) => {
    if (!node.inputs) node.inputs = [];
    if (!node.widgets) node.widgets = [];

    const getLibraryIndex = (name) => {
        const match = name && name.match(/library_(\d+)/);
        return match ? parseInt(match[1]) : null;
    };

    const ensureInputCount = () => {
        // Determine highest connected library index
        let highestConnected = 0;
        for (const input of node.inputs) {
            const idx = getLibraryIndex(input?.name);
            if (!idx) continue;
            if (input.link != null && idx > highestConnected) {
                highestConnected = idx;
            }
        }

        const desired = Math.min(MAX_INPUTS, Math.max(1, highestConnected + 1));

        // Add inputs up to desired count
        while (node.inputs.length < desired) {
            const nextIdx = node.inputs.length + 1;
            node.addInput(`library_${nextIdx}`, "STRING");
        }

        // Remove extra inputs (only if unconnected)
        for (let i = node.inputs.length - 1; i >= desired; i--) {
            const input = node.inputs[i];
            if (input && input.link == null) {
                node.removeInput(i);
            }
        }
    };

    const updateWeightWidgets = (connectedCount) => {
        let visibleWeightCount = 0;

        for (const widget of node.widgets) {
            if (!widget || !widget.name) continue;

            if (widget.name === "seed") {
                if (!widget.__origComputeSize && widget.computeSize) {
                    widget.__origComputeSize = widget.computeSize;
                }
                widget.hidden = false;
                widget.disabled = false;
                widget.computeSize = widget.__origComputeSize || widget.computeSize;
                visibleWeightCount++;
                continue;
            }

            const match = widget.name.match(/^weight_(\d+)$/);
            if (!match) continue;

            const weightIndex = parseInt(match[1]);
            const shouldShow = weightIndex <= Math.max(1, connectedCount);

            if (!widget.__origComputeSize && widget.computeSize) {
                widget.__origComputeSize = widget.computeSize;
            }

            widget.hidden = !shouldShow;
            widget.disabled = !shouldShow;
            widget.computeSize = shouldShow
                ? widget.__origComputeSize || widget.computeSize
                : () => [0, -4];
            widget.type = shouldShow ? "number" : "hidden";

            if (shouldShow) visibleWeightCount++;
        }

        return visibleWeightCount;
    };

    ensureInputCount();

    const connectedCount = Math.max(0, ...node.inputs
        .map((input) => (input && input.link != null ? getLibraryIndex(input.name) : 0)));

    const visibleWeightCount = updateWeightWidgets(connectedCount);

    // Adjust node size based on visible widgets and inputs
    const baseHeight = 100;
    const weightHeight = 36;
    const inputHeight = 26;
    const visibleInputs = node.inputs.length;
    const totalHeight = baseHeight + visibleWeightCount * weightHeight + visibleInputs * inputHeight;

    const minWidth = 320;
    const minHeight = 140;
    const width = Math.max(minWidth, node.size?.[0] || minWidth);
    const height = Math.max(minHeight, totalHeight);

    node.size = [width, height];
    node.setDirtyCanvas(true, true);
};

app.registerExtension({
    name: "comicverse.prompt_rolling",
    async nodeCreated(node) {
        if (node.comfyClass !== "PromptRollingNode") return;
        
        // Initialize dynamic input management
        syncDynamicInputs(node);
        
        // Hook into connection changes
        const originalConnectionsChange = node.onConnectionsChange;
        node.onConnectionsChange = function (type, slot, connected, link_info) {
            const result = originalConnectionsChange ? originalConnectionsChange.apply(this, arguments) : undefined;
            
            if (type === LiteGraph.INPUT) {
                syncDynamicInputs(this);
                this.setDirtyCanvas(true, true);
            }
            
            return result;
        };
        
        // Hook into configure (when loading from saved workflow)
        const originalOnConfigure = node.onConfigure;
        node.onConfigure = function (info) {
            const r = originalOnConfigure ? originalOnConfigure.apply(this, arguments) : undefined;
            syncDynamicInputs(this);
            return r;
        };
        
        // Set initial size
        node.setSize([300, 150]);
    },
});


