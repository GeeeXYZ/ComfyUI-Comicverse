import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "comicverse.library",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        const origOnDrawForeground = nodeType.prototype.onDrawForeground;
        const origOnMouseDown = nodeType.prototype.onMouseDown;

        nodeType.prototype.onNodeCreated = function () {
            const r = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;
            const node = this;
            if (node.comfyClass !== "ComicAssetLibraryNode") return r;

            node.comicverseThumbs = [];
            node.comicverseSelected = [];
            node.comicversePendingDeletions = [];
            node.comicversePreviewOverlay = null;

            // Image preview overlay method
            node._showImagePreview = function (img, index) {
                // Close existing preview if any
                if (node.comicversePreviewOverlay) {
                    node.comicversePreviewOverlay.remove();
                    node.comicversePreviewOverlay = null;
                }

                // Create overlay
                const overlay = document.createElement('div');
                overlay.style.cssText = `
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.8); z-index: 9999; display: flex;
                    align-items: center; justify-content: center; cursor: pointer;
                `;

                // Create image container
                const imgContainer = document.createElement('div');
                imgContainer.style.cssText = `
                    position: relative; max-width: 80vw; max-height: 80vh;
                    background: #222; padding: 12px; border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                `;

                const imgEl = document.createElement('img');
                // Use preview image if available, otherwise fallback to thumbnail
                if (img.originalData && img.originalData.preview) {
                    // Use high-res preview image
                    imgEl.src = img.originalData.preview;
                } else {
                    // Fallback to thumbnail if no preview available
                    imgEl.src = img.src;
                }
                imgEl.style.cssText = `
                    display: block; max-width: 80vw; max-height: 80vh;
                    object-fit: contain; border-radius: 4px;
                `;

                // Close button
                const closeBtn = document.createElement('div');
                closeBtn.textContent = '×';
                closeBtn.style.cssText = `
                    position: absolute; top: -8px; right: -8px;
                    width: 32px; height: 32px; background: #333;
                    color: white; border-radius: 50%; display: flex;
                    align-items: center; justify-content: center;
                    cursor: pointer; font-size: 24px; font-weight: bold;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                `;

                const closePreview = () => {
                    overlay.remove();
                    node.comicversePreviewOverlay = null;
                };

                closeBtn.onclick = (e) => { e.stopPropagation(); closePreview(); };
                overlay.onclick = closePreview;
                document.addEventListener('keydown', function escHandler(e) {
                    if (e.key === 'Escape') {
                        closePreview();
                        document.removeEventListener('keydown', escHandler);
                    }
                });

                imgContainer.appendChild(imgEl);
                imgContainer.appendChild(closeBtn);
                overlay.appendChild(imgContainer);
                document.body.appendChild(overlay);
                node.comicversePreviewOverlay = overlay;
            };

            node.addWidget("button", "Set output count", null, () => {
                const outWidget = node.widgets?.find(w => w.name === "output_count");
                const desired = Math.max(1, Math.min(6, Number(outWidget?.value || 2)));
                const current = (node.outputs && node.outputs.length) ? node.outputs.length : 0;
                for (let i = current - 1; i >= desired; i--) node.removeOutput(i);
                for (let i = current; i < desired; i++) node.addOutput(`image_${i + 1}`, "IMAGE");
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
                for (let i = current; i < desired; i++) node.addOutput(`image_${i + 1}`, "IMAGE");
                node.setDirtyCanvas(true, true);
            }, 0);

            return r;
        };

        // Hijack resize event to enforce minimum size
        nodeType.prototype.onResize = function (newSize) {
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

        nodeType.prototype.onDrawForeground = function (ctx) {
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

            // Reset button stores
            node.comicverseDeleteBtns = [];
            node.comicverseZoomBtns = [];

            // Iterate visually (0 to N-1) but draw data in reverse (N-1 to 0)
            for (let i = 0; i < thumbs.length; i++) {
                // Visual position (i)
                const row = Math.floor(i / cols);
                const col = i % cols;
                const x = x0 + col * (cell + padding);
                const y = y0 + row * (cell + padding);

                // Data index (reversed)
                // If we have 5 items (0..4), visual 0 maps to data 4, visual 1 maps to data 3...
                const dataIdx = thumbs.length - 1 - i;
                const img = thumbs[dataIdx];

                ctx.fillStyle = "#222";
                ctx.fillRect(x, y, cell, cell);

                if (img?.width && img?.height) {
                    const scale = Math.min((cell - 8) / img.width, (cell - 8) / img.height);
                    const w = img.width * scale;
                    const h = img.height * scale;
                    const ix = x + (cell - w) / 2;
                    const iy = y + (cell - h) / 2;
                    ctx.drawImage(img, ix, iy, w, h);
                }

                // Draw "pending deletion" overlay first
                if (node.comicversePendingDeletions?.includes(dataIdx)) {
                    ctx.fillStyle = "rgba(180, 0, 0, 0.4)";  // Dark red overlay
                    ctx.fillRect(x, y, cell, cell);
                    ctx.strokeStyle = "rgba(180, 0, 0, 0.9)";  // Dark red cross
                    ctx.lineWidth = 3;  // Large cross for deletion overlay
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
                ctx.fillStyle = "rgba(180, 0, 0, 0.9)";  // Dark red background
                ctx.fillRect(btnX, btnY, btnSize, btnSize);
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(btnX + 4, btnY + 4);
                ctx.lineTo(btnX + btnSize - 4, btnY + btnSize - 4);
                ctx.moveTo(btnX + btnSize - 4, btnY + 4);
                ctx.lineTo(btnX + 4, btnY + btnSize - 4);
                ctx.stroke();

                // Draw zoom/preview button (magnifying glass icon) on bottom-right corner
                const zoomBtnSize = 16;  // Same size as delete button
                const zoomBtnX = x + cell - zoomBtnSize - 2;
                const zoomBtnY = y + cell - zoomBtnSize - 2;
                const centerX = zoomBtnX + zoomBtnSize / 2;
                const centerY = zoomBtnY + zoomBtnSize / 2;
                // Draw magnifying glass icon (circle + handle)
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(centerX - 1, centerY - 1, 4, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(centerX + 3, centerY + 3);
                ctx.lineTo(centerX + 6, centerY + 6);
                ctx.stroke();

                if (node.comicverseSelected?.includes(dataIdx)) {
                    ctx.strokeStyle = "#3fa7ff";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x + 1, y + 1, cell - 2, cell - 2);
                }

                // Store button bounds for click detection, using REAL data index
                // Note: We use push because we are iterating sequentially visually
                node.comicverseDeleteBtns.push({ x: btnX, y: btnY, w: btnSize, h: btnSize, index: dataIdx });
                node.comicverseZoomBtns.push({ x: zoomBtnX, y: zoomBtnY, w: zoomBtnSize, h: zoomBtnSize, index: dataIdx });
            }
            // Reset ctx styles to not affect ComfyUI widgets
            ctx.lineWidth = 1;
            ctx.strokeStyle = "";
            ctx.fillStyle = "";
        };

        nodeType.prototype.onMouseDown = function (e, pos, graphcanvas) {
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

            // Check if clicking on zoom/preview button
            if (node.comicverseZoomBtns) {
                for (let btn of node.comicverseZoomBtns) {
                    if (pos[0] >= btn.x && pos[0] <= btn.x + btn.w &&
                        pos[1] >= btn.y && pos[1] <= btn.y + btn.h) {
                        // Zoom button clicked - show preview overlay
                        const thumbs = node.comicverseThumbs || [];
                        if (thumbs[btn.index]) {
                            node._showImagePreview(thumbs[btn.index], btn.index);
                        }
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

            // Visual index
            const visualIdx = row * cols + col;

            if (visualIdx >= 0 && visualIdx < thumbs.length) {
                // Map visual index to data index (reversed)
                const dataIdx = thumbs.length - 1 - visualIdx;

                const sel = node.comicverseSelected || [];
                const i = sel.indexOf(dataIdx);

                // Get dynamic limit from output_count widget
                const outWidget = node.widgets?.find(w => w.name === "output_count");
                const limit = Math.max(1, Math.min(6, Number(outWidget?.value || 2)));

                if (i >= 0) {
                    // Deselecting is always allowed
                    sel.splice(i, 1);
                } else {
                    // Selecting: enforce limit with FIFO (replace oldest)
                    while (sel.length >= limit) {
                        sel.shift(); // Remove the first (oldest) item
                    }
                    sel.push(dataIdx);
                }

                node.comicverseSelected = sel;
                const w = node.widgets?.find(w => w.name === "selected_indices");
                if (w) w.value = sel.join(",");
                node.setDirtyCanvas(true, true);
            }
        };
    },
    async setup(app) {
        app.api.addEventListener("comicverse.library.previews", (event) => {
            const { mode, thumbs, adds, removes, selected } = event.detail || {};
            const graph = app.graph;
            if (!graph) return;
            const nodes = graph._nodes?.filter(n => n.comfyClass === "ComicAssetLibraryNode") || [];
            nodes.forEach((target) => {
                const applyAdd = (t) => {
                    const img = new Image();
                    img.src = t.data;
                    img.originalData = t;
                    (target.comicverseThumbs || (target.comicverseThumbs = [])).push(img);
                };

                if (mode === "delta") {
                    // Apply removals first (descending indices)
                    const toRemove = Array.isArray(removes) ? removes.slice().sort((a, b) => b - a) : [];
                    toRemove.forEach((idx) => {
                        if (Array.isArray(target.comicverseThumbs) && idx >= 0 && idx < target.comicverseThumbs.length) {
                            target.comicverseThumbs.splice(idx, 1);
                        }
                    });
                    // Apply additions (append)
                    (adds || []).forEach(applyAdd);
                } else {
                    // Full replace
                    const incoming = (thumbs || []).map((t) => {
                        const img = new Image();
                        img.src = t.data;
                        img.originalData = t;
                        return img;
                    });
                    target.comicverseThumbs = incoming;
                }
                // Hard cap to avoid unbounded growth
                if (target.comicverseThumbs.length > 30) {
                    target.comicverseThumbs.splice(0, target.comicverseThumbs.length - 30);
                }
                // Use backend-adjusted selected indices (backend already adjusted for deletions)
                if (Array.isArray(selected)) {
                    target.comicverseSelected = selected.slice(0, 6);
                } else {
                    target.comicverseSelected = [];
                }
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


