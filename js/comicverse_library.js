import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "comicverse.library",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        const origOnDrawForeground = nodeType.prototype.onDrawForeground;
        const origOnMouseDown = nodeType.prototype.onMouseDown;

        nodeType.prototype.onNodeCreated = function() {
            const r = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;
            const node = this;
            if (node.comfyClass !== "ComicAssetLibraryNode") return r;

            node.comicverseThumbs = [];
            node.comicverseSelected = [];
            node.comicversePendingDeletions = [];

            node.addWidget("button", "Set output count", null, () => {
                const outWidget = node.widgets?.find(w => w.name === "output_count");
                const desired = Math.max(1, Math.min(6, Number(outWidget?.value || 2)));
                const current = (node.outputs && node.outputs.length) ? node.outputs.length : 0;
                for (let i = current - 1; i >= desired; i--) node.removeOutput(i);
                for (let i = current; i < desired; i++) node.addOutput(`image_${i+1}`, "IMAGE");
                // Force recalc by triggering onResize
                node.onResize(node.size);
                node.setDirtyCanvas(true, true);
            });

            // Add Delete All button
            node.addWidget("button", "Delete All", null, () => {
                // Mark all images for deletion
                const thumbs = node.comicverseThumbs || [];
                node.comicversePendingDeletions = thumbs.map((_, i) => i);
                node.comicverseSelected = [];
                const w = node.widgets?.find(w => w.name === "selected_indices");
                if (w) w.value = "";
                const wDel = node.widgets?.find(w => w.name === "pending_deletions");
                if (wDel) wDel.value = node.comicversePendingDeletions.join(",");
                node.setDirtyCanvas(true, true);
            });

            setTimeout(() => {
                const outWidget = node.widgets?.find(w => w.name === "output_count");
                const desired = Math.max(1, Math.min(6, Number(outWidget?.value || 2)));
                const current = (node.outputs && node.outputs.length) ? node.outputs.length : 0;
                for (let i = current - 1; i >= desired; i--) node.removeOutput(i);
                for (let i = current; i < desired; i++) node.addOutput(`image_${i+1}`, "IMAGE");
                node.setDirtyCanvas(true, true);
            }, 0);

            return r;
        };
        
        // Hijack resize event to enforce minimum size
        nodeType.prototype.onResize = function(newSize) {
            if (this.comfyClass === "ComicAssetLibraryNode") {
                const padding = 6;
                const cell = 84;
                const cols = 3;
                const widgets = this.widgets || [];
                const lastWidget = widgets[widgets.length - 1];
                const widgetsH = lastWidget ? (lastWidget.last_y || 0) + 26 : 100;
                const rows = Math.ceil((this.comicverseThumbs || []).length / cols);
                const desiredH = widgetsH + padding + rows * (cell + padding) + padding;
                const minW = padding + cols * (cell + padding) - padding;
                if (!newSize) newSize = this.size || [minW, desiredH];
                newSize[0] = Math.max(newSize[0] || minW, minW);
                newSize[1] = Math.max(newSize[1] || desiredH, desiredH);
                this.size = newSize;
            }
        };

        nodeType.prototype.onDrawForeground = function(ctx) {
            if (origOnDrawForeground) origOnDrawForeground.apply(this, arguments);
            const node = this;
            if (node.comfyClass !== "ComicAssetLibraryNode") return;

            const thumbs = node.comicverseThumbs || [];
            if (!thumbs.length) return;

            const padding = 6;
            const cell = 84;
            const cols = 3; // limit to 3 columns
            // Calculate actual widgets bottom position using last_y
            const widgets = node.widgets || [];
            const lastWidget = widgets[widgets.length - 1];
            const widgetsH = lastWidget ? (lastWidget.last_y || 0) + 26 : 100;
            const x0 = padding;
            const y0 = widgetsH + padding;

            const rows = Math.ceil(thumbs.length / cols);
            const desiredH = y0 + rows * (cell + padding) + padding;
            const minW = padding + cols * (cell + padding) - padding;
            
            // Set size directly with real-time widget count
            if (!node.size) node.size = [minW, desiredH];
            else {
                node.size[1] = Math.max(node.size[1], desiredH);
                node.size[0] = Math.max(node.size[0], minW);
            }

            for (let i = 0; i < thumbs.length; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                const x = x0 + col * (cell + padding);
                const y = y0 + row * (cell + padding);
                ctx.fillStyle = "#222";
                ctx.fillRect(x, y, cell, cell);
                const img = thumbs[i];
                if (img?.width && img?.height) {
                    const scale = Math.min((cell - 8) / img.width, (cell - 8) / img.height);
                    const w = img.width * scale;
                    const h = img.height * scale;
                    const ix = x + (cell - w) / 2;
                    const iy = y + (cell - h) / 2;
                    ctx.drawImage(img, ix, iy, w, h);
                }
                
                // Draw "pending deletion" overlay first
                if (node.comicversePendingDeletions?.includes(i)) {
                    ctx.fillStyle = "rgba(255, 0, 0, 0.4)";
                    ctx.fillRect(x, y, cell, cell);
                    ctx.strokeStyle = "rgba(255, 0, 0, 0.8)";
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.moveTo(x + 10, y + 10);
                    ctx.lineTo(x + cell - 10, y + cell - 10);
                    ctx.moveTo(x + cell - 10, y + 10);
                    ctx.lineTo(x + 10, y + cell - 10);
                    ctx.stroke();
                }
                
                // Draw delete button (X) on top-right corner
                const btnSize = 16;
                const btnX = x + cell - btnSize - 2;
                const btnY = y + 2;
                ctx.fillStyle = "rgba(255, 0, 0, 0.8)";
                ctx.fillRect(btnX, btnY, btnSize, btnSize);
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(btnX + 4, btnY + 4);
                ctx.lineTo(btnX + btnSize - 4, btnY + btnSize - 4);
                ctx.moveTo(btnX + btnSize - 4, btnY + 4);
                ctx.lineTo(btnX + 4, btnY + btnSize - 4);
                ctx.stroke();
                
                if (node.comicverseSelected?.includes(i)) {
                    ctx.strokeStyle = "#3fa7ff";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x + 1, y + 1, cell - 2, cell - 2);
                }

                // Store delete button bounds for click detection
                if (!node.comicverseDeleteBtns) node.comicverseDeleteBtns = [];
                node.comicverseDeleteBtns[i] = { x: btnX, y: btnY, w: btnSize, h: btnSize, index: i };
            }
        };

        nodeType.prototype.onMouseDown = function(e, pos, graphcanvas) {
            if (origOnMouseDown) origOnMouseDown.apply(this, arguments);
            const node = this;
            if (node.comfyClass !== "ComicAssetLibraryNode") return;

            const thumbs = node.comicverseThumbs || [];
            if (!thumbs.length) return;

            const padding = 6;
            const cell = 84;
            const cols = 3; // limit to 3 columns
            const widgets = node.widgets || [];
            const lastWidget = widgets[widgets.length - 1];
            const widgetsH = lastWidget ? (lastWidget.last_y || 0) + 26 : 100;
            const x0 = padding;
            const y0 = widgetsH + padding;

            // Check if clicking on delete button first
            if (node.comicverseDeleteBtns) {
                for (let btn of node.comicverseDeleteBtns) {
                    if (pos[0] >= btn.x && pos[0] <= btn.x + btn.w &&
                        pos[1] >= btn.y && pos[1] <= btn.y + btn.h) {
                        // Delete button clicked - toggle pending deletion mark
                        const idx = node.comicversePendingDeletions.indexOf(btn.index);
                        if (idx === -1) {
                            node.comicversePendingDeletions.push(btn.index);
                        } else {
                            node.comicversePendingDeletions.splice(idx, 1);
                        }
                        const wDel = node.widgets?.find(w => w.name === "pending_deletions");
                        if (wDel) {
                            wDel.value = node.comicversePendingDeletions.join(",");
                        }
                        node.setDirtyCanvas(true, true);
                        return; // Prevent thumbnail selection
                    }
                }
            }

            const x = pos[0] - x0;
            const y = pos[1] - y0;
            if (x < 0 || y < 0) return;
            const col = Math.floor(x / (cell + padding));
            const row = Math.floor(y / (cell + padding));
            if (col < 0 || row < 0) return;
            const idx = row * cols + col;
            if (idx >= 0 && idx < thumbs.length) {
                const sel = node.comicverseSelected || [];
                const i = sel.indexOf(idx);
                if (i >= 0) sel.splice(i, 1);
                else if (sel.length < 6) sel.push(idx);
                node.comicverseSelected = sel;
                const w = node.widgets?.find(w => w.name === "selected_indices");
                if (w) w.value = sel.join(",");
                node.setDirtyCanvas(true, true);
            }
        };
    },
    async setup(app) {
        app.api.addEventListener("comicverse.library.previews", (event) => {
            const { thumbs, selected } = event.detail || {};
            const graph = app.graph;
            if (!graph) return;
            const nodes = graph._nodes?.filter(n => n.comfyClass === "ComicAssetLibraryNode") || [];
            nodes.forEach((target) => {
                const incoming = (thumbs || []).map(t => {
                    const img = new Image();
                    img.src = t.data;
                    return img;
                });
                // Replace entire thumbnails list on each update to match backend state
                target.comicverseThumbs = incoming;
                // Hard cap to avoid unbounded growth
                if (target.comicverseThumbs.length > 200) {
                    target.comicverseThumbs.splice(0, target.comicverseThumbs.length - 200);
                }
                target.comicverseSelected = Array.isArray(selected) ? selected.slice(0, 6) : [];
                const w = target.widgets?.find(w => w.name === "selected_indices");
                if (w) w.value = (target.comicverseSelected || []).join(",");
                
                // Clear pending deletions after workflow execution
                target.comicversePendingDeletions = [];
                const wDel = target.widgets?.find(w => w.name === "pending_deletions");
                if (wDel) wDel.value = "";
            });
            app.graph?.setDirtyCanvas(true, true);
        });
    },
});


