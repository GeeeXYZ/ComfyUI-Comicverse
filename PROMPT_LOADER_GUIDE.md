# Prompt Library Loader 使用指南

## 概述

Prompt Library Loader 节点用于从指定路径加载 JSON 格式的 prompt 库文件，支持多个文件同时加载。

## 节点说明

### 1. Prompt Library Loader (Comic)
- **分类**: `ComicVerse/Prompt`
- **搜索关键词**: `comic`, `prompt`, `loader`, `library`
- **功能**: 从 JSON 文件加载 prompt 库
- **输入**: 
  - `file_specs_json`: JSON 配置字符串（支持多行）
- **输出**: 
  - `library_json`: 解析后的 prompt 库数据
  - `summary`: 加载摘要信息

### 2. Prompt Rolling (Comic)
- **分类**: `ComicVerse/Prompt`
- **搜索关键词**: `comic`, `prompt`, `rolling`, `random`
- **功能**: 从 prompt 库中随机选择并组合 prompt
- **输入**: 
  - `library_1` ~ `library_8`: 最多 8 个 prompt 库输入
  - `weights_json`: 权重配置（隐藏参数）
  - `seed`: 随机种子（隐藏参数）
- **输出**: 
  - `prompt`: 格式化的 prompt 字符串
  - `details`: 详细的选择信息

### 3. Text Preview (Comic)
- **分类**: `ComicVerse/Utils`
- **搜索关键词**: `comic`, `text`, `preview`, `display`
- **功能**: 显示 STRING 类型的文本数据，无输出
- **输入**: 
  - `text`: 任何 STRING 类型的输入
- **输出**: 无（纯显示节点）

## JSON 文件格式

### 文件路径配置格式

在 Prompt Library Loader 节点的 `file_specs_json` 输入框中，输入以下格式的 JSON：

```json
[
  {
    "name": "camera",
    "path": "/absolute/path/to/camera.json"
  },
  {
    "name": "lighting",
    "path": "~/Documents/prompts/lighting.json"
  },
  {
    "name": "style",
    "path": "/Users/username/prompts/style.json"
  }
]
```

**字段说明**：
- `name`: prompt 组的名称（可选，默认使用文件名）
- `path`: JSON 文件的绝对路径或使用 `~` 的路径

### Prompt 库文件格式

每个 JSON 文件应该包含一个数组，数组中的每个元素是一个 prompt 组：

#### 格式 1: 简单字符串数组
```json
[
  "low angle",
  "eye level",
  "high angle",
  "bird's eye view",
  "dutch angle"
]
```

#### 格式 2: 嵌套数组（每组多个相关 prompt）
```json
[
  ["low angle", "from below"],
  ["eye level", "straight on"],
  ["high angle", "from above"],
  ["bird's eye view", "top down view"],
  ["dutch angle", "tilted frame"]
]
```

#### 格式 3: 换行分隔的 JSON 数组
```json
["soft light", "diffused lighting"]
["hard light", "dramatic shadows"]
["rim light", "backlit"]
["golden hour", "warm sunlight"]
```

## 使用示例

### 示例 1: 基础使用

1. **创建 prompt 文件**

创建 `/Users/yourname/prompts/camera.json`:
```json
[
  ["low angle", "from below"],
  ["eye level", "straight on"],
  ["high angle", "from above"]
]
```

创建 `/Users/yourname/prompts/lighting.json`:
```json
[
  ["soft light", "diffused"],
  ["hard light", "dramatic"],
  ["rim light", "backlit"]
]
```

2. **配置 Prompt Library Loader**

在节点的 `file_specs_json` 输入框中输入：
```json
[
  {
    "name": "camera_angles",
    "path": "/Users/yourname/prompts/camera.json"
  },
  {
    "name": "lighting_setup",
    "path": "/Users/yourname/prompts/lighting.json"
  }
]
```

3. **连接到 Prompt Rolling**

- 将 Loader 的 `library_json` 输出连接到 Rolling 的 `library_1` 输入
- 运行工作流，Rolling 会从每个库中随机选择一个 prompt 组合

4. **预览结果**

- 将 Rolling 的 `prompt` 输出连接到 Text Preview 节点
- 在 Text Preview 中查看生成的 prompt

### 示例 2: 多个库组合

```json
[
  {
    "name": "camera",
    "path": "/Users/yourname/prompts/camera.json"
  },
  {
    "name": "lighting",
    "path": "/Users/yourname/prompts/lighting.json"
  },
  {
    "name": "composition",
    "path": "/Users/yourname/prompts/composition.json"
  },
  {
    "name": "mood",
    "path": "/Users/yourname/prompts/mood.json"
  }
]
```

### 示例 3: 使用相对路径（波浪号展开）

```json
[
  {
    "name": "my_prompts",
    "path": "~/Documents/ComfyUI/prompts/custom.json"
  }
]
```

## 工作流示例

```
┌─────────────────────────┐
│ Prompt Library Loader   │
│ (加载 JSON 文件)         │
└───────┬─────────────────┘
        │ library_json
        │
        ├──────────────────────┐
        │                      │
        ▼                      ▼
┌───────────────┐      ┌──────────────┐
│ Text Preview  │      │ Prompt       │
│ (查看库内容)   │      │ Rolling      │
└───────────────┘      └──────┬───────┘
                              │ prompt
                              │
                              ▼
                       ┌──────────────┐
                       │ Text Preview │
                       │ (查看结果)    │
                       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ CLIP Text    │
                       │ Encode       │
                       └──────────────┘
```

## 常见问题

### Q1: 如何找到文件的绝对路径？

**macOS/Linux**:
```bash
cd /path/to/your/prompts
pwd
# 输出: /Users/yourname/prompts
```

**Windows**:
```cmd
cd C:\path\to\your\prompts
cd
# 输出: C:\path\to\your\prompts
```

### Q2: 支持哪些路径格式？

- ✅ 绝对路径: `/Users/name/prompts/file.json`
- ✅ 波浪号: `~/Documents/prompts/file.json`
- ❌ 相对路径: `./prompts/file.json` (不推荐)

### Q3: JSON 文件编码要求？

- 必须使用 UTF-8 编码
- 支持中文和其他 Unicode 字符
- 确保 JSON 格式正确（可以用在线工具验证）

### Q4: 如何调试加载失败？

1. 检查 ComfyUI 控制台的错误信息
2. 验证 JSON 文件格式是否正确
3. 确认文件路径是否存在
4. 检查文件读取权限

### Q5: Text Preview 节点不显示内容？

- 确保节点已连接到 STRING 输出
- 运行工作流后才会显示内容
- 检查上游节点是否正确执行

## 高级用法

### 权重控制

在 Prompt Rolling 节点中，可以通过前端界面调整每个 prompt 组的权重：

```json
{
  "0:0": 1.5,
  "0:1": 0.8,
  "input_0": 1.2
}
```

### 固定随机种子

设置 `seed` 参数可以获得可重复的结果：
- `-1`: 每次随机
- `>= 0`: 固定种子，每次相同

## 文件示例

### camera.json
```json
[
  ["low angle", "from below", "worm's eye view"],
  ["eye level", "straight on", "neutral angle"],
  ["high angle", "from above", "bird's eye view"],
  ["dutch angle", "tilted frame", "canted angle"],
  ["over the shoulder", "OTS shot"],
  ["close-up", "tight frame"],
  ["wide shot", "establishing shot"],
  ["medium shot", "waist up"]
]
```

### lighting.json
```json
[
  ["soft light", "diffused lighting", "gentle illumination"],
  ["hard light", "dramatic shadows", "high contrast"],
  ["rim light", "backlit", "edge lighting"],
  ["three-point lighting", "studio setup"],
  ["natural light", "window light", "ambient"],
  ["golden hour", "warm sunlight", "magic hour"],
  ["blue hour", "twilight", "cool tones"],
  ["low key", "dark mood", "minimal lighting"],
  ["high key", "bright", "overexposed look"]
]
```

### style.json
```json
[
  ["cinematic", "film look", "movie style"],
  ["anime style", "manga aesthetic"],
  ["comic book style", "graphic novel"],
  ["watercolor", "painted look"],
  ["photorealistic", "hyper-realistic"],
  ["minimalist", "simple", "clean"],
  ["detailed", "intricate", "complex"],
  ["vintage", "retro", "old-fashioned"]
]
```

## 总结

- ✅ 所有节点都可以通过搜索 `comic` 找到
- ✅ Prompt Library Loader 支持从指定路径加载 JSON
- ✅ Text Preview 可以显示任何 STRING 输出
- ✅ 支持多文件、多格式的 prompt 库
- ✅ 完整的工作流支持：加载 → 随机 → 预览 → 使用

---

**更新日期**: 2025-11-07  
**版本**: 1.0

