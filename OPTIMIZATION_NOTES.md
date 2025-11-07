# ComicVerse 节点优化说明

## 优化日期
2025-11-07

## 优化内容

### 1. Prompt Rolling 节点优化

#### 问题 1: Weight 控制显示覆盖问题
**问题描述**: 从 weight_3 开始会覆盖 weight_2，weight_4 覆盖 weight_3，导致控件显示混乱。

**根本原因分析**:
- LiteGraph 按照 `node.widgets` 数组的顺序渲染 widgets
- 设置 `widget.y` 属性**不起作用**（这是第一次尝试的错误方向）
- 隐藏的 widgets 仍然占据数组位置，但渲染时被跳过
- 当显示/隐藏 widgets 时，如果不重新排序数组，可见的 widgets 会按照它们在原始数组中的位置渲染，导致覆盖

**解决方案**:
- 重构 `updateWeightWidgets` 函数，**重新排序 `node.widgets` 数组**而不是设置 Y 坐标
- 收集所有 widgets（seed 和 weight_1 到 weight_8）
- 配置每个 widget 的可见性和属性
- **关键修复**: 创建新的 widgets 数组，按照正确的顺序排列：
  1. seed widget（始终在最前）
  2. 可见的 weight widgets（按 1, 2, 3... 顺序）
  3. 隐藏的 weight widgets（放在最后）
- 用重新排序的数组替换 `node.widgets`

**修改文件**: `js/prompt_rolling.js`

#### 问题 2: 节点自适应显示问题
**问题描述**: 节点面板大小不能正确适应内容变化，添加新输入时可能出现内容溢出。

**解决方案**:
- 改进尺寸计算逻辑，基于实际内容动态计算最小高度：
  ```javascript
  contentHeight = titleHeight + totalWidgetsHeight + totalInputsHeight + outputHeight + padding
  ```
- 实现 `minSize` 约束，确保节点始终大于内容尺寸
- 添加 `onResize` 钩子，在用户手动调整大小时强制执行最小尺寸限制
- 每次添加新输入时自动更新 `minSize[1]`（最小高度）

**修改文件**: `js/prompt_rolling.js`

**关键改进**:
- 初始尺寸从 `[300, 150]` 调整为 `[320, 180]`
- 最小宽度设为 320px
- 最小高度根据内容动态计算，基础值为 180px
- 添加 `onResize` 钩子确保用户调整时不会小于最小尺寸

### 2. Text Preview 节点优化

#### 问题 1: 缺少 STRING 输出，无法将预览内容传递给下游节点
#### 问题 2: 节点不可用且不是多行显示

**解决方案**:

**Python 后端修改** (`text_preview_node.py`):
- 添加 `RETURN_TYPES = ("STRING",)` 和 `RETURN_NAMES = ("text",)`
- 修改 `preview_text` 方法返回类型为 `Tuple[str, Dict[str, Any]]`
- 返回值同时包含：
  - 输出数据：`text` 字符串（可连接到其他节点）
  - UI 数据：`{"ui": {"text": [text]}}` 用于前端显示
- 添加 `Tuple` 类型导入

**JavaScript 前端重构** (`js/text_preview.js`):
- **重要修复**: 使用 `beforeRegisterNodeDef` 而不是 `nodeCreated`，确保节点正确注册
- **使用 ComfyWidgets**: 采用 ComfyUI 标准的 `ComfyWidgets["STRING"]` 创建多行文本框
  - 自动支持多行显示
  - 原生支持滚动和自适应
  - 与 ComfyUI 其他节点保持一致的外观和行为
- **实现 populate 函数**: 
  - 每次执行时重新创建显示 widget
  - 正确处理文本数组（从后端返回的格式）
  - 移除旧 widgets，避免内存泄漏
- **添加 onExecuted 钩子**: 在节点执行后更新显示
- **添加 onConfigure 钩子**: 从保存的工作流中恢复文本显示
- **自适应尺寸**: 使用 `requestAnimationFrame` 和 `computeSize()` 自动调整大小
- **样式优化**:
  - 只读模式（`readOnly = true`）
  - 等宽字体（`monospace`）
  - 半透明（`opacity: 0.85`）
  - 自动换行（`white-space: pre-wrap`）

**关键改进**:
- ✅ **修复节点不可用问题**: 使用正确的注册方式和 widget 系统
- ✅ **真正的多行显示**: 使用 ComfyUI 原生的 multiline STRING widget
- ✅ 支持 STRING 输出（可选连接）
- ✅ 保持 OUTPUT_NODE 属性，即使不连接下游也会执行
- ✅ 自动调整节点大小以适应内容
- ✅ 支持从保存的工作流中恢复显示
- ✅ 与 ComfyUI 生态系统完全兼容

**参考实现**: 
直接采用 `comfyui-sixgod_prompt` 的 `previewText.js` 实现（经过验证的成熟方案）

**最终实现细节**:
```javascript
// 1. 清理旧 widgets（保留第一个隐藏的输入 widget）
this.widgets.length = 1;

// 2. 处理文本数组（移除空的第一个元素）
const v = [...text];
if (!v[0]) v.shift();

// 3. 创建标准 multiline STRING widget
const w = ComfyWidgets["STRING"](this, "", ["STRING", { multiline: true }], app).widget;

// 4. 设置只读和样式
w.inputEl.readOnly = true;
w.inputEl.style.opacity = 0.6;
w.value = v.join("");

// 5. 自动调整大小（保持用户设置的尺寸）
requestAnimationFrame(() => {
    const sz = this.computeSize();
    if (sz[0] < this.size[0]) sz[0] = this.size[0];
    if (sz[1] < this.size[1]) sz[1] = this.size[1];
    this.onResize?.(sz);
    app.graph.setDirtyCanvas(true, false);
});
```

## 测试建议

### Prompt Rolling 节点测试
1. 创建节点，连接 1 个 Prompt Library Loader
2. 逐个添加更多 Loader（最多 8 个）
3. 验证每个 weight 控件按顺序显示，无覆盖
4. 验证节点高度随输入数量自动增长
5. 尝试手动调整节点大小，确保不会小于内容尺寸

### Text Preview 节点测试
1. 创建节点，连接任意 STRING 输出
2. 运行工作流，验证文本正确显示
3. 测试长文本（多行），验证自动调整大小
4. 将 Text Preview 的输出连接到其他节点（如 CLIP Text Encode）
5. 验证输出正确传递

## 技术细节

### Widget Y 坐标管理
ComfyUI 的 LiteGraph 使用 Y 坐标来定位 widgets。通过显式设置 `widget.y`，我们可以精确控制每个控件的位置，避免重叠。

### 最小尺寸约束
通过 `node.minSize` 数组和 `onResize` 钩子，我们确保节点始终足够大以显示所有内容。这在动态添加输入/控件时特别重要。

### OUTPUT_NODE 属性
Text Preview 保持 `OUTPUT_NODE = True`，这确保即使没有下游连接，节点也会执行。这对于纯预览功能很重要，同时现在也支持可选的输出连接。

## 兼容性
- 所有更改向后兼容
- 现有工作流无需修改即可使用新功能
- Text Preview 的输出是可选的，不连接也能正常工作

