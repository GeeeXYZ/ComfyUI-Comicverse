import { app } from "../../scripts/app.js";

const EXTENSION_NAME = "ComfyUI-ComicVerse.LibraryManager";
const API_ROOT = "/comicverse/libraries";

const API = {
    async request(path, options = {}) {
        const response = await fetch(`${API_ROOT}${path}`, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });

        const data = await response.json();
        if (!response.ok || data?.error) {
            throw new Error(data?.error || response.statusText);
        }
        return data;
    },

    list() {
        return this.request("/list", { method: "GET" });
    },

    read(name) {
        const query = new URLSearchParams({ name }).toString();
        return this.request(`/read?${query}`, { method: "GET" });
    },

    create(name) {
        return this.request("/create", {
            method: "POST",
            body: JSON.stringify({ name, content: "[]" }),
        });
    },

    save(name, content) {
        return this.request("/save", {
            method: "POST",
            body: JSON.stringify({ name, content }),
        });
    },

    rename(oldName, newName) {
        return this.request("/rename", {
            method: "POST",
            body: JSON.stringify({ old_name: oldName, new_name: newName }),
        });
    },

    delete(name) {
        return this.request("/delete", {
            method: "POST",
            body: JSON.stringify({ name }),
        });
    },
};

const state = {
    dialog: null,
    libraryList: [],
    currentLibrary: null,
    currentEntries: [],
    isSaving: false,
};

function formatEntryForInput(entry) {
    if (Array.isArray(entry)) {
        return entry.join("，");
    }
    return String(entry ?? "");
}

function parseInputLine(line) {
    if (!line) {
        return null;
    }
    const normalized = line.replace(/,/g, "，").trim();
    if (!normalized) {
        return null;
    }
    const parts = normalized.split("，").map((item) => item.trim()).filter(Boolean);
    if (parts.length === 0) {
        return null;
    }
    if (parts.length === 1) {
        return parts[0];
    }
    return parts;
}

function setStatus(message, tone = "info") {
    const statusEl = state.dialog?.querySelector("#cv-lm-status");
    if (!statusEl) {
        return;
    }
    const colors = {
        info: "var(--comfy-panel-text-muted, #9aa0a6)",
        success: "var(--comfy-success, #66bb6a)",
        warning: "var(--comfy-warning, #ffa726)",
        error: "var(--comfy-error, #ef5350)",
    };
    statusEl.textContent = message;
    statusEl.style.color = colors[tone] || colors.info;
    if (tone !== "info") {
        setTimeout(() => {
            statusEl.textContent = "准备就绪";
            statusEl.style.color = colors.info;
        }, 2500);
    }
}

async function refreshLibraryList() {
    try {
        const data = await API.list();
        state.libraryList = Array.isArray(data.libraries) ? data.libraries : [];
        renderLibraryList();
    } catch (error) {
        console.error(error);
        setStatus(error.message, "error");
    }
}

async function loadLibrary(name) {
    try {
        setStatus(`正在加载 ${name}...`, "info");
        const { data, name: resolvedName } = await API.read(name);
        state.currentLibrary = resolvedName || name;
        state.currentEntries = Array.isArray(data) ? data.slice() : [];
        renderLibraryList();
        renderEditor();
        setStatus(`已加载 ${state.currentLibrary}`, "success");
    } catch (error) {
        console.error(error);
        setStatus(error.message, "error");
    }
}

async function saveCurrentLibrary() {
    if (!state.currentLibrary) {
        return;
    }
    if (state.isSaving) {
        return;
    }
    state.isSaving = true;
    setStatus("正在保存...", "info");
    try {
        const payload = JSON.stringify(state.currentEntries, null, 2);
        await API.save(state.currentLibrary, payload);
        setStatus("保存成功", "success");
        await refreshLibraryList();
    } catch (error) {
        console.error(error);
        setStatus(`保存失败：${error.message}`, "error");
    } finally {
        state.isSaving = false;
    }
}

function handleEntryCommit(index, rawValue) {
    const existing = state.currentEntries[index];
    const parsed = parseInputLine(rawValue);

    if (parsed === null) {
        state.currentEntries.splice(index, 1);
    } else {
        const same =
            Array.isArray(parsed) && Array.isArray(existing)
                ? parsed.length === existing.length &&
                  parsed.every((value, idx) => value === existing[idx])
                : !Array.isArray(parsed) && !Array.isArray(existing) && parsed === existing;
        if (same) {
            return;
        }
        state.currentEntries[index] = parsed;
    }
    renderEditor();
    void saveCurrentLibrary();
}

function handleNewEntry(line) {
    const parsed = parseInputLine(line);
    if (parsed === null) {
        return;
    }
    state.currentEntries.push(parsed);
    renderEditor();
    void saveCurrentLibrary();
}

function handleDeleteEntry(index) {
    state.currentEntries.splice(index, 1);
    renderEditor();
    void saveCurrentLibrary();
}

async function handleCreateLibrary() {
    const rawName = prompt("输入新的库名称");
    if (!rawName) {
        return;
    }
    const name = rawName.trim();
    if (!name) {
        return;
    }
    try {
        await API.create(name);
        await refreshLibraryList();
        await loadLibrary(name);
        setStatus(`已创建 ${name}`, "success");
    } catch (error) {
        console.error(error);
        setStatus(error.message, "error");
        alert(error.message);
    }
}

async function handleRenameLibrary() {
    if (!state.currentLibrary) {
        return;
    }
    const nextName = prompt("重命名库", state.currentLibrary);
    if (!nextName) {
        return;
    }
    const trimmed = nextName.trim();
    if (!trimmed || trimmed === state.currentLibrary) {
        return;
    }
    try {
        await API.rename(state.currentLibrary, trimmed);
        await refreshLibraryList();
        await loadLibrary(trimmed);
        setStatus("重命名成功", "success");
    } catch (error) {
        console.error(error);
        setStatus(error.message, "error");
        alert(error.message);
    }
}

async function handleDeleteLibrary() {
    if (!state.currentLibrary) {
        return;
    }
    const confirmed = confirm(`确认删除「${state.currentLibrary}」？\n系统将自动创建备份文件。`);
    if (!confirmed) {
        return;
    }
    try {
        await API.delete(state.currentLibrary);
        state.currentLibrary = null;
        state.currentEntries = [];
        renderLibraryList();
        renderEditor();
        setStatus("库已删除", "success");
        await refreshLibraryList();
    } catch (error) {
        console.error(error);
        setStatus(error.message, "error");
        alert(error.message);
    }
}

function renderLibraryList() {
    const container = state.dialog?.querySelector("#cv-lm-library-list");
    if (!container) {
        return;
    }
    container.innerHTML = "";

    if (!state.libraryList.length) {
        const empty = document.createElement("div");
        empty.className = "cv-lm__empty";
        empty.textContent = "暂无库文件";
        container.appendChild(empty);
        return;
    }

    state.libraryList.forEach((item) => {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "cv-lm__list-item";
        if (item.name === state.currentLibrary) {
            row.classList.add("is-active");
        }
        row.innerHTML = `
            <span class="cv-lm__list-name">${item.name}</span>
            <span class="cv-lm__list-meta">${(item.size / 1024).toFixed(1)} KB</span>
        `;
        row.addEventListener("click", () => loadLibrary(item.name));
        container.appendChild(row);
    });
}

function renderEditor() {
    const headerName = state.dialog?.querySelector("#cv-lm-current-library");
    const renameBtn = state.dialog?.querySelector("#cv-lm-rename");
    const deleteBtn = state.dialog?.querySelector("#cv-lm-delete");
    const entryList = state.dialog?.querySelector("#cv-lm-entry-list");
    const addInput = state.dialog?.querySelector("#cv-lm-new-entry");

    if (!headerName || !renameBtn || !deleteBtn || !entryList || !addInput) {
        return;
    }

    if (!state.currentLibrary) {
        headerName.textContent = "未选择库";
        renameBtn.disabled = true;
        deleteBtn.disabled = true;
        entryList.innerHTML = `<div class="cv-lm__empty">请选择左侧的库文件以编辑内容</div>`;
        addInput.disabled = true;
        addInput.value = "";
        return;
    }

    headerName.textContent = state.currentLibrary;
    renameBtn.disabled = false;
    deleteBtn.disabled = false;
    addInput.disabled = false;
    addInput.value = "";

    entryList.innerHTML = "";

    if (!state.currentEntries.length) {
        entryList.innerHTML = `<div class="cv-lm__empty">暂无条目，可在上方输入框回车新建</div>`;
        return;
    }

    state.currentEntries.forEach((entry, index) => {
        const row = document.createElement("div");
        row.className = "cv-lm__entry";

        const indexTag = document.createElement("span");
        indexTag.className = "cv-lm__entry-index";
        indexTag.textContent = index + 1;

        const input = document.createElement("input");
        input.type = "text";
        input.className = "cv-lm__entry-input";
        input.value = formatEntryForInput(entry);
        input.placeholder = "关键词按「，」分隔";

        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleEntryCommit(index, input.value);
            } else if (event.key === "Delete" && event.ctrlKey) {
                event.preventDefault();
                handleDeleteEntry(index);
            }
        });

        input.addEventListener("blur", () => {
            handleEntryCommit(index, input.value);
        });

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "cv-lm__entry-delete";
        removeBtn.title = "移除该条目";
        removeBtn.textContent = "✕";
        removeBtn.addEventListener("click", () => handleDeleteEntry(index));

        row.appendChild(indexTag);
        row.appendChild(input);
        row.appendChild(removeBtn);
        entryList.appendChild(row);
    });
}

function buildDialog() {
    const dialog = document.createElement("dialog");
    dialog.id = "comicverse-library-manager";
    dialog.className = "cv-lm";
    dialog.innerHTML = `
        <style>
            .cv-lm {
                width: min(960px, 90vw);
                height: min(720px, 85vh);
                border: none;
                border-radius: 16px;
                padding: 0;
                background: var(--comfy-menu-bg, #262b34);
                color: var(--comfy-panel-text, #e0e5f1);
                box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
                overflow: hidden;
            }
            .cv-lm__shell {
                display: grid;
                grid-template-columns: 260px 1fr;
                height: 100%;
                min-height: 0;
            }
            .cv-lm__sidebar {
                background: var(--comfy-panel-bg-alt, #1f232b);
                border-right: 1px solid var(--comfy-border-color, rgba(255, 255, 255, 0.06));
                padding: 24px 16px;
                display: flex;
                flex-direction: column;
                gap: 16px;
                min-height: 0;
            }
            .cv-lm__title {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .cv-lm__title h2 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
                letter-spacing: 0.05em;
            }
            .cv-lm__title p {
                margin: 0;
                font-size: 12px;
                color: var(--comfy-panel-text-muted, #9aa0a6);
            }
            .cv-lm__list {
                flex: 1;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-height: 0;
            }
            .cv-lm__list::-webkit-scrollbar {
                width: 6px;
            }
            .cv-lm__list::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }
            .cv-lm__list-item {
                all: unset;
                padding: 12px;
                border-radius: 10px;
                border: 1px solid transparent;
                background: rgba(255, 255, 255, 0.02);
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: background 0.2s ease, border-color 0.2s ease;
                font-size: 13px;
            }
            .cv-lm__list-item:hover,
            .cv-lm__list-item:focus {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.08);
            }
            .cv-lm__list-item.is-active {
                border-color: rgba(104, 210, 255, 0.7);
                background: rgba(104, 210, 255, 0.12);
            }
            .cv-lm__list-name {
                font-weight: 600;
            }
            .cv-lm__list-meta {
                font-size: 11px;
                color: var(--comfy-panel-text-muted, #9aa0a6);
            }
            .cv-lm__primary {
                background: var(--comfy-menu-bg, #262b34);
                padding: 24px 28px;
                display: flex;
                flex-direction: column;
                gap: 18px;
                min-height: 0;
            }
            .cv-lm__header {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .cv-lm__header-title {
                font-size: 14px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--comfy-panel-text-muted, #9aa0a6);
            }
            .cv-lm__header-name {
                font-size: 20px;
                font-weight: 600;
            }
            .cv-lm__header-actions {
                margin-left: auto;
                display: flex;
                gap: 8px;
                align-items: center;
            }
            .cv-lm__button {
                all: unset;
                cursor: pointer;
                border-radius: 999px;
                padding: 6px 14px;
                font-size: 12px;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                transition: background 0.2s ease, border-color 0.2s ease;
            }
            .cv-lm__button:hover,
            .cv-lm__button:focus {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.15);
            }
            .cv-lm__button--primary {
                background: rgba(104, 210, 255, 0.18);
                border-color: rgba(104, 210, 255, 0.4);
                color: #b7ecff;
            }
            .cv-lm__button--primary:hover,
            .cv-lm__button--primary:focus {
                background: rgba(104, 210, 255, 0.28);
            }
            .cv-lm__entries {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 12px;
                overflow: hidden;
                min-height: 0;
            }
            .cv-lm__add {
                display: flex;
                align-items: center;
                gap: 12px;
                padding-bottom: 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
            .cv-lm__add > input {
                flex: 1;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                background: rgba(255, 255, 255, 0.06);
                color: inherit;
                font-size: 14px;
                transition: background 0.2s ease;
            }
            .cv-lm__add > input:focus {
                outline: none;
                background: rgba(255, 255, 255, 0.1);
            }
            .cv-lm__entry-list {
                flex: 1;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 8px;
                padding-right: 6px;
                min-height: 0;
            }
            .cv-lm__entry-list::-webkit-scrollbar {
                width: 6px;
            }
            .cv-lm__entry-list::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.12);
                border-radius: 3px;
            }
            .cv-lm__entry {
                display: grid;
                grid-template-columns: 36px 1fr auto;
                gap: 12px;
                align-items: center;
                padding: 10px 14px;
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
            }
            .cv-lm__entry-index {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 32px;
                height: 32px;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.08);
                font-size: 13px;
                font-weight: 600;
            }
            .cv-lm__entry-input {
                border: none;
                background: transparent;
                color: inherit;
                font-size: 14px;
                padding: 0;
            }
            .cv-lm__entry-input:focus {
                outline: none;
            }
            .cv-lm__entry-delete {
                all: unset;
                cursor: pointer;
                font-size: 16px;
                padding: 4px 8px;
                color: rgba(255, 255, 255, 0.5);
                border-radius: 8px;
            }
            .cv-lm__entry-delete:hover,
            .cv-lm__entry-delete:focus {
                color: rgba(255, 255, 255, 0.9);
                background: rgba(255, 255, 255, 0.06);
            }
            .cv-lm__empty {
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--comfy-panel-text-muted, #9aa0a6);
                font-size: 13px;
                padding: 24px;
                text-align: center;
            }
            .cv-lm__footer {
                font-size: 12px;
                color: var(--comfy-panel-text-muted, #9aa0a6);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .cv-lm__close {
                all: unset;
                cursor: pointer;
                font-size: 18px;
                color: rgba(255, 255, 255, 0.55);
                line-height: 1;
                padding: 4px 6px;
                border-radius: 999px;
                transition: background 0.2s ease, color 0.2s ease;
            }
            .cv-lm__close:hover,
            .cv-lm__close:focus {
                color: rgba(255, 255, 255, 0.95);
                background: rgba(255, 255, 255, 0.08);
            }
        </style>
        <div class="cv-lm__shell">
            <aside class="cv-lm__sidebar">
                <div class="cv-lm__title">
                    <h2>Prompt Library</h2>
                    <p>集中管理 ComicVerse 提示词库</p>
                </div>
                <button type="button" class="cv-lm__button cv-lm__button--primary" id="cv-lm-create">
                    新建库文件
                </button>
                <div class="cv-lm__list" id="cv-lm-library-list"></div>
            </aside>
            <section class="cv-lm__primary">
                <div class="cv-lm__header">
                    <span class="cv-lm__header-title">当前编辑</span>
                    <span class="cv-lm__header-name" id="cv-lm-current-library">未选择库</span>
                    <div class="cv-lm__header-actions">
                        <button type="button" class="cv-lm__button" id="cv-lm-rename" disabled>重命名</button>
                        <button type="button" class="cv-lm__button" id="cv-lm-delete" disabled>删除</button>
                        <button type="button" class="cv-lm__close" id="cv-lm-close" title="关闭">✕</button>
                    </div>
                </div>
                <div class="cv-lm__entries">
                    <div class="cv-lm__add">
                        <span class="cv-lm__entry-index">+</span>
                        <input id="cv-lm-new-entry" type="text" placeholder="输入关键词，使用「，」分隔，按回车快速添加" disabled />
                    </div>
                    <div class="cv-lm__entry-list" id="cv-lm-entry-list"></div>
                </div>
                <div class="cv-lm__footer">
                    <span id="cv-lm-status">准备就绪</span>
                </div>
            </section>
        </div>
    `;
    return dialog;
}

async function openLibraryManager() {
    if (state.dialog) {
        state.dialog.close();
        state.dialog.remove();
        state.dialog = null;
    }

    state.dialog = buildDialog();
    document.body.appendChild(state.dialog);
    state.dialog.showModal();

    const teardown = () => {
        if (!state.dialog) {
            return;
        }
        state.dialog.close();
        state.dialog.remove();
        state.dialog = null;
    };

    state.dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        teardown();
    });

    state.dialog.addEventListener("click", (event) => {
        const shell = state.dialog?.querySelector(".cv-lm__shell");
        if (shell && !shell.contains(event.target)) {
            teardown();
        }
    });

    const closeBtn = state.dialog.querySelector("#cv-lm-close");
    const createBtn = state.dialog.querySelector("#cv-lm-create");
    const renameBtn = state.dialog.querySelector("#cv-lm-rename");
    const deleteBtn = state.dialog.querySelector("#cv-lm-delete");
    const addInput = state.dialog.querySelector("#cv-lm-new-entry");

    closeBtn?.addEventListener("click", teardown);

    createBtn?.addEventListener("click", handleCreateLibrary);
    renameBtn?.addEventListener("click", handleRenameLibrary);
    deleteBtn?.addEventListener("click", handleDeleteLibrary);

    addInput?.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            handleNewEntry(addInput.value);
            addInput.value = "";
        }
    });

    await refreshLibraryList();
}

app.registerExtension({
    name: EXTENSION_NAME,
    async nodeCreated(node) {
        if (node.comfyClass !== "LibraryManagerNode") {
            return;
        }
        node.addWidget("button", "Manage Libraries", null, () => openLibraryManager());
        node.setSize([240, 64]);
    },
});
