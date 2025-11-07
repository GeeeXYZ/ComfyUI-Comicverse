# Prompt Library 文件夹

此文件夹包含 Prompt Library Loader 节点自动加载的 JSON 文件。

## 使用方法

1. **添加新的 Prompt 库**：
   - 在此文件夹中创建新的 `.json` 文件
   - 文件名将作为库的名称显示在下拉菜单中
   - 例如：`camera.json` → 在节点中显示为 "camera"

2. **JSON 文件格式**：
   ```json
   [
     ["prompt 1", "variation 1", "variation 2"],
     ["prompt 2", "variation"],
     ["prompt 3"]
   ]
   ```

3. **在 ComfyUI 中使用**：
   - 添加 Prompt Library Loader 节点
   - 从下拉菜单中选择库名称
   - 连接到 Prompt Rolling 节点

## 内置库

### camera.json
包含常用的摄像机角度和镜头类型：
- 低角度 (low angle)
- 平视 (eye level)
- 俯视 (high angle)
- 鸟瞰 (bird's eye view)
- 荷兰角 (dutch angle)
- 过肩镜头 (over the shoulder)
- 特写 (close-up)
- 中景 (medium shot)
- 远景 (wide shot)
- 等等...

### scenes.json
包含常见的场景和地点：
- cafe (咖啡馆)
- hotel (酒店)
- restaurant (餐厅)
- office (办公室)
- bedroom (卧室)
- street (街道)
- park (公园)
- beach (海滩)
- forest (森林)
- 等等...

## 添加自定义库

创建一个新文件，例如 `lighting.json`：

```json
[
  ["soft light", "diffused lighting"],
  ["hard light", "dramatic shadows"],
  ["rim light", "backlit"],
  ["golden hour", "warm sunlight"],
  ["blue hour", "twilight"]
]
```

保存后，重启 ComfyUI 或刷新节点，新的库将出现在下拉菜单中。

## 支持的格式

### 简单格式（单个 prompt）
```json
[
  "prompt 1",
  "prompt 2",
  "prompt 3"
]
```

### 分组格式（相关 prompt 组合）
```json
[
  ["main prompt", "variation 1", "variation 2"],
  ["another prompt", "its variation"],
  ["third prompt"]
]
```

### 中文支持
完全支持中文和其他 Unicode 字符：
```json
[
  ["低角度", "仰视"],
  ["平视", "正面"],
  ["俯视", "从上往下"]
]
```

## 注意事项

- 文件必须使用 UTF-8 编码
- JSON 格式必须正确（可以用在线工具验证）
- 文件名不要包含特殊字符
- 重启 ComfyUI 后新文件才会被识别

---

**提示**: 可以参考 `examples/` 文件夹中的更多示例

