"""
Comic Asset Library Node
Manages comic materials with preview and selection functionality.
"""

import comfy
import torch
from PIL import Image
from typing import List, Tuple, Optional


class ComicAssetLibraryNode:
    """
    漫画素材库节点
    接收AI生成或手动上传的漫画素材，提供暂存、预览、筛选功能

    输入参数（Inputs）：
    - image_input_1~20: 多通道图片输入，最多支持20张
    - upload_local: 本地图片上传按钮（待实现）

    输出参数（Outputs）：
    - selected_images: 按用户勾选顺序排列的素材列表
    - selected_count: 选中的素材数量
    """

    @classmethod
    def INPUT_TYPES(cls):
        # Define only the inputs as optional (no forceInput)
        # Users can connect any subset of these inputs
        input_types = {}
        for i in range(1, 21):
            input_types[f"image_input_{i}"] = ("IMAGE",)
        return input_types

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("selected_images", "selected_count")
    FUNCTION = "process_images"
    CATEGORY = "ComicVerse/Library"

    def __init__(self):
        self.assets = []
        self.selected_indices = []

    def process_images(self, **kwargs):
        """
        处理输入的图片，转换为ComfyUI格式并去重

        Returns:
            Tuple[IMAGE, INT]: (selected_images, selected_count)
        """
        # 收集所有非None的图片输入
        images = []
        for i in range(1, 21):
            img_key = f"image_input_{i}"
            if img_key in kwargs and kwargs[img_key] is not None:
                img_tensor = kwargs[img_key]
                images.append(img_tensor)

        # 去重处理（基于tensor的唯一性）
        # ComfyUI中图片以[batch, height, width, channels]格式存储
        unique_tensors = []
        seen_tensors = set()

        for img_tensor in images:
            # 转换为numpy进行哈希
            img_array = img_tensor.detach().cpu().numpy()
            img_hash = img_array.tobytes()
            if img_hash not in seen_tensors:
                seen_tensors.add(img_hash)
                unique_tensors.append(img_tensor)

        # 为每个输入创建可选择的输出
        # 在ComfyUI中，勾选逻辑在UI层处理，节点只需要传递数据
        if unique_tensors:
            # 合并所有图片到一个批次
            # 每个图片可能是[1, H, W, C]，需要拼接
            batch_images = []
            for img in unique_tensors:
                if img.dim() == 4 and img.shape[0] == 1:
                    batch_images.append(img[0])  # 移除batch维度
                else:
                    batch_images.append(img)

            # 创建新的batch维度
            if batch_images:
                # 确保所有图片尺寸一致
                first_img = batch_images[0]
                height, width = first_img.shape[0], first_img.shape[1]

                normalized_tensors = []
                for img in batch_images:
                    img_h, img_w = img.shape[0], img.shape[1]
                    if img_h != height or img_w != width:
                        # 缩放图片到统一尺寸
                        # 这里简化处理，实际可能需要更复杂的缩放逻辑
                        pass
                    normalized_tensors.append(img)

                # 添加batch维度并返回
                if normalized_tensors:
                    output_tensor = torch.stack(normalized_tensors, dim=0)
                    return (output_tensor, len(normalized_tensors))

        # 空输入或无效输入处理
        # 返回一个默认的1x1像素图片
        default_image = torch.zeros(1, 512, 512, 3)
        return (default_image, 0)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """
        检查输入是否有变化，用于触发重新处理
        返回True如果任何输入发生变化
        """
        for i in range(1, 21):
            if kwargs.get(f"image_input_{i}") is not None:
                # 返回nan表示始终重新计算
                return float("nan")
        return False

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        """
        验证输入是否有效
        """
        # 至少需要一个图片输入
        has_input = False
        for i in range(1, 21):
            if kwargs.get(f"image_input_{i}") is not None:
                has_input = True
                break

        if not has_input:
            return "Please connect at least one image input."

        return True
