"""
Decorative Text Adder Node
Adds decorative text (onomatopoeia, narration, etc.) to images with style options.
"""

import torch
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class DecorativeTextAdderNode:
    """
    装饰文字添加节点
    为图片添加装饰文字（拟声词、旁白等），支持样式调整

    输入参数（Inputs）：
    - input_image: 输入图片
    - text_content: 装饰文字内容
    - font_style: 字体样式（"手写体", "黑体", "卡通体"）
    - text_size: 文字大小（px）
    - text_color: 文字颜色
    - text_position_x: 文字X坐标
    - text_position_y: 文字Y坐标

    输出参数（Outputs）：
    - final_image: 叠加装饰文字后的最终成品图
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "input_image": ("IMAGE",),
            "text_content": ("STRING", {
                "multiline": True,
                "default": "BOOM!"
            }),
            "font_style": (
                ["手写体", "黑体", "卡通体"],
                {
                    "default": "手写体"
                }
            ),
            "text_size": ("INT", {
                "default": 30,
                "min": 10,
                "max": 100,
                "step": 1
            }),
            "text_color": ("STRING", {
                "default": "#FF0000"
            }),
            "text_position_x": ("INT", {
                "default": 100,
                "min": 0,
                "max": 2000,
                "step": 1
            }),
            "text_position_y": ("INT", {
                "default": 100,
                "min": 0,
                "max": 2000,
                "step": 1
            }),
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("final_image",)
    FUNCTION = "add_decorative_text"
    CATEGORY = "ComicVerse/Layout"
    OUTPUT_NODE = False

    # 字体文件映射
    FONT_MAPPING = {
        "手写体": "handwriting.ttf",
        "黑体": "black_bold.ttf",
        "卡通体": "cartoon.ttf"
    }

    def add_decorative_text(self, input_image, text_content, font_style,
                           text_size, text_color, text_position_x, text_position_y):
        """
        添加装饰文字到图片

        Args:
            input_image: 输入图片张量
            text_content: 装饰文字内容
            font_style: 字体样式
            text_size: 文字大小
            text_color: 文字颜色（十六进制字符串）
            text_position_x: 文字X坐标
            text_position_y: 文字Y坐标

        Returns:
            IMAGE: 叠加装饰文字后的图片
        """
        # 转换为PIL Image
        img_array = (input_image[0].detach().cpu().numpy() * 255).astype(np.uint8)
        canvas = Image.fromarray(img_array, mode='RGB')
        draw = ImageDraw.Draw(canvas)

        # 解析颜色
        text_rgb = self._parse_color(text_color)

        # 加载字体
        font = self._load_font(font_style, text_size)

        # 添加文字（带描边效果）
        self._draw_text_with_outline(
            draw,
            text_content,
            (text_position_x, text_position_y),
            text_rgb,
            font
        )

        # 转换回tensor格式
        canvas_array = np.array(canvas)
        output_tensor = torch.from_numpy(canvas_array).float() / 255.0
        output_tensor = output_tensor.unsqueeze(0)

        return (output_tensor,)

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
            return (255, 0, 0)  # 默认红色

    def _load_font(self, font_style, text_size):
        """
        加载字体文件

        Args:
            font_style: 字体样式
            text_size: 字体大小

        Returns:
            ImageFont: PIL字体对象
        """
        # 获取当前节点文件所在目录
        current_dir = os.path.dirname(os.path.dirname(__file__))
        fonts_dir = os.path.join(current_dir, "fonts")
        font_filename = self.FONT_MAPPING.get(font_style, "handwriting.ttf")
        font_path = os.path.join(fonts_dir, font_filename)

        # 尝试加载自定义字体
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, text_size)
            except Exception as e:
                print(f"Failed to load font {font_path}: {e}")

        # 回退到系统字体
        system_font_paths = self._get_system_font_paths()
        for font_path in system_font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, text_size)
                except Exception:
                    continue

        # 最后回退到默认字体
        return ImageFont.load_default()

    def _get_system_font_paths(self):
        """获取系统字体路径列表"""
        import platform

        system = platform.system()
        font_paths = []

        if system == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/HelveticaNeue.ttc",
                "/System/Library/Fonts/SFNS.ttf",
            ]
        elif system == "Windows":
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibri.ttf",
            ]
        else:  # Linux
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/TTF/arial.ttf",
            ]

        return font_paths

    def _draw_text_with_outline(self, draw, text, position, fill_color, font):
        """
        绘制带描边的文字

        Args:
            draw: ImageDraw对象
            text: 文字内容
            position: 文字位置
            fill_color: 填充颜色
            font: 字体对象
        """
        x, y = position

        # 绘制描边（黑色，向8个方向偏移1像素）
        outline_color = (0, 0, 0)
        outline_width = 1

        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x != 0 or adj_y != 0:
                    draw.text(
                        (x + adj_x, y + adj_y),
                        text,
                        fill=outline_color,
                        font=font
                    )

        # 绘制主文字
        draw.text(position, text, fill=fill_color, font=font)

    @classmethod
    def VALIDATE_INPUTS(cls, input_image, text_content, font_style,
                       text_size, text_color, text_position_x, text_position_y):
        """验证输入参数"""
        # 验证字体样式
        valid_styles = ["手写体", "黑体", "卡通体"]
        if font_style not in valid_styles:
            return f"Invalid font_style. Must be one of: {', '.join(valid_styles)}"

        # 验证文字大小
        if not (10 <= text_size <= 100):
            return "Text size must be between 10 and 100."

        # 验证颜色格式
        if not isinstance(text_color, str) or len(text_color) != 7 or not text_color.startswith('#'):
            return "Text color must be in format #RRGGBB."

        try:
            int(text_color[1:], 16)
        except ValueError:
            return "Text color must be a valid hex color code."

        # 验证文本内容
        if not text_content or len(text_content.strip()) == 0:
            return "Text content cannot be empty."

        return True

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        """检查输入变化"""
        return float("nan")
