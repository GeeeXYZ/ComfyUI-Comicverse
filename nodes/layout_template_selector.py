"""
Layout Template Selector Node
Provides preset layout templates with configurable parameters.
"""

import torch


class LayoutTemplateSelectorNode:
    """
    排版模板选择节点
    提供预设排版模板，配置基础布局参数（边距、背景色），输出模板结构数据

    输入参数（Inputs）：
    - template_type: 模板类型（"2横版", "2竖版", "4格经典", "3格斜切", "自由网格"）
    - grid_margin: 网格边距（px），默认5，范围1~20
    - background_color: 背景色，默认白色

    输出参数（Outputs）：
    - template_config: 模板配置字典
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "template_type": (
                ["2横版", "2竖版", "4格经典", "3格斜切", "自由网格"],
                {
                    "default": "4格经典"
                }
            ),
            "grid_margin": ("INT", {
                "default": 5,
                "min": 1,
                "max": 20,
                "step": 1
            }),
            "background_color": ("STRING", {
                "default": "#FFFFFF"
            }),
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("template_config",)
    FUNCTION = "generate_template"
    CATEGORY = "ComicVerse/Library"

    # 预设模板数据字典
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
            "grid_count": 4,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.33, "h": 1.0},
                {"x": 0.33, "y": 0, "w": 0.33, "h": 1.0},
                {"x": 0.66, "y": 0, "w": 0.34, "h": 1.0}
            ]
        }
    }

    def generate_template(self, template_type, grid_margin, background_color):
        """
        生成模板配置

        Args:
            template_type: 选择的模板类型
            grid_margin: 网格边距
            background_color: 背景色（十六进制字符串）

        Returns:
            str: 模板配置的JSON字符串
        """
        import json

        # 获取预设模板数据
        if template_type not in self.TEMPLATE_DATA:
            raise ValueError(f"Unknown template type: {template_type}")

        template_data = self.TEMPLATE_DATA[template_type].copy()

        # 构建完整配置
        template_config = {
            "grid_count": template_data["grid_count"],
            "grid_info": template_data["grid_info"],
            "margin": grid_margin,
            "bg_color": self._parse_color(background_color)
        }

        # 转换为JSON字符串供下游节点使用
        return (json.dumps(template_config),)

    def _parse_color(self, color_str):
        """
        解析颜色字符串

        Args:
            color_str: 颜色字符串（十六进制格式，如#FFFFFF）

        Returns:
            tuple: RGB元组 (R, G, B)
        """
        # 移除#号
        if color_str.startswith('#'):
            color_str = color_str[1:]

        # 转换为RGB
        try:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            # 默认白色
            return (255, 255, 255)

    @classmethod
    def VALIDATE_INPUTS(cls, template_type, grid_margin, background_color):
        """
        验证输入是否有效
        """
        # 验证模板类型
        valid_templates = ["2横版", "2竖版", "4格经典", "3格斜切", "自由网格"]
        if template_type not in valid_templates:
            return f"Invalid template type. Must be one of: {', '.join(valid_templates)}"

        # 验证网格边距
        if not (1 <= grid_margin <= 20):
            return "Grid margin must be between 1 and 20."

        # 验证背景色格式
        if not isinstance(background_color, str) or len(background_color) != 7:
            return "Background color must be in format #RRGGBB."

        try:
            int(background_color[1:], 16)
        except ValueError:
            return "Background color must be a valid hex color code."

        return True
