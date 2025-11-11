# Library Manager 使用指南

## 概述

Library Manager 是一个用于管理 ComicVerse 提示词库的可视化工具。它提供了一个友好的界面来创建、编辑、重命名和删除提示词库文件。

## 功能特性

- ✅ **列出所有库**：显示 `library/` 目录下的所有 JSON 文件
- ✅ **创建新库**：创建新的提示词库文件
- ✅ **编辑库内容**：使用内置编辑器修改 JSON 内容
- ✅ **保存修改**：保存编辑后的内容（自动创建备份）
- ✅ **重命名库**：重命名现有的库文件
- ✅ **删除库**：删除库文件（自动创建备份）
- ✅ **JSON 验证**：保存前自动验证 JSON 格式

## 使用方法

### 1. 添加 Library Manager 节点

1. 在 ComfyUI 中搜索 `library manager` 或 `comicverse`
2. 添加 **Library Manager | ComicVerse** 节点到工作流
3. 点击节点上的 **"Manage Libraries"** 按钮

### 2. 界面说明

弹出的管理界面分为三个部分：

#### 顶部工具栏
- **+ New Library**：创建新的库文件
- **Save**：保存当前编辑的内容
- **Refresh**：刷新库列表
- **状态提示**：显示当前操作状态

#### 左侧面板
- 显示所有可用的库文件
- 点击库名称可以加载其内容到编辑器
- 当前选中的库会高亮显示

#### 右侧编辑器
- **Editing**：显示当前编辑的库名称
- **Rename**：重命名当前库
- **Delete**：删除当前库
- **文本编辑器**：编辑 JSON 内容
- **提示信息**：显示 JSON 格式要求

### 3. 创建新库

1. 点击 **"+ New Library"** 按钮
2. 在弹出的对话框中输入库名称（例如：`emotions`）
3. 点击确定
4. 新库会自动加载到编辑器中，初始内容为空数组 `[]`
5. 编辑内容并点击 **"Save"** 保存

### 4. 编辑现有库

1. 在左侧列表中点击要编辑的库
2. 库的内容会加载到右侧编辑器
3. 修改 JSON 内容
4. 点击 **"Save"** 保存修改
5. 保存前会自动创建备份文件（`.backup` 后缀）

### 5. 重命名库

1. 在左侧列表中点击要重命名的库
2. 点击 **"Rename"** 按钮
3. 在弹出的对话框中输入新名称
4. 点击确定完成重命名

### 6. 删除库

1. 在左侧列表中点击要删除的库
2. 点击 **"Delete"** 按钮
3. 确认删除操作
4. 文件会被删除，同时创建备份（`.deleted` 后缀）

## JSON 格式要求

库文件必须是一个 JSON 数组，每个元素可以是：

### 格式 1：字符串数组（推荐）

```json
[
  ["happy", "joyful", "cheerful"],
  ["sad", "melancholy", "gloomy"],
  ["angry", "furious", "enraged"]
]
```

每个子数组代表一组相关的提示词变体。

### 格式 2：单个字符串

```json
[
  "happy",
  "sad",
  "angry"
]
```

每个字符串代表一个独立的提示词。

### 格式 3：混合格式

```json
[
  ["happy", "joyful"],
  "neutral",
  ["sad", "melancholy", "gloomy"]
]
```

可以混合使用字符串和数组。

## 注意事项

### 文件命名规则
- 只能使用字母、数字、空格、连字符和下划线
- 不要包含特殊字符或路径分隔符
- 文件名会自动添加 `.json` 扩展名

### 保存和备份
- 每次保存前会自动创建 `.backup` 备份文件
- 删除文件时会创建 `.deleted` 备份文件
- 备份文件保存在同一目录下

### JSON 验证
- 保存前会自动验证 JSON 格式
- 必须是有效的 JSON 数组
- 如果格式错误，会显示错误信息并阻止保存

### 未保存的修改
- 编辑内容后状态栏会显示 "Unsaved changes"
- 切换到其他库或关闭对话框时会提示保存
- 点击 "Save" 按钮保存修改

## 工作流集成

Library Manager 创建或修改的库文件可以直接在其他节点中使用：

1. **Prompt Library Loader**：加载库文件
2. **Prompt Rolling**：使用库中的提示词进行随机组合
3. **Text Preview**：预览库内容

修改库文件后，需要刷新或重新运行工作流才能看到更新。

## 故障排除

### 问题：点击 "Manage Libraries" 按钮没有反应
- 确保 ComfyUI 已正确加载自定义节点
- 检查浏览器控制台是否有错误信息
- 尝试刷新页面

### 问题：无法保存修改
- 检查 JSON 格式是否正确
- 确保文件名有效
- 检查文件权限

### 问题：库列表为空
- 确保 `ComfyUI-Comicverse/library/` 目录存在
- 检查目录中是否有 `.json` 文件
- 点击 "Refresh" 按钮刷新列表

## API 端点

如果需要通过脚本或其他工具管理库文件，可以使用以下 API 端点：

- `GET /comicverse/libraries/list` - 列出所有库
- `GET /comicverse/libraries/read?name=xxx` - 读取库内容
- `POST /comicverse/libraries/create` - 创建新库
- `POST /comicverse/libraries/save` - 保存库内容
- `POST /comicverse/libraries/rename` - 重命名库
- `POST /comicverse/libraries/delete` - 删除库

详细的 API 文档请参考 `library_manager_api.py` 源代码。

## 示例工作流

### 创建情绪提示词库

1. 添加 Library Manager 节点
2. 点击 "Manage Libraries"
3. 点击 "+ New Library"，输入 `emotions`
4. 在编辑器中输入：
   ```json
   [
     ["happy", "joyful", "cheerful", "delighted"],
     ["sad", "melancholy", "gloomy", "sorrowful"],
     ["angry", "furious", "enraged", "irate"],
     ["calm", "peaceful", "serene", "tranquil"]
   ]
   ```
5. 点击 "Save"
6. 关闭对话框
7. 添加 Prompt Library Loader 节点，选择 `emotions` 库
8. 连接到 Prompt Rolling 节点使用

## 更新日志

### v1.3 (当前版本)
- ✅ 初始发布
- ✅ 完整的 CRUD 功能
- ✅ JSON 验证
- ✅ 自动备份
- ✅ 友好的用户界面



