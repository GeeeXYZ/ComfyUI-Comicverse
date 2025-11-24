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
import base64

try:
    from server import PromptServer  # ComfyUI server messaging
except Exception:  # pragma: no cover
    PromptServer = None  # type: ignore


# Persistent in-process cache for library images per node instance
_LIBRARY_CACHE: dict[str, List[torch.Tensor]] = {}
_LIBRARY_HASHES: dict[str, List[str]] = {}
_PENDING_DELETIONS: dict[str, List[int]] = {}  # Track pending deletions per node

# Lightweight caches for encoded thumbnails and previews keyed by image hash
_THUMB_CACHE: dict[str, str] = {}
_PREVIEW_CACHE: dict[str, str] = {}
_LAST_SENT_COUNT: dict[str, int] = {}

def _encode_image_data_url(img, *, prefer_webp: bool, jpeg_ok: bool, quality: int = 80) -> tuple[str, str]:
    """
    Encode PIL.Image to a data URL. Prefer WebP when available; fall back to JPEG (if no alpha)
    or PNG. Returns (data_url, mime).
    """
    mime = "image/png"
    buffer = BytesIO()
    mode = img.mode
    has_alpha = mode in ("RGBA", "LA") or ("transparency" in img.info)
    # Try WebP first if requested
    if prefer_webp:
        try:
            img.save(buffer, format="WEBP", quality=quality, method=4)
            mime = "image/webp"
            data = buffer.getvalue()
            return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii"), mime
        except Exception:
            buffer = BytesIO()
            # fall through to JPEG/PNG
    # Try JPEG if allowed and no alpha
    if jpeg_ok and not has_alpha:
        try:
            # Ensure RGB for JPEG
            rgb = img.convert("RGB") if img.mode != "RGB" else img
            rgb.save(buffer, format="JPEG", quality=quality, optimize=True)
            mime = "image/jpeg"
            data = buffer.getvalue()
            return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii"), mime
        except Exception:
            buffer = BytesIO()
    # Fallback PNG (supports alpha, lossless)
    try:
        img.save(buffer, format="PNG")
        mime = "image/png"
        data = buffer.getvalue()
        return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii"), mime
    except Exception:
        # As a last resort, return an empty 1x1 PNG data URL
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/ee1GfUAAAAASUVORK5CYII=", "image/png"


class ComicAssetLibraryNode:
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "output_count": ("INT", {"default": 2, "min": 1, "max": 6}),
                "selected_indices": ("STRING", {"default": "", "multiline": False, "placeholder": "选中顺序：如 2,0,1"}),
                "pending_deletions": ("STRING", {"default": "", "multiline": False, "placeholder": "待删除索引（自动填充）"}),
            },
            "optional": {
                "image_input_a": ("IMAGE", {}),
                "image_input_b": ("IMAGE", {}),
            },
            "hidden": {
                "unique_id": ("UNIQUE_ID", {}),
            },
        }

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

    def run(self, output_count: int, selected_indices: str = "", image_input_a=None, image_input_b=None, unique_id: str = "", pending_deletions: str = "", **kwargs):
        # Collect connected IMAGE inputs (two ports), each may be a batch [B,H,W,C]
        image_batches = []
        if image_input_a is not None:
            image_batches.append(image_input_a)
        if image_input_b is not None:
            image_batches.append(image_input_b)

        if len(image_batches) == 0:
            raise ValueError("请至少连接1个 IMAGE 输入到漫画素材库节点 (ComicAssetLibraryNode)。")

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
        
        # Track actual deletion indices for later index adjustment and delta payloads
        requested_deletions: List[int] = []
        actual_deletions: List[int] = []
        
        # Record pre-deletion count BEFORE any modifications
        pre_deletion_count = len(lib_list)
        
        # Process pending deletions first (before adding new images)
        if pending_deletions:
            requested_deletions = [int(i.strip()) for i in pending_deletions.split(",") if i.strip().isdigit()]
            # Delete in reverse order to avoid index shifting issues
            for idx in sorted(requested_deletions, reverse=True):
                if 0 <= idx < len(lib_list):
                    lib_list.pop(idx)
                    lib_hashes.pop(idx)
                    actual_deletions.append(idx)
            # We stored actual deletions in descending order; normalize to ascending for later logic
            actual_deletions.sort()
        
        # Record count after deletion but before adding new images
        post_deletion_count = len(lib_list)
        
        # Adjust selected_indices after deletions: selected indices are based on pre-deletion list
        # Need to map them to post-deletion list positions
        # Do this BEFORE adding new images to avoid confusion
        if actual_deletions and selected_indices:
            deletion_indices_set = set(actual_deletions)
            # Parse selection indices assuming they refer to pre-deletion list
            selected_before = self._parse_indices(selected_indices, pre_deletion_count)
            if selected_before:
                adjusted_selected = []
                for sel_idx in selected_before:
                    # Skip if this index was deleted
                    if sel_idx in deletion_indices_set:
                        continue
                    # Calculate adjustment: for each deletion index < sel_idx, reduce by 1
                    adjustment = sum(1 for d in actual_deletions if d < sel_idx)
                    new_idx = sel_idx - adjustment
                    if 0 <= new_idx < post_deletion_count:
                        adjusted_selected.append(new_idx)
                # Update selected_indices with adjusted indices
                selected_indices = ",".join(map(str, adjusted_selected)) if adjusted_selected else ""
        
        # Hard cap to avoid unbounded memory
        max_cache = 30
        popped_count = 0
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
                popped_count += 1
        
        # Adjust selected_indices for cache eviction (FIFO)
        if popped_count > 0 and selected_indices:
            # Parse current indices (which might have been adjusted by pending deletions)
            # Note: We use a large max_len here because we are tracking indices relative to the state 
            # BEFORE the pops in this loop, but AFTER pending deletions. 
            # Actually, it's easier to parse based on the list size at the start of this loop?
            # No, the indices are valid for the list as it was *before* we started popping in this loop.
            # But we are adding and popping interleaved.
            # Wait, the logic: "indices relative to the start of the list".
            # If we pop 0, everyone shifts down by 1.
            # So simply subtracting popped_count from the index is correct, 
            # assuming the index referred to the position *before* these specific pops.
            # Yes, selected_indices passed into this block refers to the list state after pending deletions.
            
            # We need to parse it first.
            # We can use a dummy max_len because we just want the integers.
            current_indices = self._parse_indices(selected_indices, 999999) or []
            adjusted_indices = []
            for idx in current_indices:
                new_idx = idx - popped_count
                if new_idx >= 0:
                    adjusted_indices.append(new_idx)
            selected_indices = ",".join(map(str, adjusted_indices)) if adjusted_indices else ""

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
                key = unique_id or "global"
                prev_count = _LAST_SENT_COUNT.get(key, 0)
                new_count = len(lib_list)

                # If first time, or counts don't make sense (overflow eviction, etc.), send full
                full_sync_needed = (prev_count == 0) or (popped_count > 0)
                if not full_sync_needed:
                    if new_count < prev_count and not actual_deletions:
                        # count shrunk but we have no explicit deletion info -> fall back to full
                        full_sync_needed = True

                if full_sync_needed:
                    thumbs = []
                    max_send = min(120, new_count)
                    max_preview = min(30, new_count)
                    for i in range(max_send):
                        b = lib_list[i]
                        h, w, c = b.shape[1:]
                        img_uint8 = (b[0].clamp(0, 1) * 255).byte().cpu().numpy()
                        from PIL import Image
                        img = Image.fromarray(img_uint8, mode='RGBA' if c == 4 else 'RGB')
                        digest = lib_hashes[i] if i < len(lib_hashes) else None

                        thumb_w = 96
                        scale = thumb_w / float(w)
                        thumb_h = max(1, int(h * scale))
                        if digest and digest in _THUMB_CACHE:
                            thumb_data_url = _THUMB_CACHE[digest]
                        else:
                            thumb_img = img.resize((thumb_w, thumb_h), Image.BILINEAR)
                            data_url, _ = _encode_image_data_url(thumb_img, prefer_webp=True, jpeg_ok=(c == 3), quality=80)
                            thumb_data_url = data_url
                            if digest:
                                _THUMB_CACHE[digest] = thumb_data_url

                        entry = {"w": thumb_w, "h": thumb_h, "data": thumb_data_url}
                        if i < max_preview:
                            if digest and digest in _PREVIEW_CACHE:
                                entry["preview"] = _PREVIEW_CACHE[digest]
                            else:
                                max_preview_dim = 1024
                                if w > h:
                                    preview_w = min(max_preview_dim, w)
                                    preview_h = max(1, int(h * preview_w / w))
                                else:
                                    preview_h = min(max_preview_dim, h)
                                    preview_w = max(1, int(w * preview_h / h))
                                preview_img = img.resize((preview_w, preview_h), Image.BILINEAR)
                                data_url, _ = _encode_image_data_url(preview_img, prefer_webp=True, jpeg_ok=(c == 3), quality=80)
                                entry["preview"] = data_url
                                if digest:
                                    _PREVIEW_CACHE[digest] = data_url
                        thumbs.append(entry)

                    # guard caches
                    if len(_THUMB_CACHE) > 500:
                        _THUMB_CACHE.clear()
                    if len(_PREVIEW_CACHE) > 500:
                        _PREVIEW_CACHE.clear()

                    Payload = {
                        "node_id": unique_id,
                        "mode": "full",
                        "thumbs": thumbs,
                        "count": new_count,
                        "selected": self._parse_indices(selected_indices, len(lib_list)) or [],
                    }
                    PromptServer.instance.send_sync("comicverse.library.previews", Payload)
                    _LAST_SENT_COUNT[key] = new_count
                else:
                    # delta mode: send deletions and appends
                    deletes_count = len(actual_deletions)
                    adds_count = max(0, new_count - (prev_count - deletes_count))
                    # additions are assumed appended at the end of lib_list
                    adds: List[Dict[str, Any]] = []
                    if adds_count > 0:
                        start = max(0, new_count - adds_count)
                        end = new_count
                        max_preview = min(30, new_count)
                        for i in range(start, end):
                            b = lib_list[i]
                            h, w, c = b.shape[1:]
                            img_uint8 = (b[0].clamp(0, 1) * 255).byte().cpu().numpy()
                            from PIL import Image
                            img = Image.fromarray(img_uint8, mode='RGBA' if c == 4 else 'RGB')
                            digest = lib_hashes[i] if i < len(lib_hashes) else None

                            thumb_w = 96
                            scale = thumb_w / float(w)
                            thumb_h = max(1, int(h * scale))
                            if digest and digest in _THUMB_CACHE:
                                thumb_data_url = _THUMB_CACHE[digest]
                            else:
                                thumb_img = img.resize((thumb_w, thumb_h), Image.BILINEAR)
                                data_url, _ = _encode_image_data_url(thumb_img, prefer_webp=True, jpeg_ok=(c == 3), quality=80)
                                thumb_data_url = data_url
                                if digest:
                                    _THUMB_CACHE[digest] = thumb_data_url

                            entry = {"w": thumb_w, "h": thumb_h, "data": thumb_data_url}
                            if i < max_preview:
                                if digest and digest in _PREVIEW_CACHE:
                                    entry["preview"] = _PREVIEW_CACHE[digest]
                                else:
                                    max_preview_dim = 1024
                                    if w > h:
                                        preview_w = min(max_preview_dim, w)
                                        preview_h = max(1, int(h * preview_w / w))
                                    else:
                                        preview_h = min(max_preview_dim, h)
                                        preview_w = max(1, int(w * preview_h / h))
                                    preview_img = img.resize((preview_w, preview_h), Image.BILINEAR)
                                    data_url, _ = _encode_image_data_url(preview_img, prefer_webp=True, jpeg_ok=(c == 3), quality=80)
                                    entry["preview"] = data_url
                                    if digest:
                                        _PREVIEW_CACHE[digest] = data_url
                            adds.append(entry)

                    Payload = {
                        "node_id": unique_id,
                        "mode": "delta",
                        "removes": sorted([i for i in actual_deletions if 0 <= i < prev_count], reverse=True),
                        "adds": adds,
                        "count": new_count,
                        "selected": self._parse_indices(selected_indices, len(lib_list)) or [],
                    }
                    PromptServer.instance.send_sync("comicverse.library.previews", Payload)
                    _LAST_SENT_COUNT[key] = new_count
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
    "ComicAssetLibraryNode": ComicAssetLibraryNode,
    "LayoutTemplateSelectorNode": LayoutTemplateSelectorNode,
    "PromptStrengthSlider": PromptStrengthSlider,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicAssetLibraryNode": "Comic Assets Library | ComicVerse",
    "LayoutTemplateSelectorNode": "Layout Template Selector | ComicVerse",
    "PromptStrengthSlider": "Prompt Weight Slider | ComicVerse",
}


