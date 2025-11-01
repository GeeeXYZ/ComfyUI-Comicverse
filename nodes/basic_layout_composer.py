"""
Basic Layout Composer Node
Generates initial layout based on images and template configuration.
Supports automatic layout and manual drag-and-drop adjustment.
"""

import torch
import json
from PIL import Image, ImageDraw
import numpy as np


class BasicLayoutComposerNode:
    """
    基础排版节点
    根据素材列表和模板配置生成初始排版图，支持手动拖拽调整素材位置

    输入参数（Inputs）：
    - images: 素材图片列表
    - template_config: 模板配置字典（JSON字符串）
    - layout_mode: 排版模式（"自动排版", "手动拖拽"）

    输出参数（Outputs）：
    - layout_image: 排版后的图片
    - element_coords: 素材位置坐标字典
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "images": ("IMAGE",),
            "template_config": ("STRING",),
            "layout_mode": (
                ["自动排版", "手动拖拽"],
                {
                    "default": "自动排版"
                }
            ),
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("layout_image", "element_coords")
    FUNCTION = "compose_layout"
    CATEGORY = "ComicVerse/Layout"
    OUTPUT_NODE = False

    # 默认画布尺寸
    DEFAULT_CANVAS_WIDTH = 1080
    DEFAULT_CANVAS_HEIGHT = 1920

    def compose_layout(self, images, template_config, layout_mode):
        """
        根据输入图片和模板配置生成排版图

        Args:
            images: 输入图片张量 [batch, height, width, channels]
            template_config: 模板配置JSON字符串
            layout_mode: 排版模式

        Returns:
            Tuple[IMAGE, str]: (排版图片, 坐标字典JSON)
        """
        import json

        # 解析模板配置
        try:
            config = json.loads(template_config)
        except json.JSONDecodeError:
            raise ValueError("Invalid template_config JSON format")

        grid_count = config.get("grid_count", 0)
        grid_info = config.get("grid_info", [])
        margin = config.get("margin", 5)
        bg_color = config.get("bg_color", (255, 255, 255))

        # 验证图片数量与网格数量匹配
        if images.shape[0] != grid_count:
            raise ValueError(
                f"Image count ({images.shape[0]}) does not match grid count ({grid_count}). "
                f"Please ensure you have exactly {grid_count} images."
            )

        # 创建画布
        canvas_width = self.DEFAULT_CANVAS_WIDTH
        canvas_height = self.DEFAULT_CANVAS_HEIGHT

        # 转换为PIL Image格式处理
        images_pil = []
        for i in range(images.shape[0]):
            img_array = (images[i].detach().cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_array, mode='RGB')
            images_pil.append(pil_img)

        # 创建背景画布
        canvas = Image.new('RGB', (canvas_width, canvas_height), bg_color)

        # 记录元素坐标
        element_coords = {}

        # 执行自动排版
        for idx, grid in enumerate(grid_info):
            # 获取原始图片
            img = images_pil[idx]

            # 计算网格实际尺寸和位置（像素坐标）
            grid_x = int(grid["x"] * canvas_width)
            grid_y = int(grid["y"] * canvas_height)
            grid_w = int(grid["w"] * canvas_width)
            grid_h = int(grid["h"] * canvas_height)

            # 应用边距（上下左右都留边）
            margin_px = margin
            grid_x += margin_px
            grid_y += margin_px
            grid_w -= margin_px * 2
            grid_h -= margin_px * 2

            # 计算缩放后的图片尺寸（保持宽高比）
            img_w, img_h = img.size
            scale_ratio = min(grid_w / img_w, grid_h / img_h)
            new_w = int(img_w * scale_ratio)
            new_h = int(img_h * scale_ratio)

            # 居中对齐
            paste_x = grid_x + (grid_w - new_w) // 2
            paste_y = grid_y + (grid_h - new_h) // 2

            # 缩放并粘贴图片
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas.paste(resized_img, (paste_x, paste_y))

            # 记录元素坐标（格式：x1, y1, x2, y2）
            element_coords[str(idx)] = (paste_x, paste_y, paste_x + new_w, paste_y + new_h)

        # 转换回ComfyUI tensor格式
        canvas_array = np.array(canvas)
        canvas_tensor = torch.from_numpy(canvas_array).float() / 255.0
        canvas_tensor = canvas_tensor.unsqueeze(0)  # 添加batch维度

        return (canvas_tensor, json.dumps(element_coords))

    @classmethod
    def VALIDATE_INPUTS(cls, images, template_config, layout_mode):
        """
        验证输入是否有效
        """
        # 验证模板配置
        try:
            config = json.loads(template_config)
            required_keys = ["grid_count", "grid_info", "margin", "bg_color"]
            for key in required_keys:
                if key not in config:
                    return f"Missing required key in template_config: {key}"
        except json.JSONDecodeError:
            return "Invalid template_config JSON format"

        # 验证layout_mode
        valid_modes = ["自动排版", "手动拖拽"]
        if layout_mode not in valid_modes:
            return f"Invalid layout_mode. Must be one of: {', '.join(valid_modes)}"

        # 验证图片
        if images is None or images.shape[0] == 0:
            return "No images provided"

        return True

    @classmethod
    def IS_CHANGED(cls, images, template_config, layout_mode):
        """
        检查输入是否有变化
        """
        return float("nan")

    @classmethod
    def UI(cls, **kwargs):
        """
        用户界面定义（为未来手动拖拽功能预留）
        """
        ui_elements = []

        # 显示当前排版模式
        layout_mode = kwargs.get("layout_mode", "自动排版")
        ui_elements.append({
            "type": "text",
            "text": f"Layout Mode: {layout_mode}",
            "color": "blue"
        })

        # 如果是手动模式，显示画布信息
        if layout_mode == "手动拖拽":
            ui_elements.append({
                "type": "text",
                "text": "Drag-and-drop functionality will be implemented in future version",
                "color": "gray"
            })

        return ui_elements
