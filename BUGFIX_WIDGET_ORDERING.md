# Widget 覆盖问题修复说明

## Bug 描述

在 Prompt Rolling 节点中，当连接多个 library 输入时，weight 控件出现覆盖现象：
- 连接 library_1: ✅ 显示 seed, weight_1
- 连接 library_2: ✅ 显示 seed, weight_1, weight_2
- 连接 library_3: ❌ weight_3 覆盖 weight_2 的位置
- 连接 library_4: ❌ weight_4 覆盖 weight_3 的位置

## 根本原因

### LiteGraph Widget 渲染机制

LiteGraph（ComfyUI 使用的图形库）渲染 widgets 的方式：

```javascript
// LiteGraph 内部渲染逻辑（简化版）
for (let i = 0; i < node.widgets.length; i++) {
    const widget = node.widgets[i];
    if (widget.hidden) continue;  // 跳过隐藏的 widget
    
    // 按照数组顺序渲染，不使用 widget.y
    renderWidget(widget, currentY);
    currentY += widget.height;
}
```

**关键点**:
1. LiteGraph **按照 `node.widgets` 数组的顺序**渲染 widgets
2. `widget.y` 属性**不起作用**
3. 隐藏的 widgets（`widget.hidden = true`）会被跳过，但仍占据数组位置

### 为什么会覆盖

假设初始 widgets 数组顺序为：`[seed, weight_1, weight_2, weight_3, ...]`

**场景 1: 只连接 library_1**
```javascript
widgets 数组: [seed, weight_1, weight_2(hidden), weight_3(hidden), ...]
渲染顺序: seed → weight_1 ✅
```

**场景 2: 连接 library_1 和 library_2**
```javascript
widgets 数组: [seed, weight_1, weight_2, weight_3(hidden), ...]
渲染顺序: seed → weight_1 → weight_2 ✅
```

**场景 3: 连接 library_1, library_2, library_3（问题出现）**

如果 widgets 数组顺序混乱（例如由于之前的隐藏/显示操作）：
```javascript
widgets 数组: [seed, weight_1, weight_3, weight_2, ...]
                                  ↑ 错误位置
渲染顺序: seed → weight_1 → weight_3 → weight_2
实际显示:  seed    weight_1   weight_3  weight_2
位置:      Y=0     Y=30       Y=60      Y=90
                              ↑ weight_3 显示在 weight_2 应该在的位置
```

## 错误的修复尝试

### 第一次尝试：设置 widget.y 坐标

```javascript
// ❌ 这个方法不起作用
widget.y = currentY;
currentY += widget.height;
```

**为什么失败**: LiteGraph 不使用 `widget.y` 来定位 widgets，而是按照数组顺序渲染。

## 正确的修复方案

### 重新排序 widgets 数组

```javascript
const updateWeightWidgets = (connectedCount) => {
    // 1. 收集所有 widgets
    const seedWidget = node.widgets.find(w => w.name === "seed");
    const weightWidgets = [];
    for (let i = 1; i <= MAX_INPUTS; i++) {
        const widget = node.widgets.find(w => w.name === `weight_${i}`);
        if (widget) weightWidgets.push({ index: i, widget });
    }

    // 2. 配置可见性
    for (const { index, widget } of weightWidgets) {
        const shouldShow = index <= connectedCount;
        widget.hidden = !shouldShow;
        // ... 其他配置
    }

    // 3. ✅ 关键修复：重新排序数组
    const newWidgetsOrder = [];
    
    // 添加 seed（始终在最前）
    if (seedWidget) newWidgetsOrder.push(seedWidget);
    
    // 添加可见的 weights（按顺序 1, 2, 3...）
    for (let i = 1; i <= MAX_INPUTS; i++) {
        const widget = weightWidgets.find(w => w.index === i)?.widget;
        if (widget && !widget.hidden) {
            newWidgetsOrder.push(widget);
        }
    }
    
    // 添加隐藏的 weights（放在最后）
    for (let i = 1; i <= MAX_INPUTS; i++) {
        const widget = weightWidgets.find(w => w.index === i)?.widget;
        if (widget && widget.hidden) {
            newWidgetsOrder.push(widget);
        }
    }
    
    // 4. 替换原数组
    node.widgets = newWidgetsOrder;
};
```

### 修复后的效果

**连接 library_1, library_2, library_3**:
```javascript
widgets 数组: [seed, weight_1, weight_2, weight_3, weight_4(hidden), ...]
                                                    ↑ 正确顺序
渲染顺序: seed → weight_1 → weight_2 → weight_3 ✅
实际显示:  seed    weight_1   weight_2   weight_3
位置:      Y=0     Y=30       Y=60       Y=90
```

## 技术要点

### 1. 数组顺序决定渲染顺序
```javascript
// LiteGraph 渲染逻辑
node.widgets.forEach(widget => {
    if (!widget.hidden) render(widget);
});
```

### 2. 隐藏 vs 移除
- **隐藏** (`widget.hidden = true`): widget 仍在数组中，但不渲染
- **移除** (`node.widgets.splice(i, 1)`): widget 从数组中删除

我们使用隐藏而不是移除，因为：
- 保留 widget 状态（值、配置等）
- 避免重新创建 widget 的开销
- 但必须正确排序数组

### 3. 为什么要把隐藏的 widgets 放在最后
```javascript
// ✅ 正确：隐藏的在最后
[seed, weight_1, weight_2, weight_3(hidden), weight_4(hidden)]

// ❌ 错误：隐藏的在中间
[seed, weight_1, weight_3(hidden), weight_2, weight_4(hidden)]
//                ↑ 这会导致后续的 weight_2 渲染位置错误
```

## 测试验证

### 测试步骤
1. 创建 Prompt Rolling 节点
2. 连接 library_1，验证显示：seed, weight_1
3. 连接 library_2，验证显示：seed, weight_1, weight_2
4. 连接 library_3，验证显示：seed, weight_1, weight_2, weight_3（不覆盖）
5. 连接 library_4 到 library_8，验证所有 weights 按顺序显示
6. 断开 library_3，验证 weight_3 消失，weight_4 保持正确位置
7. 重新连接 library_3，验证 weight_3 重新出现在正确位置

### 预期结果
- ✅ 所有 weight 控件按顺序显示（1, 2, 3, ...）
- ✅ 没有覆盖现象
- ✅ 动态添加/删除输入时，控件位置正确
- ✅ 节点大小自动调整以适应所有可见控件

## 相关文件

- `js/prompt_rolling.js` - 修复的文件
- `OPTIMIZATION_NOTES.md` - 优化说明
- `CHANGELOG_v1.2.md` - 更新日志

## 经验教训

1. **理解底层渲染机制**: 不要假设 UI 框架的行为，要查看实际的渲染逻辑
2. **数组顺序很重要**: 在动态 UI 中，数据结构的顺序往往决定显示顺序
3. **测试边界情况**: 不仅要测试正常流程，还要测试添加/删除/重新添加等操作
4. **参考成熟实现**: 查看其他成功的 ComfyUI 自定义节点如何处理类似问题

## 参考资料

- LiteGraph.js 文档: https://github.com/jagenjo/litegraph.js
- ComfyUI 自定义节点开发指南
- `comfyui-sixgod_prompt` 的实现（参考了其 widget 管理方式）

