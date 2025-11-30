import os
import json
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import piexif
import random

# Global state to track playback index for each node instance
# Key: unique_id, Value: current_index
_FOLDER_STATE = {}

class LoadImageFolderWithPrompt:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "sort_method": (["sequential", "random"], {"default": "sequential"}),
                "image_index": ("INT", {"default": -1, "min": -1, "step": 1, "tooltip": "-1 for auto/sequential, >=0 to lock specific index"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    CATEGORY = "ComicVerse/Image"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("image", "mask", "positive", "negative", "filename", "current_index")
    FUNCTION = "load_image"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(s, **kwargs):
        # Always re-run to support sequential/random playback
        return float("nan")

    def load_image(self, folder_path, sort_method, image_index, unique_id):
        if not folder_path or not os.path.isdir(folder_path):
            if not folder_path:
                raise FileNotFoundError("Please provide a folder path.")
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Get all image files
        valid_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}
        files = [
            f for f in os.listdir(folder_path) 
            if os.path.isfile(os.path.join(folder_path, f)) 
            and os.path.splitext(f)[1].lower() in valid_extensions
        ]
        
        if not files:
            raise FileNotFoundError(f"No valid images found in folder: {folder_path}")

        # Sort files to ensure consistent order for sequential playback
        files.sort()

        # Determine which file to load
        current_index = 0
        
        if sort_method == "random":
            current_index = random.randint(0, len(files) - 1)
            file_name = files[current_index]
        else: # sequential
            # Get state for this node instance
            state = _FOLDER_STATE.get(unique_id, {})
            
            if image_index >= 0:
                # Locked mode: User specified a specific index
                current_index = image_index
                
                # Update internal state so if user switches back to -1, it continues from here
                # We set the state to the NEXT image, so if they unlock, it plays the next one
                state["current_index"] = (current_index + 1) % len(files)
            else:
                # Auto mode: Use internal state
                current_index = state.get("current_index", 0)
                
                # Update state for next run
                state["current_index"] = (current_index + 1) % len(files)

            _FOLDER_STATE[unique_id] = state
            
            # Ensure index is within bounds
            if current_index >= len(files):
                current_index = current_index % len(files)
            
            file_name = files[current_index]

        image_path = os.path.join(folder_path, file_name)
        img = Image.open(image_path)
        
        positive_prompt = ""
        negative_prompt = ""
        prompt_graph = {}

        # Strategy 0: ComicVerse Metadata (Direct Read)
        if "ComicVerse_Positive" in img.info:
            try:
                positive_prompt = json.loads(img.info.get("ComicVerse_Positive", ""))
            except:
                positive_prompt = img.info.get("ComicVerse_Positive", "")
                
            try:
                negative_prompt = json.loads(img.info.get("ComicVerse_Negative", ""))
            except:
                negative_prompt = img.info.get("ComicVerse_Negative", "")
                
            print(f"[ComicVerse] Loaded Prompts from Metadata for {file_name}")
            print(f"[ComicVerse] Positive: {positive_prompt[:50]}...")

        # Strategy 1: Standard PNG Info
        if "prompt" in img.info:
            try:
                raw_prompt = img.info["prompt"]
                if isinstance(raw_prompt, str):
                    prompt_graph = json.loads(raw_prompt)
                elif isinstance(raw_prompt, dict):
                    prompt_graph = raw_prompt
            except Exception as e:
                print(f"Error extracting prompt from PNG info: {e}")
            try:
                if "exif" in img.info:
                    exif_dict = piexif.load(img.info["exif"])
                    if piexif.ExifIFD.UserComment in exif_dict.get("Exif", {}):
                        user_comment = exif_dict["Exif"][piexif.ExifIFD.UserComment]
                        try:
                            if isinstance(user_comment, bytes):
                                if user_comment.startswith(b'UNICODE\0\0'):
                                    json_str = user_comment[8:].decode('utf-16be').strip()
                                else:
                                    json_str = user_comment.decode('utf-8')
                                prompt_graph = json.loads(json_str)
                        except:
                            pass
                    
                    if not prompt_graph and "0th" in exif_dict:
                        if 271 in exif_dict["0th"]: # UserComment/Make/Model usage in some workflows
                            try:
                                val = exif_dict["0th"][271]
                                if isinstance(val, bytes):
                                    val = val.decode('utf-8')
                                if val.startswith("Prompt:"):
                                    val = val[7:]
                                prompt_graph = json.loads(val)
                            except:
                                pass
            except Exception:
                pass

        if prompt_graph and not positive_prompt:
            positive_prompt, negative_prompt = self.extract_prompts(prompt_graph)

        # --- Image Processing ---
        img = ImageOps.exif_transpose(img)
        if img.mode == 'I':
            img = img.point(lambda i: i * (1 / 255))
        image = img.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        
        if 'A' in img.getbands():
            mask = np.array(img.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            
        return (image, mask.unsqueeze(0), positive_prompt, negative_prompt, file_name, current_index)

    def extract_prompts(self, prompt_graph):
        # Find KSampler nodes
        samplers = []
        for node_id, node_data in prompt_graph.items():
            class_type = node_data.get("class_type", "")
            if "KSampler" in class_type or "Sampler" in class_type:
                samplers.append((node_id, node_data))
        
        if not samplers:
            return "", ""

        # Use the last sampler
        samplers.sort(key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
        target_sampler_id, target_sampler = samplers[-1]

        positive_text = self.trace_input(prompt_graph, target_sampler, "positive")
        negative_text = self.trace_input(prompt_graph, target_sampler, "negative")
        
        return positive_text, negative_text

    def trace_input(self, graph, current_node, input_name, visited=None):
        if visited is None:
            visited = set()
        return self._trace_recursive(graph, current_node, input_name, visited)

    def _trace_recursive(self, graph, node_data, input_name, visited):
        inputs = node_data.get("inputs", {})
        if input_name not in inputs:
            return ""
            
        link = inputs[input_name]
        if not isinstance(link, list) or len(link) < 1:
            return ""
            
        source_id = str(link[0])
        if source_id in visited:
            return ""
        visited.add(source_id)
        
        if source_id not in graph:
            return ""
            
        source_node = graph[source_id]
        class_type = source_node.get("class_type", "")
        
        # 1. Text Source Nodes
        if "CLIPTextEncode" in class_type:
            return self._get_text_from_inputs(graph, source_node, "text", visited)
        
        if class_type in ["Text Multiline", "ShowText|pysssss", "TextPreviewNode", "ShowText"]:
             return self._get_text_from_inputs(graph, source_node, "text", visited) or \
                    self._get_text_from_inputs(graph, source_node, "string", visited)

        # 2. Conditioning/Flow Nodes
        if "ConditioningConcat" in class_type or "ConditioningCombine" in class_type:
            t1 = self._trace_recursive(graph, source_node, "conditioning_to", visited)
            t2 = self._trace_recursive(graph, source_node, "conditioning_from", visited)
            return f"{t1} {t2}".strip()
            
        if "ControlNetApply" in class_type:
            return self._trace_recursive(graph, source_node, "positive", visited) if input_name == "positive" else \
                   self._trace_recursive(graph, source_node, "negative", visited)

        if "Reroute" in class_type or "Node" in class_type:
             for key, val in source_node.get("inputs", {}).items():
                 if isinstance(val, list):
                     return self._trace_recursive(graph, source_node, key, visited)

        # 3. String Primitives / Joiners
        if "JoinStrings" in class_type or "JoinStringMulti" in class_type:
             parts = []
             for key in source_node.get("inputs", {}):
                 if "string" in key or "text" in key:
                     parts.append(self._get_text_from_inputs(graph, source_node, key, visited))
             return ", ".join([p for p in parts if p])

        return ""

    def _get_text_from_inputs(self, graph, node_data, input_name, visited):
        inputs = node_data.get("inputs", {})
        if input_name not in inputs:
            return ""
        
        val = inputs[input_name]
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            return self._trace_recursive(graph, node_data, input_name, visited)
        return str(val)

NODE_CLASS_MAPPINGS = {
    "LoadImageFolderWithPrompt": LoadImageFolderWithPrompt
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageFolderWithPrompt": "Load Image Folder with Prompt"
}
