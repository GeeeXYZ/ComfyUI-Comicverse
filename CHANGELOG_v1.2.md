# ComicVerse v1.2.0 更新日志

**发布日期**: 2025-11-07

## 修改的文件

### Python 后端
1. **text_preview_node.py**
   - 添加 `RETURN_TYPES = ("STRING",)` 支持输出
   - 修改 `preview_text` 返回类型为 `Tuple[str, Dict[str, Any]]`
   - 同时返回输出数据和 UI 数据
   - 添加 `Tuple` 类型导入

### JavaScript 前端
1. **js/prompt_rolling.js**
   - 重构 `updateWeightWidgets` 函数，修复 widget 覆盖问题
   - 为每个 widget 显式设置 Y 坐标
   - 改进尺寸计算逻辑，基于实际内容动态计算
   - 实现 `minSize` 约束机制
   - 添加 `onResize` 钩子强制执行最小尺寸
   - 初始尺寸调整为 320x180

2. **js/text_preview.js**
   - 改进多行文本显示（6-25 行）
   - 优化 `computeSize` 函数，更精确的高度计算
   - 在 `onExecuted` 中实现自适应尺寸调整
   - 添加 `onResize` 钩子
   - 初始尺寸调整为 400x200
   - 改进 textarea 样式（禁用手动 resize，100% 宽度）

### 测试文件
1. **tests/test_prompt_nodes.py**
   - 添加 `TextPreviewNode` 导入
   - 新增 4 个测试函数：
     - `test_text_preview_basic`: 基础功能测试
     - `test_text_preview_multiline`: 多行文本测试
     - `test_text_preview_empty`: 空字符串测试
     - `test_text_preview_long_text`: 长文本测试

### 文档文件
1. **README.md**
   - 添加 v1.2.0 更新日志条目

2. **OPTIMIZATION_NOTES.md** (新建)
   - 详细的优化说明文档
   - 技术实现细节
   - 测试建议

3. **USAGE_GUIDE_v1.2.md** (新建)
   - 完整的使用指南
   - 工作流示例
   - 常见问题解答

4. **CHANGELOG_v1.2.md** (本文件)
   - 详细的更改记录

## 主要改进

### 1. Prompt Rolling 节点

#### 问题修复
- ✅ **关键修复**: Weight 控件不再相互覆盖（通过重新排序 widgets 数组）
- ✅ 所有控件按正确顺序显示（seed → weight_1 → weight_2 → ...）
- ✅ 节点大小自动适应内容
- ✅ 用户调整大小时强制执行最小尺寸

#### 技术改进
- **核心修复**: 重新排序 `node.widgets` 数组而不是设置 Y 坐标
  - LiteGraph 按数组顺序渲染 widgets，不使用 `widget.y` 属性
  - 每次更新时重建 widgets 数组：seed → 可见 weights → 隐藏 weights
- 动态计算内容高度
- 实现 `minSize` 约束
- 添加 `onResize` 钩子
- 详细的 bug 分析文档：`BUGFIX_WIDGET_ORDERING.md`

### 2. Text Preview 节点

#### 问题修复
- ✅ **关键修复**: 节点不可用问题（使用 ComfyUI 标准 widget 系统）
- ✅ **关键修复**: 真正的多行显示（使用 ComfyWidgets["STRING"]）

#### 新功能
- ✅ 新增 STRING 输出（可选连接）
- ✅ 支持将文本传递给下游节点
- ✅ 保持 OUTPUT_NODE 属性，不连接也能执行

#### 显示改进
- ✅ 使用 ComfyUI 原生 multiline STRING widget
- ✅ 自动调整节点大小以适应内容
- ✅ 等宽字体、半透明、自动换行
- ✅ 支持从保存的工作流中恢复显示

#### 技术改进
- **核心修复**: 使用 `beforeRegisterNodeDef` 而不是 `nodeCreated`
- **核心修复**: 使用 `ComfyWidgets["STRING"]` 创建标准 multiline widget
- 实现 `populate` 函数处理文本更新
- 添加 `onExecuted` 和 `onConfigure` 钩子
- 返回类型改为 `Tuple[str, Dict[str, Any]]`
- 参考 `comfyui-sixgod_prompt` 的成熟实现

## 测试覆盖

### 新增测试
- Text Preview 基础功能测试
- 多行文本处理测试
- 空字符串处理测试
- 长文本处理测试

### 测试运行
```bash
cd ComfyUI-Comicverse
pytest tests/test_prompt_nodes.py -v
```

## 兼容性

### 向后兼容
- ✅ 完全向后兼容 v1.1.0
- ✅ 现有工作流无需修改
- ✅ Text Preview 的输出是可选的
- ✅ 节点行为保持一致

### 破坏性变更
- ❌ 无破坏性变更

## 升级指南

### 从 v1.1.0 升级
1. 拉取最新代码或通过 ComfyUI Manager 更新
2. 重启 ComfyUI
3. 现有工作流自动适配，无需修改

### 新功能使用
1. **Prompt Rolling**: 无需操作，自动修复
2. **Text Preview 输出**: 可选连接到其他节点

## 已知问题

- 无已知问题

## 下一步计划

- [ ] 添加更多排版模板
- [ ] 实现对话气泡生成器
- [ ] 添加装饰文字功能
- [ ] 改进 Comic Assets Library 的批量操作

## 贡献者

- 主要开发: GeeeXYZ
- 优化和测试: AI Assistant

## 许可证

与主项目保持一致

---

**完整文档**: 
- [OPTIMIZATION_NOTES.md](OPTIMIZATION_NOTES.md) - 技术细节
- [USAGE_GUIDE_v1.2.md](USAGE_GUIDE_v1.2.md) - 使用指南
- [README.md](README.md) - 项目主文档

