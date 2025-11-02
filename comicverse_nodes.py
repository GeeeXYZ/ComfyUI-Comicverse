"""
ComicVerse custom nodes (initial scaffold)

This module provides a minimal test node to verify repository loading in ComfyUI.
Place the repository folder under ComfyUI's `custom_nodes` directory to load.
"""

from typing import Dict, Any, List, Tuple
import re
import torch
from io import BytesIO
import hashlib
import json

try:
    from server import PromptServer  # ComfyUI server messaging
except Exception:  # pragma: no cover
    PromptServer = None  # type: ignore


class ComicVerseTestNode:
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        # Minimal input: a single string to echo back
        return {
            "required": {
                "text": ("STRING", {"default": "Hello ComicVerse!", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text_out",)
    FUNCTION = "run"
    CATEGORY = "ComicVerse/Test"

    def run(self, text: str):
        # Echo input back to verify execution path
        return (str(text),)


# Persistent in-process cache for library images per node instance
_LIBRARY_CACHE: dict[str, List[torch.Tensor]] = {}
_LIBRARY_HASHES: dict[str, List[str]] = {}
_PENDING_DELETIONS: dict[str, List[int]] = {}  # Track pending deletions per node


class ComicAssetLibraryNode:
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        input_types = {
            "required": {
                "output_count": ("INT", {"default": 2, "min": 1, "max": 6}),
                "selected_indices": ("STRING", {"default": "", "multiline": False, "placeholder": "选中顺序：如 2,0,1"}),
                "pending_deletions": ("STRING", {"default": "", "multiline": False, "placeholder": "待删除索引（自动填充）"}),
            },
            "optional": {},
            "hidden": {
                "unique_id": ("UNIQUE_ID", {}),
            },
        }
        # Add 20 optional IMAGE inputs
        for i in range(1, 21):
            input_types["optional"][f"image_input_{i}"] = ("IMAGE", {})
        return input_types

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "INT")
    RETURN_NAMES = ("image_1", "image_2", "image_3", "image_4", "image_5", "image_6", "selected_count")
    FUNCTION = "run"
    CATEGORY = "ComicVerse/Library"

    def _parse_indices(self, selected_indices: str, max_len: int):
        if not selected_indices:
            return None
        tokens = re.split(r"[\s,]+", selected_indices.strip())
        indices = []
        for t in tokens:
            if t == "":
                continue
            try:
                idx = int(t)
            except ValueError:
                raise ValueError(f"Invalid index '{t}' in selected_indices. Use comma-separated integers.")
            if idx < 0 or idx >= max_len:
                raise ValueError(f"Index {idx} out of range [0, {max_len-1}].")
            indices.append(idx)
        return indices

    def run(self, output_count: int, selected_indices: str = "", unique_id: str = "", pending_deletions: str = "", **kwargs):
        # Collect connected IMAGE inputs from kwargs (image_input_1, image_input_2, ..., image_input_20)
        image_batches = []
        for i in range(1, 21):
            img_key = f"image_input_{i}"
            if img_key in kwargs and kwargs[img_key] is not None:
                image_batches.append(kwargs[img_key])

        # Allow running without inputs (for cache viewing/deletion only)
        # if len(image_batches) == 0:
        #     raise ValueError("请至少连接1个 IMAGE 输入到漫画素材库节点 (ComicAssetLibraryNode)。")

        # Validate basic tensor shapes, flatten to single-image batches (allow different H,W)
        current_list = []
        for idx, tensor in enumerate(image_batches):
            if tensor is None:
                continue
            if tensor.dim() != 4 or tensor.shape[3] not in (3, 4):
                raise ValueError(f"第{idx+1}个 IMAGE 输入张量形状无效，期望形状 [B,H,W,C] 且 C=3 或 4。")
            # Flatten each batch into single-image tensors [1,H,W,C]
            for i in range(tensor.shape[0]):
                current_list.append(tensor[i:i+1])

        # Get or initialize cache per node unique_id
        key = unique_id or "global"
        lib_list = _LIBRARY_CACHE.get(key, [])
        lib_hashes = _LIBRARY_HASHES.get(key, [])
        
        # Process pending deletions first (before adding new images)
        if pending_deletions:
            indices = [int(i.strip()) for i in pending_deletions.split(",") if i.strip().isdigit()]
            # Delete in reverse order to avoid index shifting issues
            for idx in sorted(indices, reverse=True):
                if 0 <= idx < len(lib_list):
                    lib_list.pop(idx)
                    lib_hashes.pop(idx)
        
        # Hard cap to avoid unbounded memory
        max_cache = 200
        for b in current_list:
            # compute hash to de-duplicate
            h, w, c = b.shape[1:]
            img_uint8 = (b[0].clamp(0, 1) * 255).byte().cpu().numpy()
            from PIL import Image
            img = Image.fromarray(img_uint8, mode='RGBA' if c == 4 else 'RGB')
            bio = BytesIO()
            img.save(bio, format='PNG')
            digest = hashlib.sha256(bio.getvalue()).hexdigest()
            if digest in lib_hashes:
                continue
            lib_list.append(b)
            lib_hashes.append(digest)
            if len(lib_list) > max_cache:
                lib_list.pop(0)
                lib_hashes.pop(0)
        _LIBRARY_CACHE[key] = lib_list
        _LIBRARY_HASHES[key] = lib_hashes

        # Determine selection order relative to the library
        order = self._parse_indices(selected_indices, len(lib_list))
        if order is None or len(order) == 0:
            ordered = []
        else:
            ordered = [lib_list[i] for i in order]

        # Respect output_count and hard-cap to 6 (only if we have items to select)
        k = max(1, min(6, int(output_count)))
        selected = ordered[:k] if len(ordered) >= k else ordered

        # Pad with black images if fewer than k
        outputs: list = []
        
        if len(selected) == 0:
            # no selection -> do not output real images; return blanks and count=0
            selected = []
            # Need to create a blank with a valid shape; use first input's shape or default
            if len(lib_list) > 0:
                ref_shape = lib_list[0].shape[1:]
            elif len(current_list) > 0:
                ref_shape = current_list[0].shape[1:]
            else:
                ref_shape = (512, 512, 3)
        else:
            ref_shape = selected[0].shape[1:]
        
        def _blank():
            h, w, c = ref_shape
            # Use first tensor's device/dtype if available, else defaults
            if len(current_list) > 0:
                ref_tensor = current_list[0]
                return torch.zeros((1, h, w, c), dtype=ref_tensor.dtype, device=ref_tensor.device)
            else:
                return torch.zeros((1, h, w, c))

        # Build up to 6 outputs
        for i in range(6):
            if i < len(selected):
                outputs.append(selected[i])
            elif i < k:
                outputs.append(_blank())
            else:
                # beyond requested count: still return a tensor (reuse last) to satisfy output shape
                outputs.append(outputs[-1])

        selected_count = int(min(len(ordered), k))

        # Push thumbnails to frontend for interactive preview and selection
        try:
            if PromptServer is not None:
                thumbs = []
                max_send = min(120, len(lib_list))
                max_preview = min(30, len(lib_list))  # Only send full preview for first 30
                for i in range(max_send):
                    b = lib_list[i]
                    # b: [1,H,W,C] tensor in 0..1
                    h, w, c = b.shape[1:]
                    img_uint8 = (b[0].clamp(0, 1) * 255).byte().cpu().numpy()
                    from PIL import Image
                    img = Image.fromarray(img_uint8, mode='RGBA' if c == 4 else 'RGB')
                    
                    # create thumbnail (96px for grid display)
                    thumb_w = 96
                    scale = thumb_w / float(w)
                    thumb_h = max(1, int(h * scale))
                    thumb_img = img.resize((thumb_w, thumb_h), Image.BILINEAR)
                    bio = BytesIO()
                    thumb_img.save(bio, format='PNG')
                    data = bio.getvalue()
                    import base64
                    thumb_data_url = "data:image/png;base64," + base64.b64encode(data).decode('ascii')
                    
                    # create preview image (max 1024px for zoom)
                    thumb_entry = {"w": thumb_img.width, "h": thumb_img.height, "data": thumb_data_url}
                    if i < max_preview:
                        max_preview_dim = 1024
                        if w > h:
                            preview_w = min(max_preview_dim, w)
                            preview_h = max(1, int(h * preview_w / w))
                        else:
                            preview_h = min(max_preview_dim, h)
                            preview_w = max(1, int(w * preview_h / h))
                        preview_img = img.resize((preview_w, preview_h), Image.BILINEAR)
                        bio = BytesIO()
                        preview_img.save(bio, format='PNG')
                        data = bio.getvalue()
                        preview_data_url = "data:image/png;base64," + base64.b64encode(data).decode('ascii')
                        thumb_entry["preview"] = preview_data_url
                    
                    thumbs.append(thumb_entry)
                PromptServer.instance.send_sync("comicverse.library.previews", {
                    "thumbs": thumbs,
                    "count": len(lib_list),
                    "selected": self._parse_indices(selected_indices, len(lib_list)) or [],
                })
        except Exception:
            pass

        return (*outputs, selected_count)


class LayoutTemplateSelectorNode:
    """
    Node 2: 排版模板选择节点
    提供预设排版模板，配置基础布局参数（边距、背景色），输出模板结构数据
    """
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "template_type": (["2横版", "2竖版", "4格经典", "3格斜切", "自由网格"],),
                "grid_margin": ("INT", {"default": 5, "min": 1, "max": 20}),
                "background_color_r": ("INT", {"default": 255, "min": 0, "max": 255}),
                "background_color_g": ("INT", {"default": 255, "min": 0, "max": 255}),
                "background_color_b": ("INT", {"default": 255, "min": 0, "max": 255}),
            }
        }

    RETURN_TYPES = ("STRING",)  # JSON-encoded template_config
    RETURN_NAMES = ("template_config",)
    FUNCTION = "run"
    CATEGORY = "ComicVerse/Layout"

    _TEMPLATES = {
        "2横版": {
            "grid_count": 2,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.5, "h": 1.0},
                {"x": 0.5, "y": 0, "w": 0.5, "h": 1.0},
            ]
        },
        "2竖版": {
            "grid_count": 2,
            "grid_info": [
                {"x": 0, "y": 0, "w": 1.0, "h": 0.5},
                {"x": 0, "y": 0.5, "w": 1.0, "h": 0.5},
            ]
        },
        "4格经典": {
            "grid_count": 4,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.5, "h": 0.5},
                {"x": 0.5, "y": 0, "w": 0.5, "h": 0.5},
                {"x": 0, "y": 0.5, "w": 0.5, "h": 0.5},
                {"x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5},
            ]
        },
        "3格斜切": {
            "grid_count": 3,
            "grid_info": [
                {"x": 0, "y": 0, "w": 0.33, "h": 0.5},
                {"x": 0.33, "y": 0, "w": 0.33, "h": 0.5},
                {"x": 0.66, "y": 0, "w": 0.34, "h": 1.0},
            ]
        },
        "自由网格": {
            "grid_count": 1,
            "grid_info": [
                {"x": 0, "y": 0, "w": 1.0, "h": 1.0},
            ]
        }
    }

    def run(self, template_type: str, grid_margin: int, background_color_r: int, background_color_g: int, background_color_b: int):
        if template_type not in self._TEMPLATES:
            raise ValueError(f"Unknown template type: {template_type}")

        template_data = self._TEMPLATES[template_type].copy()
        template_data["margin"] = grid_margin
        template_data["bg_color"] = (background_color_r, background_color_g, background_color_b)

        # Validate grid_count matches grid_info length
        if template_data["grid_count"] != len(template_data["grid_info"]):
            raise ValueError(
                f"Template '{template_type}' grid_count ({template_data['grid_count']}) "
                f"mismatch with grid_info length ({len(template_data['grid_info'])})"
            )

        # Return JSON-encoded string for downstream nodes
        return (json.dumps(template_data),)


def _format_float(value: float) -> str:
    """Format float to exactly one decimal place."""
    return f"{value:.1f}"


class PromptStrengthSlider:
    """Assigns strengths to prompts and emits a formatted string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": (
                    "STRING",
                    {
                        "forceInput": True,
                        "tooltip": "Connect a STRING of prompts (comma/newline separated)",
                    },
                ),
            },
            "hidden": {
                "strengths_json": "STRING",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "apply_strengths"
    CATEGORY = "ComicVerse/Prompt"

    def apply_strengths(
        self,
        prompts: str = "",
        strengths_json: str = "",
    ):
        prompts_list, strengths = self._extract_prompts_and_strengths(strengths_json)

        normalized: Dict[str, float] = {}
        formatted_pairs = []
        for prompt in prompts_list:
            value = strengths.get(prompt, 1.0)
            if value < 0.0:
                value = 0.0
            if value > 2.0:
                value = 2.0
            normalized[prompt] = value
            formatted_pairs.append(f"({prompt}:{_format_float(value)})")

        formatted = ",".join(formatted_pairs)
        return (formatted,)

    @staticmethod
    def _extract_prompts_and_strengths(raw_json: str):
        prompts: List[str] = []
        if not raw_json:
            return prompts, {}
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            return prompts, {}

        meta_prompts = payload.get("__prompts__")
        order_meta = payload.get("__order__")
        if isinstance(meta_prompts, list):
            prompts = [str(item).strip() for item in meta_prompts if str(item).strip()]
        elif isinstance(order_meta, list):
            candidates = []
            for entry in order_meta:
                if isinstance(entry, dict):
                    name = entry.get("id") or entry.get("label") or entry.get("displayLabel")
                    if name and str(name).strip():
                        candidates.append(str(name).strip())
            prompts = candidates
        if not prompts:
            prompts = [key for key in payload.keys() if not key.startswith("__") and not key.isdigit()]
            prompts.sort()

        strengths = {}
        for index, prompt in enumerate(prompts):
            value = payload.get(prompt)
            if value is None:
                value = payload.get(str(index))
            try:
                strengths[prompt] = float(value)
            except (TypeError, ValueError):
                strengths[prompt] = 1.0

        return prompts, strengths


NODE_CLASS_MAPPINGS = {
    "ComicVerseTestNode": ComicVerseTestNode,
    "ComicAssetLibraryNode": ComicAssetLibraryNode,
    "LayoutTemplateSelectorNode": LayoutTemplateSelectorNode,
    "PromptStrengthSlider": PromptStrengthSlider,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicVerseTestNode": "ComicVerse Test Node",
    "ComicAssetLibraryNode": "Comic Assets Library",
    "LayoutTemplateSelectorNode": "排版模板选择 (LayoutTemplateSelector)",
    "PromptStrengthSlider": "Prompt weight slider",
}


