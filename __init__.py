"""
ComicVerse Nodes - ComfyUI Custom Nodes for Comic Layout
A collection of nodes for semi-automatic comic panel layout and design.

Author: ComicVerse Team
Version: 0.1
"""

import torch
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional, Dict


# ================================
# Node 1: Comic Asset Library
# ================================

class ComicAssetLibraryNode:
    """
    漫画素材库节点
    接收AI生成或手动上传的漫画素材，提供暂存、预览、筛选功能
    """

    @classmethod
    def INPUT_TYPES(cls):
        input_types = {}
        for i in range(1, 21):
            input_types[f"image_input_{i}"] = ("IMAGE",)
        return input_types

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("selected_images", "selected_count")
    FUNCTION = "process_images"
    CATEGORY = "ComicVerse"

    def process_images(self, **kwargs):
        """处理输入的图片"""
        images = []
        for i in range(1, 21):
            img_key = f"image_input_{i}"
            if img_key in kwargs and kwargs[img_key] is not None:
                img_tensor = kwargs[img_key]
                images.append(img_tensor)

        if images:
            batch_images = []
            for img in images:
                if img.dim() == 4 and img.shape[0] == 1:
                    batch_images.append(img[0])
                else:
                    batch_images.append(img)

            if batch_images:
                output_tensor = torch.stack(batch_images, dim=0)
                return (output_tensor, len(batch_images))

        default_image = torch.zeros(1, 512, 512, 3)
        return (default_image, 0)


# ================================
# Node 2: Layout Template Selector
# ================================

class LayoutTemplateSelectorNode:
    """
    排版模板选择节点
    提供预设排版模板，配置基础布局参数
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "template_type": (
                ["2横版", "2竖版", "4格经典", "3格斜切", "自由网格"],
                {"default": "4格经典"}
            ),
            "grid_margin": ("INT", {"default": 5, "min": 1, "max": 20, "step": 1}),
            "background_color": ("STRING", {"default": "#FFFFFF"}),
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("template_config",)
    FUNCTION = "generate_template"
    CATEGORY = "ComicVerse"

    TEMPLATE_DATA = {
        "2横版": {
            "grid_count": 2,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.5, "h": 1.0},
                {"x": 0.5, "y": 0, "w": 0.5, "h": 1.0}
            ]
        },
        "2竖版": {
            "grid_count": 2,
            "grid_info": [
                {"x": 0, "y": 0, "w": 1.0, "h": 0.5},
                {"x": 0, "y": 0.5, "w": 1.0, "h": 0.5}
            ]
        },
        "4格经典": {
            "grid_count": 4,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.5, "h": 0.5},
                {"x": 0.5, "y": 0, "w": 0.5, "h": 0.5},
                {"x": 0, "y": 0.5, "w": 0.5, "h": 0.5},
                {"x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5}
            ]
        },
        "3格斜切": {
            "grid_count": 3,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.6, "h": 0.6},
                {"x": 0.6, "y": 0, "w": 0.4, "h": 0.4},
                {"x": 0, "y": 0.6, "w": 1.0, "h": 0.4}
            ]
        },
        "自由网格": {
            "grid_count": 3,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.33, "h": 1.0},
                {"x": 0.33, "y": 0, "w": 0.33, "h": 1.0},
                {"x": 0.66, "y": 0, "w": 0.34, "h": 1.0}
            ]
        }
    }

    def generate_template(self, template_type, grid_margin, background_color):
        """生成模板配置"""
        if template_type not in self.TEMPLATE_DATA:
            raise ValueError(f"Unknown template type: {template_type}")

        template_data = self.TEMPLATE_DATA[template_type].copy()

        template_config = {
            "grid_count": template_data["grid_count"],
            "grid_info": template_data["grid_info"],
            "margin": grid_margin,
            "bg_color": self._parse_color(background_color)
        }

        return (json.dumps(template_config),)

    def _parse_color(self, color_str):
        """解析颜色字符串"""
        if color_str.startswith('#'):
            color_str = color_str[1:]

        try:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            return (255, 255, 255)


# ================================
# Node 3: Basic Layout Composer
# ================================

class BasicLayoutComposerNode:
    """
    基础排版节点
    根据素材列表和模板配置生成初始排版图
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "images": ("IMAGE",),
            "template_config": ("STRING",),
            "layout_mode": (["自动排版", "手动拖拽"], {"default": "自动排版"}),
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("layout_image", "element_coords")
    FUNCTION = "compose_layout"
    CATEGORY = "ComicVerse"

    DEFAULT_CANVAS_WIDTH = 1080
    DEFAULT_CANVAS_HEIGHT = 1920

    def compose_layout(self, images, template_config, layout_mode):
        """生成排版图"""
        try:
            config = json.loads(template_config)
        except json.JSONDecodeError:
            raise ValueError("Invalid template_config JSON format")

        grid_count = config.get("grid_count", 0)
        grid_info = config.get("grid_info", [])
        margin = config.get("margin", 5)
        bg_color = config.get("bg_color", (255, 255, 255))

        if images.shape[0] != grid_count:
            raise ValueError(
                f"Image count ({images.shape[0]}) does not match grid count ({grid_count})."
            )

        canvas_width = self.DEFAULT_CANVAS_WIDTH
        canvas_height = self.DEFAULT_CANVAS_HEIGHT

        images_pil = []
        for i in range(images.shape[0]):
            img_array = (images[i].detach().cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_array, mode='RGB')
            images_pil.append(pil_img)

        canvas = Image.new('RGB', (canvas_width, canvas_height), bg_color)
        element_coords = {}

        for idx, grid in enumerate(grid_info):
            img = images_pil[idx]

            grid_x = int(grid["x"] * canvas_width)
            grid_y = int(grid["y"] * canvas_height)
            grid_w = int(grid["w"] * canvas_width)
            grid_h = int(grid["h"] * canvas_height)

            margin_px = margin
            grid_x += margin_px
            grid_y += margin_px
            grid_w -= margin_px * 2
            grid_h -= margin_px * 2

            img_w, img_h = img.size
            scale_ratio = min(grid_w / img_w, grid_h / img_h)
            new_w = int(img_w * scale_ratio)
            new_h = int(img_h * scale_ratio)

            paste_x = grid_x + (grid_w - new_w) // 2
            paste_y = grid_y + (grid_h - new_h) // 2

            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas.paste(resized_img, (paste_x, paste_y))

            element_coords[str(idx)] = (paste_x, paste_y, paste_x + new_w, paste_y + new_h)

        canvas_array = np.array(canvas)
        canvas_tensor = torch.from_numpy(canvas_array).float() / 255.0
        canvas_tensor = canvas_tensor.unsqueeze(0)

        return (canvas_tensor, json.dumps(element_coords))


# ================================
# Node 4: Speech Bubble Generator
# ================================

class SpeechBubbleGeneratorNode:
    """
    对话气泡生成节点
    为排版图添加对话气泡，支持自定义文本、样式和位置
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "base_image": ("IMAGE",),
            "target_image_index": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
            "bubble_text": ("STRING", {"multiline": True, "default": "Hello World!"}),
            "bubble_style": (["圆形", "尖角", "云状"], {"default": "圆形"}),
            "bubble_position_x": ("INT", {"default": 50, "min": 0, "max": 2000, "step": 1}),
            "bubble_position_y": ("INT", {"default": 50, "min": 0, "max": 2000, "step": 1}),
            "bubble_color": ("STRING", {"default": "#FFFFFF"}),
            "text_color": ("STRING", {"default": "#000000"}),
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image_with_bubbles", "bubble_coords")
    FUNCTION = "add_speech_bubble"
    CATEGORY = "ComicVerse"

    def add_speech_bubble(self, base_image, target_image_index, bubble_text,
                          bubble_style, bubble_position_x, bubble_position_y,
                          bubble_color, text_color):
        """添加对话气泡"""
        img_array = (base_image[0].detach().cpu().numpy() * 255).astype(np.uint8)
        canvas = Image.fromarray(img_array, mode='RGB')
        draw = ImageDraw.Draw(canvas)

        bubble_rgb = self._parse_color(bubble_color)
        text_rgb = self._parse_color(text_color)

        bubble_width, bubble_height = self._calculate_bubble_size(bubble_text)

        bubble_coords = None
        if bubble_style == "圆形":
            bubble_coords = self._draw_oval_bubble(draw, bubble_position_x, bubble_position_y,
                                                   bubble_width, bubble_height, bubble_rgb)
        elif bubble_style == "尖角":
            bubble_coords = self._draw_pointed_bubble(draw, bubble_position_x, bubble_position_y,
                                                      bubble_width, bubble_height, bubble_rgb, canvas.size)
        elif bubble_style == "云状":
            bubble_coords = self._draw_cloud_bubble(draw, bubble_position_x, bubble_position_y,
                                                    bubble_width, bubble_height, bubble_rgb)

        self._add_bubble_text(draw, bubble_text, bubble_coords, bubble_width, bubble_height, text_rgb)

        canvas_array = np.array(canvas)
        output_tensor = torch.from_numpy(canvas_array).float() / 255.0
        output_tensor = output_tensor.unsqueeze(0)

        bubble_coords_dict = {"0": bubble_coords}
        return (output_tensor, json.dumps(bubble_coords_dict))

    def _parse_color(self, color_str):
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
        lines = text.split('\n')
        max_chars = max(len(line) for line in lines) if lines else 1
        num_lines = len(lines)

        width = max_chars * 12 + 40
        width = max(width, 200)
        height = num_lines * 25 + 40
        height = max(height, 100)

        return width, height

    def _draw_oval_bubble(self, draw, x, y, width, height, color):
        draw.ellipse([x, y, x + width, y + height],
                     fill=color, outline=(0, 0, 0), width=2)
        return (x, y, x + width, y + height)

    def _draw_pointed_bubble(self, draw, x, y, width, height, color, canvas_size):
        draw.rectangle([x, y, x + width, y + height],
                       fill=color, outline=(0, 0, 0), width=2)
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
        draw.ellipse([x, y, x + width, y + height],
                     fill=color, outline=(0, 0, 0), width=2)
        circle_radius = 15
        draw.ellipse([x + width - 10, y - 10, x + width - 10 + circle_radius, y - 10 + circle_radius],
                     fill=color, outline=(0, 0, 0), width=1)
        draw.ellipse([x - 5, y - 5, x - 5 + circle_radius, y - 5 + circle_radius],
                     fill=color, outline=(0, 0, 0), width=1)
        return (x, y, x + width, y + height)

    def _add_bubble_text(self, draw, text, coords, bubble_width, bubble_height, text_color):
        try:
            font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        lines = text.split('\n')
        line_height = 25
        total_text_height = len(lines) * line_height

        start_y = coords[1] + (bubble_height - total_text_height) // 2
        start_x = coords[0] + 10

        for i, line in enumerate(lines):
            text_y = start_y + i * line_height
            draw.text((start_x, text_y), line, fill=text_color, font=font)


# ================================
# Node 5: Decorative Text Adder
# ================================

class DecorativeTextAdderNode:
    """
    装饰文字添加节点
    为图片添加装饰文字（拟声词、旁白等）
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "input_image": ("IMAGE",),
            "text_content": ("STRING", {"multiline": True, "default": "BOOM!"}),
            "font_style": (["手写体", "黑体", "卡通体"], {"default": "手写体"}),
            "text_size": ("INT", {"default": 30, "min": 10, "max": 100, "step": 1}),
            "text_color": ("STRING", {"default": "#FF0000"}),
            "text_position_x": ("INT", {"default": 100, "min": 0, "max": 2000, "step": 1}),
            "text_position_y": ("INT", {"default": 100, "min": 0, "max": 2000, "step": 1}),
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("final_image",)
    FUNCTION = "add_decorative_text"
    CATEGORY = "ComicVerse"

    FONT_MAPPING = {
        "手写体": "handwriting.ttf",
        "黑体": "black_bold.ttf",
        "卡通体": "cartoon.ttf"
    }

    def add_decorative_text(self, input_image, text_content, font_style,
                           text_size, text_color, text_position_x, text_position_y):
        """添加装饰文字"""
        img_array = (input_image[0].detach().cpu().numpy() * 255).astype(np.uint8)
        canvas = Image.fromarray(img_array, mode='RGB')
        draw = ImageDraw.Draw(canvas)

        text_rgb = self._parse_color(text_color)
        font = self._load_font(font_style, text_size)

        self._draw_text_with_outline(draw, text_content,
                                     (text_position_x, text_position_y), text_rgb, font)

        canvas_array = np.array(canvas)
        output_tensor = torch.from_numpy(canvas_array).float() / 255.0
        output_tensor = output_tensor.unsqueeze(0)

        return (output_tensor,)

    def _parse_color(self, color_str):
        if color_str.startswith('#'):
            color_str = color_str[1:]
        try:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            return (255, 0, 0)

    def _load_font(self, font_style, text_size):
        current_dir = os.path.dirname(__file__)
        fonts_dir = os.path.join(current_dir, "fonts")
        font_filename = self.FONT_MAPPING.get(font_style, "handwriting.ttf")
        font_path = os.path.join(fonts_dir, font_filename)

        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, text_size)
            except Exception:
                pass

        try:
            return ImageFont.load_default()
        except Exception:
            return None

    def _draw_text_with_outline(self, draw, text, position, fill_color, font):
        x, y = position
        outline_color = (0, 0, 0)
        outline_width = 1

        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x != 0 or adj_y != 0:
                    draw.text((x + adj_x, y + adj_y), text,
                             fill=outline_color, font=font)

        draw.text(position, text, fill=fill_color, font=font)


# ================================
# Node Class Mappings
# ================================

NODE_CLASS_MAPPINGS = {
    "ComicAssetLibrary": ComicAssetLibraryNode,
    "LayoutTemplateSelector": LayoutTemplateSelectorNode,
    "BasicLayoutComposer": BasicLayoutComposerNode,
    "SpeechBubbleGenerator": SpeechBubbleGeneratorNode,
    "DecorativeTextAdder": DecorativeTextAdderNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicAssetLibrary": "Comic Asset Library",
    "LayoutTemplateSelector": "Layout Template Selector",
    "BasicLayoutComposer": "Basic Layout Composer",
    "SpeechBubbleGenerator": "Speech Bubble Generator",
    "DecorativeTextAdder": "Decorative Text Adder",
}

WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
