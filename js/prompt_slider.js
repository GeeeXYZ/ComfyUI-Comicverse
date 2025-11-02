import { app } from "../../scripts/app.js";

const parsePrompts = (raw) => {
    if (!raw) return [];
    const tokens = raw
        .split(/[\n,]/)
        .map((token) => token.trim())
        .filter((token, index, arr) => token && arr.indexOf(token) === index);
    return tokens;
};

const hardHide = (widget) => {
    if (!widget) return;
    widget.hidden = true;
    widget.type = "hidden";
    widget.label = "";
    widget.computeSize = () => [0, -4];
    widget.size = [0, -4];
    widget.height = 0;

    const emptyDraw = () => {};
    widget.draw = emptyDraw;
    widget.onDraw = null;
    widget.drawBackground = emptyDraw;
    widget.drawForeground = emptyDraw;

    widget.mouse = () => false;
    widget.onMouse = () => false;
    widget.onMouseEnter = null;
    widget.onMouseLeave = null;
    widget.onMouseDown = null;
    widget.onMouseUp = null;
    widget.onMouseMove = null;
    widget.onMouseWheel = null;

    widget.serialize = true;
    widget.disabled = true;

    if (widget.flags) {
        widget.flags.ignoreMouse = true;
        widget.flags.noHover = true;
        widget.flags.collapsed = true;
        widget.flags.no_focus = true;
        widget.flags.hidden = true;
        widget.flags.skipDraw = true;
    } else {
        widget.flags = {
            ignoreMouse: true,
            noHover: true,
            collapsed: true,
            no_focus: true,
            hidden: true,
            skipDraw: true,
        };
    }

    if (widget.options) {
        widget.options.hidden = true;
    }
    
    // Move widget off-screen to prevent any visual artifacts
    widget.last_y = -9999;
    widget.y = -9999;
};

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const PANEL_SETTINGS = {
    columnWidth: 25,
    gap: 4,
    sidePadding: 16,
    trackHeight: 100,
    topPadding: 50,
    bottomPadding: 20,
    sliderWidth: 4,
    knobRadius: 6,
    trackRadius: 6,
    trackBorder: 1,
};

const PANEL_COLORS = {
    background: "#1a1a1a",
    track: "#2a2a2a",
    trackBorder: "#3a3a3a",
    active: "#cccccc",
    knobFill: "#e8e8e8",
    knobStroke: "#1a1a1a",
    valueText: "#d0d0d0",
    labelText: "#888888",
    emptyText: "#666666",
};

const MIN_PANEL_WIDTH = 160;
const OUTER_MARGIN = 6;

const drawRoundedRect = (ctx, x, y, width, height, radius) => {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
};

const clampToRange = (value) => {
    if (typeof value === "number" && Number.isFinite(value)) {
        return clamp(value, 0, 2);
    }
    const numeric = parseFloat(value);
    if (!Number.isFinite(numeric)) {
        return 1.0;
    }
    return clamp(numeric, 0, 2);
};

const tryReadLinkedString = (node) => {
    const graph = app.graph;
    if (!graph) return null;
    const inputs = Array.isArray(node.inputs) ? node.inputs : [];
    for (const input of inputs) {
        const linkId = (typeof input?.link === "number" ? input.link : null) ?? (Array.isArray(input?.links) ? input.links[0] : null);
        if (linkId == null) continue;
        const link = graph.links?.[linkId];
        if (!link) continue;
        const originId = link.origin_id ?? link.originId ?? link.origin_node_id ?? link.origin_node;
        const srcNode = typeof originId === "number" ? graph.getNodeById?.(originId) : null;
        if (!srcNode) continue;
        const namesPriority = ["string", "text", "prompt", "value"];
        if (Array.isArray(srcNode.widgets)) {
            for (const name of namesPriority) {
                const w = srcNode.widgets.find((it) => it?.name === name && typeof it.value === "string" && it.value.trim());
                if (w) return w.value;
            }
            const anyText = srcNode.widgets.find((it) => typeof it?.value === "string" && it.value.trim());
            if (anyText) return anyText.value;
        }
    }
    return null;
};

const buildPanelWidget = (node, state, serializeStrengths) => {
    const widget = {
        name: "prompt_slider_panel",
        type: "custom",
        serialize: false,
    };

    widget.computeSize = function () {
        const count = Math.max(state.prompts.length, 1);
        const columns = Math.max(count, 1);
        const rows = 1;
        const contentWidth = columns * PANEL_SETTINGS.columnWidth + Math.max(0, columns - 1) * PANEL_SETTINGS.gap;
        const innerWidth = PANEL_SETTINGS.sidePadding * 2 + contentWidth;
        const totalWidth = Math.max(MIN_PANEL_WIDTH, innerWidth + OUTER_MARGIN * 2);
        const height = PANEL_SETTINGS.topPadding + rows * PANEL_SETTINGS.trackHeight + PANEL_SETTINGS.bottomPadding;
        this._computedSize = [totalWidth, height];
        this._contentWidth = contentWidth;
        this._columns = columns;
        this._rows = rows;
        return this._computedSize;
    };

    widget.draw = function (ctx, nodeInstance, widgetWidth, y, widgetHeight) {
        const computed = this._computedSize ?? this.computeSize();
        const width = widgetWidth ?? computed[0];
        const height = widgetHeight ?? computed[1];
        const prompts = state.prompts;
        const columns = this._columns ?? Math.max(prompts.length, 1);
        const contentWidth = this._contentWidth ?? (columns * PANEL_SETTINGS.columnWidth + Math.max(0, columns - 1) * PANEL_SETTINGS.gap);
        const innerWidth = width - OUTER_MARGIN * 2;
        const extraSpace = Math.max(0, innerWidth - (PANEL_SETTINGS.sidePadding * 2 + contentWidth));
        const baseX = OUTER_MARGIN + PANEL_SETTINGS.sidePadding + extraSpace / 2;
        const trackTopBase = OUTER_MARGIN + PANEL_SETTINGS.topPadding;

        state.layout = [];

        ctx.save();
        drawRoundedRect(ctx, OUTER_MARGIN, y + OUTER_MARGIN, width - OUTER_MARGIN * 2, height - OUTER_MARGIN * 2, 14);
        ctx.fillStyle = PANEL_COLORS.background;
        ctx.fill();
        ctx.restore();

        if (!prompts.length) {
            return;
        }

        prompts.forEach((entry, index) => {
            const col = index % columns;
            const rowTop = trackTopBase;
            const sliderCenterX = baseX + col * (PANEL_SETTINGS.columnWidth + PANEL_SETTINGS.gap) + PANEL_SETTINGS.columnWidth / 2;
            const sliderX = sliderCenterX - PANEL_SETTINGS.sliderWidth / 2;
            const sliderYAbsolute = y + rowTop;
            const sliderWidth = PANEL_SETTINGS.sliderWidth;
            const sliderHeight = PANEL_SETTINGS.trackHeight;

            state.layout[index] = {
                left: sliderX - PANEL_SETTINGS.knobRadius * 2,
                right: sliderX + sliderWidth + PANEL_SETTINGS.knobRadius * 2,
                top: sliderYAbsolute,
                bottom: sliderYAbsolute + sliderHeight,
                height: sliderHeight,
                centerX: sliderCenterX,
            };

            const value = clampToRange(entry.value);
            const normalized = (value - 0) / 2;
            const activeHeight = sliderHeight * normalized;

            // Track background
            ctx.save();
            drawRoundedRect(
                ctx,
                sliderX - PANEL_SETTINGS.trackBorder,
                sliderYAbsolute,
                sliderWidth + PANEL_SETTINGS.trackBorder * 2,
                sliderHeight,
                PANEL_SETTINGS.trackRadius,
            );
            ctx.fillStyle = PANEL_COLORS.track;
            ctx.fill();
            ctx.lineWidth = PANEL_SETTINGS.trackBorder;
            ctx.strokeStyle = PANEL_COLORS.trackBorder;
            ctx.stroke();

            if (activeHeight > 0) {
                drawRoundedRect(
                    ctx,
                    sliderX - PANEL_SETTINGS.trackBorder,
                    sliderYAbsolute + sliderHeight - activeHeight,
                    sliderWidth + PANEL_SETTINGS.trackBorder * 2,
                    activeHeight,
                    PANEL_SETTINGS.trackRadius,
                );
                ctx.fillStyle = PANEL_COLORS.active;
                ctx.fill();
            }

            // Knob
            const knobCenterY = sliderYAbsolute + sliderHeight - activeHeight;
            ctx.fillStyle = PANEL_COLORS.knobFill;
            ctx.beginPath();
            ctx.arc(sliderCenterX, knobCenterY, PANEL_SETTINGS.knobRadius, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 1;
            ctx.strokeStyle = PANEL_COLORS.knobStroke;
            ctx.stroke();
            ctx.restore();

            // Value text
            ctx.save();
            ctx.font = "11px sans-serif";
            ctx.fillStyle = PANEL_COLORS.valueText;
            ctx.textAlign = "center";
            ctx.fillText(value.toFixed(1), sliderCenterX, sliderYAbsolute - 10);
            ctx.restore();

            // Label text (rotated 90 degrees counterclockwise, on the left side)
            ctx.save();
            ctx.font = "10px sans-serif";
            ctx.fillStyle = PANEL_COLORS.labelText;
            const trackBottomAbsolute = sliderYAbsolute + sliderHeight;
            const labelX = sliderX - 8; // Position to the left of the slider
            const labelY = trackBottomAbsolute; // Align with bottom of track
            
            // Translate to position, rotate -90 degrees, then draw text
            ctx.translate(labelX, labelY);
            ctx.rotate(-Math.PI / 2);
            ctx.textAlign = "left"; // Text starts from bottom of track
            ctx.textBaseline = "middle";
            ctx.fillText(entry.label, 0, 0); // Use full label instead of truncated displayLabel
            ctx.restore();
        });
    };

    widget.mouse = function (event, pos) {
        const { LiteGraph } = globalThis;
        if (!LiteGraph) return false;

        const evType = typeof event === "string" ? event : (event?.type || "");
        const pointerdown = LiteGraph.pointerdown ?? "pointerdown";
        const pointermove = LiteGraph.pointermove ?? "pointermove";
        const pointerup = LiteGraph.pointerup ?? "pointerup";

        const isDown = evType === pointerdown || evType === "mousedown" || evType === "touchstart" || evType === "pointerdown";
        const isMove = evType === pointermove || evType === "mousemove" || evType === "touchmove" || evType === "pointermove";
        const isUp = evType === pointerup || evType === "mouseup" || evType === "touchend" || evType === "pointerup";

        if (isDown) {
            const hitIndex = state.layout.findIndex((metrics) => (
                pos[0] >= metrics.left && pos[0] <= metrics.right &&
                pos[1] >= metrics.top && pos[1] <= metrics.bottom
            ));
            if (hitIndex === -1) return false;
            state.draggingIndex = hitIndex;
        } else if (isUp) {
            state.draggingIndex = null;
            return true;
        }

        if (state.draggingIndex == null) return false;
        if (!isDown && !isMove) return false;

        const metrics = state.layout[state.draggingIndex];
        if (!metrics) return false;

        const yClamped = clamp(pos[1], metrics.top, metrics.bottom);
        let ratio = 1 - (yClamped - metrics.top) / metrics.height;
        ratio = clamp(ratio, 0, 1);
        let computed = ratio * 2;
        computed = Math.round(computed / 0.1) * 0.1; // quantize to 0.1
        computed = Number(computed.toFixed(2));

        const entry = state.prompts[state.draggingIndex];
        if (!entry) return false;
        if (entry.value !== computed) {
            entry.value = computed;
            if (entry.id) {
                state.strengths[entry.id] = computed;
            }
            state.strengths[String(state.draggingIndex)] = computed;
            serializeStrengths();
            app.graph?.setDirtyCanvas(true, true);
        }

        return true;
    };

    return widget;
};

app.registerExtension({
    name: "PromptSlider",
    async nodeCreated(node) {
        if (node.comfyClass !== "PromptStrengthSlider") return;
        if (!node.widgets) node.widgets = [];

        // Robustly remove the auto-created strengths_json input slot without affecting other UI
        const removeStrengthsInput = () => {
            if (!node.inputs) return;
            let removed = false;
            for (let i = node.inputs.length - 1; i >= 0; i--) {
                const inp = node.inputs[i];
                if (inp && inp.name === "strengths_json") {
                    node.removeInput(i);
                    removed = true;
                }
            }
            if (removed && app.graph) app.graph.setDirtyCanvas(true, true);
        };

        // Attempt immediately and also after layout settles
        removeStrengthsInput();
        setTimeout(removeStrengthsInput, 0);
        setTimeout(removeStrengthsInput, 50);
        setTimeout(removeStrengthsInput, 200);
        // Ensure when node is configured from saved workflow
        const originalOnConfigure = node.onConfigure;
        node.onConfigure = function(json) {
            const r = typeof originalOnConfigure === "function" ? originalOnConfigure.apply(this, arguments) : undefined;
            removeStrengthsInput();
            return r;
        };

        const state = {
            prompts: [],
            strengths: {},
            layout: [],
            panelWidget: null,
            draggingIndex: null,
            sourceNodeId: null,
        };

        const getWidget = (name) => node.widgets?.find((w) => w.name === name);

        let strengthJsonWidget = getWidget("strengths_json");
        if (!strengthJsonWidget) {
            strengthJsonWidget = node.addWidget("text", "strengths_json", "", () => {}, { multiline: false, serialize: true });
        }

        const serializeStrengths = () => {
            if (!strengthJsonWidget) return;
            const payload = {};
            const meta = [];
            const promptList = [];
            state.prompts.forEach((entry, index) => {
                const value = Math.round(clamp(entry.value, 0, 2) * 10) / 10; // store quantized 0.1
                const promptKey = entry.prompt ?? entry.id ?? `Prompt ${index + 1}`;
                payload[String(index)] = value;
                payload[promptKey] = value;
                meta.push({
                    id: promptKey,
                    label: entry.label,
                    displayLabel: entry.displayLabel,
                    value,
                });
                promptList.push(promptKey);
            });
            payload.__order__ = meta;
            payload.__prompts__ = promptList;
            if (state.sourceNodeId != null) {
                payload.__source_id__ = state.sourceNodeId;
            }
            strengthJsonWidget.value = JSON.stringify(payload);
            if (typeof strengthJsonWidget.callback === "function") {
                strengthJsonWidget.callback(strengthJsonWidget.value);
            }
        };

        const ensurePanelWidget = () => {
            if (state.panelWidget) return;
            const panelWidget = buildPanelWidget(node, state, serializeStrengths);
            node.addCustomWidget(panelWidget);
            state.panelWidget = panelWidget;
        };

        ensurePanelWidget();

        const resolvePromptSourceText = () => {
            const fromLink = tryReadLinkedString(node);
            if (fromLink) return fromLink;
            return null;
        };

        const rebuildPanelSize = () => {
            if (!state.panelWidget) return;
            const computedSize = state.panelWidget.computeSize();
            const width = computedSize?.[0] ?? MIN_PANEL_WIDTH;
            const height = computedSize?.[1] ?? (PANEL_SETTINGS.topPadding + PANEL_SETTINGS.trackHeight + PANEL_SETTINGS.bottomPadding);
            const controlBlock = 26 /*button*/ + 12 /*spacing*/;
            const totalHeight = height + controlBlock;
            if (!Array.isArray(node.size)) node.size = [width + 12, totalHeight + 20];
            node.size[0] = Math.max(node.size[0] ?? 0, width + 12);
            node.size[1] = Math.max(node.size[1] ?? 0, totalHeight + 20);
        };

        const loadPrompts = () => {
            const rawSource = resolvePromptSourceText();
            let promptTokens = parsePrompts(rawSource ?? "");

            let existingPayload = {};
            try {
                existingPayload = JSON.parse(strengthJsonWidget?.value ?? "{}") ?? {};
            } catch (err) {
                existingPayload = {};
            }

            const storedMeta = Array.isArray(existingPayload.__order__) ? existingPayload.__order__ : [];
            const storedPrompts = Array.isArray(existingPayload.__prompts__)
                ? existingPayload.__prompts__.map((item) => (typeof item === "string" ? item.trim() : ""))
                    .filter((value) => value)
                : [];
            const storedSourceId = Number.isFinite(existingPayload.__source_id__)
                ? Number(existingPayload.__source_id__)
                : null;
            if (storedSourceId != null) {
                state.sourceNodeId = storedSourceId;
            }

            if (!promptTokens.length && storedPrompts.length) {
                promptTokens = storedPrompts;
            }

            if (!promptTokens.length && storedMeta.length) {
                promptTokens = storedMeta
                    .map((item) => (item && typeof item === "object") ? (item.id || item.label) : null)
                    .filter((value) => typeof value === "string" && value.trim());
            }

            if (!promptTokens.length) {
                promptTokens = Object.keys(existingPayload)
                    .filter((key) => key && !key.startsWith("__") && Number.isNaN(Number(key)));
            }

            state.prompts = promptTokens.map((prompt, index) => {
                const fallbackMeta = storedMeta[index];
                const safePrompt = (typeof prompt === "string" && prompt.trim())
                    ? prompt.trim()
                    : (fallbackMeta?.id || fallbackMeta?.label || `Prompt ${index + 1}`);
                let storedValue = existingPayload[safePrompt];
                if (typeof storedValue !== "number") {
                    storedValue = existingPayload[String(index)];
                }
                if (typeof storedValue !== "number" && fallbackMeta && typeof fallbackMeta.value === "number") {
                    storedValue = fallbackMeta.value;
                }
                const value = clampToRange(storedValue);
                const displaySource = safePrompt || `Prompt ${index + 1}`;
                const displayLabel = displaySource.length > 14 ? `${displaySource.slice(0, 13)}…` : displaySource;
                return {
                    id: safePrompt,
                    prompt: safePrompt,
                    label: displaySource,
                    displayLabel,
                    value,
                };
            });

            state.strengths = {};
            state.prompts.forEach((entry, idx) => {
                const key = entry.prompt || entry.id || String(idx);
                state.strengths[key] = entry.value;
                state.strengths[String(idx)] = entry.value;
            });

            serializeStrengths();
            rebuildPanelSize();
            app.graph?.setDirtyCanvas(true, true);
        };

        const loadButton = node.addWidget("button", "Load Prompts", null, () => {
            loadPrompts();
        }, { serialize: false });
        loadButton.computeSize = function () {
            return [120, 26];
        };
        loadButton.promptSliderControl = true;

        // Now hide the strengthJsonWidget after all other widgets are added
        hardHide(strengthJsonWidget);
        
        // Move strengthJsonWidget to the end to prevent layout issues
        if (Array.isArray(node.widgets) && strengthJsonWidget) {
            const idx = node.widgets.indexOf(strengthJsonWidget);
            if (idx > -1) {
                node.widgets.splice(idx, 1);
                node.widgets.push(strengthJsonWidget);
            }
        }

        rebuildPanelSize();
        
        setTimeout(() => {
            if (app.graph) {
                app.graph.setDirtyCanvas(true, true);
            }
        }, 100);

        // Override onResize to enforce minimum size based on panel content
        const originalOnResize = node.onResize;
        node.onResize = function (size) {
            if (!state.panelWidget) {
                if (typeof originalOnResize === "function") {
                    return originalOnResize.call(this, size);
                }
                return;
            }
            
            const computedSize = state.panelWidget.computeSize();
            const minWidth = (computedSize?.[0] ?? MIN_PANEL_WIDTH) + 36;
            const minHeight = (computedSize?.[1] ?? (PANEL_SETTINGS.topPadding + PANEL_SETTINGS.trackHeight + PANEL_SETTINGS.bottomPadding)) + 70;
            
            // Enforce minimum size
            if (Array.isArray(size)) {
                size[0] = Math.max(size[0] ?? minWidth, minWidth);
                size[1] = Math.max(size[1] ?? minHeight, minHeight);
            }
            
            if (typeof originalOnResize === "function") {
                return originalOnResize.call(this, size);
            }
        };

        const originalOnRemoved = node.onRemoved;
        node.onRemoved = function () {
            state.prompts = [];
            state.layout = [];
            state.strengths = {};
            state.draggingIndex = null;
            if (typeof originalOnRemoved === "function") originalOnRemoved.apply(this);
        };

        loadPrompts();
    },
});

