# Prompt Library 示例文件

本目录包含了用于 Prompt Library Loader 节点的示例 JSON 文件。

## 文件列表

### Prompt 库文件

1. **camera_angles.json** - 摄像机角度
   - 包含 11 种常见的摄像机角度和视角
   - 例如：低角度、平视、俯视、鸟瞰等

2. **lighting.json** - 光照设置
   - 包含 12 种光照类型和氛围
   - 例如：柔光、硬光、边缘光、黄金时刻等

3. **composition.json** - 构图方式
   - 包含 12 种构图技巧
   - 例如：三分法则、黄金比例、引导线等

4. **style.json** - 艺术风格
   - 包含 15 种艺术和视觉风格
   - 例如：电影感、动漫风格、水彩画等

### 配置文件

- **example_config.json** - 示例配置模板
  - 展示如何配置多个 prompt 库文件
  - **需要修改路径为实际路径**

## 使用方法

### 步骤 1: 获取文件的绝对路径

**macOS/Linux**:
```bash
cd /path/to/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples
pwd
# 输出类似: /Users/yourname/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples
```

**Windows**:
```cmd
cd C:\path\to\ComfyUI\custom_nodes\ComfyUI-ComicVerse\examples
cd
# 输出类似: C:\path\to\ComfyUI\custom_nodes\ComfyUI-ComicVerse\examples
```

### 步骤 2: 修改配置文件

编辑 `example_config.json`，将路径替换为实际路径：

```json
[
  {
    "name": "camera_angles",
    "path": "/Users/yourname/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/camera_angles.json"
  },
  {
    "name": "lighting",
    "path": "/Users/yourname/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/lighting.json"
  }
]
```

或者使用波浪号（推荐）：

```json
[
  {
    "name": "camera_angles",
    "path": "~/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/camera_angles.json"
  }
]
```

### 步骤 3: 在 ComfyUI 中使用

1. 在 ComfyUI 中搜索 `comic` 或 `prompt loader`
2. 添加 **Prompt Library Loader** 节点
3. 将配置 JSON 复制到节点的输入框中
4. 连接到 **Prompt Rolling** 节点
5. 运行工作流

### 步骤 4: 预览结果

1. 搜索 `comic` 或 `text preview`
2. 添加 **Text Preview (Comic)** 节点
3. 连接 Prompt Rolling 的输出到 Text Preview
4. 查看生成的 prompt

## 快速开始示例

### 最简配置（单个文件）

```json
[
  {
    "name": "camera",
    "path": "~/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/camera_angles.json"
  }
]
```

### 完整配置（所有文件）

```json
[
  {
    "name": "camera_angles",
    "path": "~/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/camera_angles.json"
  },
  {
    "name": "lighting",
    "path": "~/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/lighting.json"
  },
  {
    "name": "composition",
    "path": "~/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/composition.json"
  },
  {
    "name": "style",
    "path": "~/ComfyUI/custom_nodes/ComfyUI-ComicVerse/examples/style.json"
  }
]
```

## 自定义 Prompt 库

### 创建自己的 JSON 文件

1. 创建一个新的 `.json` 文件
2. 使用以下格式之一：

**简单格式**（单个 prompt）:
```json
[
  "prompt 1",
  "prompt 2",
  "prompt 3"
]
```

**分组格式**（相关 prompt 组合）:
```json
[
  ["main prompt", "variation 1", "variation 2"],
  ["another prompt", "its variation"],
  ["third prompt"]
]
```

3. 保存文件并在配置中引用其路径

### 中文 Prompt 支持

完全支持中文和其他 Unicode 字符：

```json
[
  ["低角度", "仰视", "从下往上"],
  ["平视", "正面", "水平视角"],
  ["俯视", "从上往下", "高角度"]
]
```

## 常见问题

### Q: 路径中包含空格怎么办？
A: JSON 中路径用引号包裹，空格不影响：
```json
"path": "/Users/my name/my folder/file.json"
```

### Q: Windows 路径的反斜杠如何处理？
A: 使用双反斜杠或正斜杠：
```json
"path": "C:\\Users\\name\\prompts\\file.json"
或
"path": "C:/Users/name/prompts/file.json"
```

### Q: 如何验证 JSON 格式是否正确？
A: 使用在线工具如 jsonlint.com 或 VSCode 的 JSON 验证功能

### Q: 文件编码要求？
A: 必须使用 UTF-8 编码保存

## 工作流示例

```
Prompt Library Loader
  ↓ (library_json)
Prompt Rolling
  ↓ (prompt)
Text Preview  →  CLIP Text Encode  →  生成图像
```

## 进阶用法

### 多个 Loader 组合

可以创建多个 Prompt Library Loader 节点，分别加载不同类型的 prompt：

```
Loader 1 (camera + lighting)  →  Rolling 的 library_1
Loader 2 (style + mood)       →  Rolling 的 library_2
```

### 权重调整

在 Prompt Rolling 节点的前端界面中，可以为每个 prompt 组调整权重（0.0 - 2.0）

---

**提示**: 更多详细信息请参考 `PROMPT_LOADER_GUIDE.md`

