# ComicVerse Nodes for ComfyUI

ComicVerse 节点库提供了一套完整的漫画量产工具(开发中)。

## 功能特性

- **素材管理**：支持多图片输入，提供预览、勾选和删除功能
- **待删除标记**：标记待删除图片，运行工作流时自动删除
- **模板排版**：内置多种排版模板（横版、竖版、经典4格等）
- **灵活布局**：支持自动排版和手动拖拽调整（待实现）
- **对话气泡**：多种样式的气泡（圆形、尖角、云状）
- **装饰文字**：支持多种字体样式的装饰文字和拟声词
- **库管理工具**：可视化编辑提示词库，支持增删改查操作 ✨NEW

## 节点列表

### 1. Comic Assets Library（漫画素材库节点）✅

**功能**：
- 接收最多 2 个 IMAGE 输入（支持批量图片）
- 自动暂存并去重（SHA256 哈希）
- 显示缩略图预览（最多 200 张）
- 点击缩略图选择/取消选择（最多 6 张）
- **删除功能**：
  - 点击缩略图右上角 ❌ 标记待删除
  - 点击 "Delete All" 标记所有图片待删除
  - 运行工作流时自动删除标记的图片
  - 删除后缩略图区域自动更新

**输入**：
- `output_count`：输出图片数量（1-6）
- `selected_indices`：选中索引（如 "2,0,1"）
- `pending_deletions`：待删除索引（自动填充）
- `image_input_a`、`image_input_b`：图片输入

**输出**：
- `image_1` ~ `image_6`：选中的图片
- `selected_count`：选中数量

### 2. Layout Template Selector（排版模板选择节点）✅

提供预设排版模板，配置基础布局参数。

**模板类型**：
- 2横版
- 2竖版
- 4格经典
- 3格斜切
- 自由网格

### 3. Prompt Library Loader（提示词库加载节点）✅

**功能**：

- 读取一个或多个 JSON 提示词文件，并输出标准化的提示词库数据
- 自动缓存文件内容，文件改动后自动刷新
- 生成摘要信息，快速确认每个文件的提示词数量
- 节点界面支持添加 / 编辑 / 删除文件路径，并显示最近一次运行的摘要

**输入**：

- `file_specs_json`：JSON 数组，例如：

  ```json
  [
    {"name": "camera", "path": "/data/prompts/camera.json"},
    {"name": "lighting", "path": "/data/prompts/lighting.json"}
  ]
  ```

  - `name` 可选，默认为文件名
  - `path` 支持绝对或相对路径，读取 UTF-8 JSON

**输出**：

- `library_json`：包含所有分组的 JSON 字符串
- `summary`：人类可读的分组统计信息

**提示词文件格式**：

- 标准 JSON：

  ```json
  [
    ["low angle", "medium distance"],
    ["fish-eye", "18mm"]
  ]
  ```

- 逐行 JSON 数组（每行一个分组）：

  ```
  ["low angle", "medium distance"]
  ["fish-eye", "18mm"]
  ```

### 4. Prompt Rolling（提示词滚动组合节点）✅

**功能**：

- 连接 1~8 个 Prompt Library Loader 输出
- 每次运行从每个分组随机抽取一组提示词
- 支持为每个输入分组设置权重（默认 1.0）
- 可选指定随机种子，便于复现
- 节点界面自动增加输入端、提供权重调节控件，并显示最近一次的组合结果

**输入**：

- `library_1` ~ `library_8`：来自 Loader 的 `library_json`
- `weights_json`（隐藏）：键值对，例如 `{ "input_0": 1.3, "camera": 1.1 }`
- `seed`（隐藏）：-1 表示随机，否则使用固定整数种子

**输出**：

- `prompt`：组合后的提示词字符串，如 `(low angle, medium distance:1.30), cinematic lighting`
- `details`：JSON 字符串，包含随机种子与每个分组的抽取详情

### 5. Text Preview (Comic)（文本预览节点）✅

**功能**：
- 显示任何 STRING 类型的输入内容
- 无输出，纯显示节点
- 用于调试和查看文本数据
- 自动在工作流执行后更新显示

**输入**：
- `text`：任何 STRING 输出（必须连接）

**输出**：无

**用途**：
- 查看 Prompt Library Loader 的输出
- 预览 Prompt Rolling 生成的 prompt
- 调试任何文本数据流

### 6. Library Manager（提示词库管理节点）✅ ✨NEW

**功能**：
- 可视化管理提示词库 JSON 文件
- 创建、编辑、重命名、删除库文件
- 内置 JSON 编辑器和验证
- 自动备份功能

**操作**：
- 点击节点上的 **"Manage Libraries"** 按钮打开管理界面
- 左侧列表显示所有可用的库
- 右侧编辑器用于编辑 JSON 内容
- 支持完整的增删改查操作

**特性**：
- ✅ 列出所有库文件
- ✅ 创建新库（初始为空数组）
- ✅ 编辑库内容（JSON 格式）
- ✅ 保存修改（自动创建 .backup 备份）
- ✅ 重命名库文件
- ✅ 删除库（自动创建 .deleted 备份）
- ✅ JSON 格式验证

**详细文档**：参见 [LIBRARY_MANAGER_GUIDE.md](LIBRARY_MANAGER_GUIDE.md)

### 7+. 其他节点（规划中）

- Basic Layout Composer（布局生成）
- Speech Bubble Generator（对话气泡）
- Decorative Text Adder（装饰文字）

## 安装方法

### 方法 1：通过 GitHub 链接安装（推荐）

1. 在 ComfyUI 主界面，点击 **"Manager"** → **"Custom Nodes"**
2. 点击 **"Install from URL"**
3. 输入：
   ```
   https://github.com/GeeeXYZ/ComfyUI-Comicverse
   ```
4. 点击 **"Install"**
5. 重启 ComfyUI

### 方法 2：手动安装

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/GeeeXYZ/ComfyUI-Comicverse.git
```

## 使用示例

### 基本工作流

#### 素材管理工作流
1. **添加素材**：连接图片到 Comic Assets Library 的 `image_input_a` 和 `image_input_b`
2. **选择图片**：点击缩略图勾选要输出的图片
3. **设置数量**：调整 `output_count`，点击 "Set output count"
4. **删除图片**：点击缩略图右上角 ❌ 标记待删除，运行工作流生效
5. **使用模板**：连接 Layout Template Selector 选择排版模板

#### Prompt 工作流
1. **加载提示词库**：
   - 在 ComfyUI 中搜索 `comic` 或 `prompt loader`
   - 添加 Prompt Library Loader 节点
   - 在输入框中配置 JSON 文件路径（参考 `examples/` 目录）
   - 运行查看摘要

2. **预览库内容**：
   - 搜索 `comic` 或 `text preview`
   - 添加 Text Preview 节点
   - 连接 Loader 的 `library_json` 输出到 Text Preview
   - 查看加载的内容

3. **随机组合提示词**：
   - 添加 Prompt Rolling 节点
   - 连接 Loader 的 `library_json` 到 Rolling 的 `library_1`
   - 可选：添加更多 Loader 到 `library_2` ~ `library_8`
   - 运行工作流获取随机组合

4. **查看结果**：
   - 连接 Rolling 的 `prompt` 输出到 Text Preview
   - 或直接连接到 CLIP Text Encode 用于图像生成

**完整工作流示例**：
```
Prompt Library Loader → Text Preview (查看库内容)
         ↓
Prompt Rolling → Text Preview (查看生成的 prompt)
         ↓
CLIP Text Encode → 图像生成
```

## 技术特点

- **持久化缓存**：图片缓存跨工作流运行持久保存
- **去重机制**：基于 SHA256 哈希自动去重
- **延迟删除**：标记删除，运行工作流时执行
- **动态 UI**：缩略图区域随图片数量自适应调整
- **提示词管线**：从本地 JSON 库加载、随机抽取并加权输出提示词
- **搜索友好**：所有节点都使用 `ComicVerse` 分类，搜索 `comic` 即可找到
- **文本预览**：Text Preview 节点方便调试和查看文本数据流

## 提示词 JSON 规范

- 顶层为数组
- 每个元素可以是：
  - 字符串（视为单独一条提示词）
  - 字符串数组（视为一组需要同时输出的提示词）
- 空字符串会被忽略

示例：

```json
[
  ["close-up", "portrait"],
  "bokeh",
  ["wide shot", "landscape"]
]
```

## 测试

项目包含基础单元测试，验证提示词解析与随机组合逻辑：

```bash
cd ComfyUI-ComicVerse
pytest -q
```

> 如未安装 pytest，可执行 `pip install pytest`。

## 更多文档

- **[PROMPT_LOADER_GUIDE.md](PROMPT_LOADER_GUIDE.md)** - Prompt Loader 和 Rolling 详细使用指南
- **[examples/README.md](examples/README.md)** - 示例 JSON 文件说明
- **[BUGFIX_ANALYSIS.md](BUGFIX_ANALYSIS.md)** - Comic Library 索引问题修复分析

## 开发文档

详见项目仓库的 commit history 和代码注释。

## 更新日志

### v1.2.0 (2025-11-07)
- ✅ **重要修复**: Prompt Rolling 节点 weight 控件显示覆盖问题（通过重新排序 widgets 数组）
- ✅ 改进 Prompt Rolling 节点自适应尺寸，确保面板始终大于内容
- ✅ **重要修复**: Text Preview 节点不可用问题（使用 ComfyUI 标准 widget 系统）
- ✅ Text Preview 节点新增 STRING 输出（可选连接）
- ✅ 改进 Text Preview 真正的多行文本显示
- ✅ 两个节点均支持自动调整大小和最小尺寸约束
- ✅ 添加完整的单元测试覆盖新功能
- ✅ 添加详细的 bug 修复文档（BUGFIX_WIDGET_ORDERING.md）

### v1.1.0 (2025-11-07)
- ✅ 新增 Text Preview (Comic) 节点
- ✅ 修复 Comic Library 图片选择不一致问题
- ✅ 改进 Prompt Library Loader 支持多行输入
- ✅ 所有节点支持通过 `comic` 关键词搜索
- ✅ 添加完整的示例 JSON 文件和使用指南

### v1.0.0
- ✅ Comic Assets Library 节点
- ✅ Layout Template Selector 节点
- ✅ Prompt Library Loader 节点
- ✅ Prompt Rolling 节点
- ✅ Prompt Strength Slider 节点
