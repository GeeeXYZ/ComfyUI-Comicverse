import os
import json
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import piexif

class LoadImageWithPrompt:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {"required":
                    {"image": (sorted(files), {"image_upload": True})},
                }

    CATEGORY = "ComicVerse/Image"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "positive", "negative")
    FUNCTION = "load_image"
    OUTPUT_NODE = True

    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        
        output_images = []
        output_masks = []
        
        positive_prompt = ""
        negative_prompt = ""
        prompt_graph = {}
        
        # Strategy 0: ComicVerse Metadata (Direct Read)
        # If the image was saved with SaveImageWithPromptInfo, we can read the prompts directly.
        if "ComicVerse_Positive" in img.info:
            try:
                # Try to decode as JSON (new format)
                positive_prompt = json.loads(img.info.get("ComicVerse_Positive", ""))
            except:
                # Fallback to raw string (old format or error)
                positive_prompt = img.info.get("ComicVerse_Positive", "")
            
            try:
                negative_prompt = json.loads(img.info.get("ComicVerse_Negative", ""))
            except:
                negative_prompt = img.info.get("ComicVerse_Negative", "")
                
            print(f"[ComicVerse] Loaded Prompts from Metadata for {image_path}")
            print(f"[ComicVerse] Positive: {positive_prompt[:50]}...")
            # If we found our custom metadata, we can skip the complex graph tracing
            # But we still might want to load the prompt graph for other purposes if needed?
            # For now, let's assume if we have this, we are good on prompts.
            # We still try to load prompt_graph just in case, but we won't overwrite our found prompts.
            pass
        
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

        # Strategy 2: Exif (WebP/JPEG)
        if not prompt_graph:
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

        # 2. Parse Positive and Negative Prompts
        # positive_prompt and negative_prompt are already initialized or set by Strategy 0
        
        if prompt_graph and not positive_prompt:
            positive_prompt, negative_prompt = self.extract_prompts(prompt_graph)

        # 3. Process Image
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
            
        return (image, mask.unsqueeze(0), positive_prompt, negative_prompt)

    def extract_prompts(self, prompt_graph):
        # Find KSampler nodes
        samplers = []
        for node_id, node_data in prompt_graph.items():
            class_type = node_data.get("class_type", "")
            if "KSampler" in class_type or "Sampler" in class_type:
                samplers.append((node_id, node_data))
        
        if not samplers:
            return "", ""

        # Use the last sampler (often the final refine/upscale step, or just the last added)
        # Sorting by ID is a heuristic, assuming higher ID = later addition
        samplers.sort(key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
        target_sampler_id, target_sampler = samplers[-1]

        positive_text = self.trace_input(prompt_graph, target_sampler, "positive")
        negative_text = self.trace_input(prompt_graph, target_sampler, "negative")
        
        return positive_text, negative_text

    def trace_input(self, graph, current_node, input_name, visited=None):
        if visited is None:
            visited = set()
        
        node_id = None
        # Find the node ID of current_node (reverse lookup or passed in? simpler to pass data)
        # But we need ID to track visited.
        # Let's assume current_node is the data dict. We need to find its ID or pass it.
        # Refactoring to pass ID.
        return self._trace_recursive(graph, current_node, input_name, visited)

    def _trace_recursive(self, graph, node_data, input_name, visited):
        inputs = node_data.get("inputs", {})
        if input_name not in inputs:
            return ""
            
        link = inputs[input_name]
        # Link format in 'prompt' JSON: [node_id, slot_index]
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
        # CLIPTextEncode, Text Multiline, ShowText, etc.
        if "CLIPTextEncode" in class_type:
            # Usually 'text' input contains the string or a link to a string primitive
            return self._get_text_from_inputs(graph, source_node, "text", visited)
        
        if class_type in ["Text Multiline", "ShowText|pysssss", "TextPreviewNode", "ShowText"]:
             # These often hold text in 'text' or 'string' widgets/inputs
             return self._get_text_from_inputs(graph, source_node, "text", visited) or \
                    self._get_text_from_inputs(graph, source_node, "string", visited)

        # 2. Conditioning/Flow Nodes
        if "ConditioningConcat" in class_type or "ConditioningCombine" in class_type:
            # Recurse on both inputs
            t1 = self._trace_recursive(graph, source_node, "conditioning_to", visited)
            t2 = self._trace_recursive(graph, source_node, "conditioning_from", visited)
            return f"{t1} {t2}".strip()
            
        if "ControlNetApply" in class_type:
            # Pass through 'positive' or 'negative' (usually same name as input)
            # But here we are tracing UP from a conditioning input.
            # ControlNetApply outputs conditioning. It has 'positive' and 'negative' INPUTS.
            # We need to know which output slot we are connected to? 
            # The 'prompt' JSON doesn't easily show output slots in the link (the link is [id, slot]).
            # But we are tracing from the INPUT of the downstream node.
            # The downstream node said: "My 'positive' input comes from SourceNode output X".
            # We assume if we asked for 'positive', we want the 'positive' input of the ControlNet node.
            # This is a simplification.
            return self._trace_recursive(graph, source_node, "positive", visited) if input_name == "positive" else \
                   self._trace_recursive(graph, source_node, "negative", visited)

        if "Reroute" in class_type or "Node" in class_type: # Generic pass-through
             # Reroute usually has one input, often named same as output or just '*'
             # We try to find ANY input that looks like a link
             for key, val in source_node.get("inputs", {}).items():
                 if isinstance(val, list): # It's a link
                     return self._trace_recursive(graph, source_node, key, visited)

        # 3. String Primitives / Joiners
        if "JoinStrings" in class_type or "JoinStringMulti" in class_type:
             # Concatenate all string inputs
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
        if isinstance(val, list): # Link to another node (e.g. primitive string node)
            return self._trace_recursive(graph, node_data, input_name, visited)
        return str(val)

    @classmethod
    def IS_CHANGED(s, image):
        image_path = folder_paths.get_annotated_filepath(image)
        m = os.path.getmtime(image_path)
        return m

    @classmethod
    def VALIDATE_INPUTS(s, image):
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True

NODE_CLASS_MAPPINGS = {
    "LoadImageWithPrompt": LoadImageWithPrompt
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageWithPrompt": "Load Image with Prompt"
}
