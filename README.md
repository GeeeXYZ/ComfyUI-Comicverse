# ComicVerse Nodes for ComfyUI

ComicVerse 节点库提供了一套完整的漫画排版和设计工具，支持半自动漫画面板布局、对话气泡添加和装饰文字功能。

## 功能特性

- **素材管理**：支持多图片输入，提供预览、勾选和删除功能
- **待删除标记**：标记待删除图片，运行工作流时自动删除
- **模板排版**：内置多种排版模板（横版、竖版、经典4格等）
- **灵活布局**：支持自动排版和手动拖拽调整（待实现）
- **对话气泡**：多种样式的气泡（圆形、尖角、云状）
- **装饰文字**：支持多种字体样式的装饰文字和拟声词

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

### 3-5. 其他节点（待实现）

- Basic Layout Composer
- Speech Bubble Generator
- Decorative Text Adder

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

1. **添加素材**：连接图片到 Comic Assets Library 的 `image_input_a` 和 `image_input_b`
2. **选择图片**：点击缩略图勾选要输出的图片
3. **设置数量**：调整 `output_count`，点击 "Set output count"
4. **删除图片**：点击缩略图右上角 ❌ 标记待删除，运行工作流生效
5. **使用模板**：连接 Layout Template Selector 选择排版模板

## 技术特点

- **持久化缓存**：图片缓存跨工作流运行持久保存
- **去重机制**：基于 SHA256 哈希自动去重
- **延迟删除**：标记删除，运行工作流时执行
- **动态 UI**：缩略图区域随图片数量自适应调整

## 开发文档

详见项目仓库的 commit history 和代码注释。
