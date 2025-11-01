"""
Speech Bubble Generator Node
Adds speech bubbles to the layout image with customizable styles and text.
"""

import torch
import json
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class SpeechBubbleGeneratorNode:
    """
    对话气泡生成节点
    为排版图添加对话气泡，支持自定义文本、样式和位置

    输入参数（Inputs）：
    - base_image: 基础排版图
    - target_image_index: 气泡关联的素材索引
    - bubble_text: 气泡文本内容（支持换行）
    - bubble_style: 气泡样式（"圆形", "尖角", "云状"）
    - bubble_position: 气泡左上角坐标（x, y）
    - bubble_color: 气泡填充色
    - text_color: 文字颜色

    输出参数（Outputs）：
    - image_with_bubbles: 叠加对话气泡后的图片
    - bubble_coords: 气泡坐标字典
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "base_image": ("IMAGE",),
            "target_image_index": ("INT", {
                "default": 0,
                "min": 0,
                "max": 100,
                "step": 1
            }),
            "bubble_text": ("STRING", {
                "multiline": True,
                "default": "Hello World!"
            }),
            "bubble_style": (
                ["圆形", "尖角", "云状"],
                {
                    "default": "圆形"
                }
            ),
            "bubble_position_x": ("INT", {
                "default": 50,
                "min": 0,
                "max": 2000,
                "step": 1
            }),
            "bubble_position_y": ("INT", {
                "default": 50,
                "min": 0,
                "max": 2000,
                "step": 1
            }),
            "bubble_color": ("STRING", {
                "default": "#FFFFFF"
            }),
            "text_color": ("STRING", {
                "default": "#000000"
            }),
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image_with_bubbles", "bubble_coords")
    FUNCTION = "add_speech_bubble"
    CATEGORY = "ComicVerse/Layout"
    OUTPUT_NODE = False

    def add_speech_bubble(self, base_image, target_image_index, bubble_text,
                          bubble_style, bubble_position_x, bubble_position_y,
                          bubble_color, text_color):
        """
        为图片添加对话气泡

        Args:
            base_image: 基础图片张量
            target_image_index: 目标素材索引
            bubble_text: 气泡文本
            bubble_style: 气泡样式
            bubble_position_x: 气泡X坐标
            bubble_position_y: 气泡Y坐标
            bubble_color: 气泡颜色
            text_color: 文字颜色

        Returns:
            Tuple[IMAGE, str]: (带气泡的图片, 坐标字典JSON)
        """
        # 转换为PIL Image
        img_array = (base_image[0].detach().cpu().numpy() * 255).astype(np.uint8)
        canvas = Image.fromarray(img_array, mode='RGB')
        draw = ImageDraw.Draw(canvas)

        # 解析颜色
        bubble_rgb = self._parse_color(bubble_color)
        text_rgb = self._parse_color(text_color)

        # 计算气泡尺寸
        bubble_width, bubble_height = self._calculate_bubble_size(bubble_text)

        # 根据样式绘制气泡
        bubble_coords = None

        if bubble_style == "圆形":
            bubble_coords = self._draw_oval_bubble(
                draw, bubble_position_x, bubble_position_y,
                bubble_width, bubble_height, bubble_rgb
            )
        elif bubble_style == "尖角":
            bubble_coords = self._draw_pointed_bubble(
                draw, bubble_position_x, bubble_position_y,
                bubble_width, bubble_height, bubble_rgb, canvas.size
            )
        elif bubble_style == "云状":
            bubble_coords = self._draw_cloud_bubble(
                draw, bubble_position_x, bubble_position_y,
                bubble_width, bubble_height, bubble_rgb
            )

        # 添加文字
        self._add_bubble_text(
            draw, bubble_text, bubble_coords,
            bubble_width, bubble_height, text_rgb
        )

        # 转换回tensor格式
        canvas_array = np.array(canvas)
        output_tensor = torch.from_numpy(canvas_array).float() / 255.0
        output_tensor = output_tensor.unsqueeze(0)

        # 记录气泡坐标
        bubble_coords_dict = {
            "0": bubble_coords
        }

        return (output_tensor, json.dumps(bubble_coords_dict))

    def _parse_color(self, color_str):
        """解析颜色字符串为RGB元组"""
        if color_str.startswith('#'):
            color_str = color_str[1:]

        try:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            return (255, 255, 255)

    def _calculate_bubble_size(self, text):
        """根据文本长度计算气泡尺寸"""
        import numpy as np

        # 基础尺寸
        base_width = 200
        base_height = 100

        # 根据文本长度调整
        lines = text.split('\n')
        max_chars = max(len(line) for line in lines) if lines else 1
        num_lines = len(lines)

        # 计算宽度（字符数 * 10 + 基础宽度）
        width = max_chars * 12 + 40
        width = max(width, base_width)

        # 计算高度（行数 * 20 + 基础高度）
        height = num_lines * 25 + 40
        height = max(height, base_height)

        return width, height

    def _draw_oval_bubble(self, draw, x, y, width, height, color):
        """绘制椭圆形气泡"""
        # 绘制椭圆
        draw.ellipse(
            [x, y, x + width, y + height],
            fill=color,
            outline=(0, 0, 0),
            width=2
        )
        return (x, y, x + width, y + height)

    def _draw_pointed_bubble(self, draw, x, y, width, height, color, canvas_size):
        """绘制尖角气泡"""
        # 绘制矩形主体
        draw.rectangle(
            [x, y, x + width, y + height],
            fill=color,
            outline=(0, 0, 0),
            width=2
        )

        # 绘制尖角（指向下方中间）
        point_x = x + width // 2
        point_y = y + height
        triangle = [
            (point_x - 20, y + height),
            (point_x + 20, y + height),
            (point_x, y + height + 30)
        ]
        draw.polygon(triangle, fill=color, outline=(0, 0, 0))

        return (x, y, x + width, y + height)

    def _draw_cloud_bubble(self, draw, x, y, width, height, color):
        """绘制云状气泡（多个圆弧拼接）"""
        import math

        # 绘制椭圆形主体
        draw.ellipse(
            [x, y, x + width, y + height],
            fill=color,
            outline=(0, 0, 0),
            width=2
        )

        # 添加云状凸起（小圆圈）
        circle_radius = 15
        # 右上角
        draw.ellipse(
            [x + width - 10, y - 10, x + width - 10 + circle_radius, y - 10 + circle_radius],
            fill=color,
            outline=(0, 0, 0),
            width=1
        )
        # 左上角
        draw.ellipse(
            [x - 5, y - 5, x - 5 + circle_radius, y - 5 + circle_radius],
            fill=color,
            outline=(0, 0, 0),
            width=1
        )

        return (x, y, x + width, y + height)

    def _add_bubble_text(self, draw, text, coords, bubble_width, bubble_height, text_color):
        """在气泡中添加文字"""
        # 尝试加载系统字体
        try:
            # 默认字体
            font_size = 20
            # 在macOS上尝试常见字体路径
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]

            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break

            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # 计算文字位置（居中）
        lines = text.split('\n')
        line_height = 25
        total_text_height = len(lines) * line_height

        start_y = coords[1] + (bubble_height - total_text_height) // 2
        start_x = coords[0] + 10

        # 绘制每一行文字
        for i, line in enumerate(lines):
            text_y = start_y + i * line_height
            draw.text(
                (start_x, text_y),
                line,
                fill=text_color,
                font=font
            )

    @classmethod
    def VALIDATE_INPUTS(cls, base_image, target_image_index, bubble_text,
                       bubble_style, bubble_position_x, bubble_position_y,
                       bubble_color, text_color):
        """验证输入参数"""
        # 验证样式
        valid_styles = ["圆形", "尖角", "云状"]
        if bubble_style not in valid_styles:
            return f"Invalid bubble_style. Must be one of: {', '.join(valid_styles)}"

        # 验证颜色格式
        for color_name, color_val in [("bubble_color", bubble_color), ("text_color", text_color)]:
            if not isinstance(color_val, str) or len(color_val) != 7 or not color_val.startswith('#'):
                return f"{color_name} must be in format #RRGGBB."

            try:
                int(color_val[1:], 16)
            except ValueError:
                return f"{color_name} must be a valid hex color code."

        # 验证文本
        if not bubble_text or len(bubble_text.strip()) == 0:
            return "Bubble text cannot be empty."

        return True

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        """检查输入变化"""
        return float("nan")
