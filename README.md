# ComicVerse Nodes for ComfyUI

ComicVerse节点库提供了一套完整的漫画排版和设计工具，支持半自动漫画面板布局、对话气泡添加和装饰文字功能。

## 功能特性

- **素材管理**：支持多图片输入和本地文件上传，提供预览和勾选功能
- **模板排版**：内置多种排版模板（横版、竖版、经典4格等）
- **灵活布局**：支持自动排版和手动拖拽调整
- **对话气泡**：多种样式的气泡（圆形、尖角、云状）
- **装饰文字**：支持多种字体样式的装饰文字和拟声词

## 节点列表

1. **Comic Asset Library（漫画素材库节点）**
   - 管理漫画素材，支持多图片输入
   - 提供预览和勾选功能
   - 输出用户选择的素材列表

2. **Layout Template Selector（排版模板选择节点）**
   - 提供预设排版模板
   - 可配置边距和背景色
   - 输出模板配置数据

3. **Basic Layout Composer（基础排版节点）**
   - 根据素材和模板生成排版图
   - 支持自动排版和手动拖拽
   - 输出排版结果和坐标信息

4. **Speech Bubble Generator（对话气泡生成节点）**
   - 添加对话气泡到排版图
   - 支持多种气泡样式
   - 可自定义位置和颜色

5. **Decorative Text Adder（装饰文字添加节点）**
   - 添加装饰文字和拟声词
   - 支持多种字体样式
   - 可自定义颜色和大小

## 安装方法

1. 将此文件夹复制到ComfyUI的`custom_nodes`目录
2. 重启ComfyUI
3. 在节点列表中搜索"ComicVerse"即可找到所有节点

## 使用示例

完整工作流：
```
Comic Asset Library → Layout Template Selector → Basic Layout Composer → Speech Bubble Generator → Decorative Text Adder → Final Output
```

## 技术栈

- Python 3.10+
- Pillow (PIL)
- ComfyUI Framework

## 开发文档

详见项目根目录的《ComicVerse v0.1 功能说明文档》
