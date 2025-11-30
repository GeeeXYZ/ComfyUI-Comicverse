import os
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths
import random

class SaveImageWithPromptInfo:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "positive_text": ("STRING", {"forceInput": True}),
                "negative_text": ("STRING", {"forceInput": True}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "ComicVerse/Image"

    def save_images(self, images, filename_prefix="ComfyUI", positive_text="", negative_text="", prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = PngInfo()

            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            # Add ComicVerse specific metadata
            if positive_text:
                # Use json.dumps to ensure ASCII-safe encoding for Unicode characters
                metadata.add_text("ComicVerse_Positive", json.dumps(positive_text))
                print(f"[ComicVerse] Saved Positive Prompt: {positive_text[:50]}...")
            if negative_text:
                metadata.add_text("ComicVerse_Negative", json.dumps(negative_text))
                print(f"[ComicVerse] Saved Negative Prompt: {negative_text[:50]}...")

            file = f"{filename}_{counter:05}_.png"
            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results }, "result": (images,) }

NODE_CLASS_MAPPINGS = {
    "SaveImageWithPromptInfo": SaveImageWithPromptInfo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithPromptInfo": "Save Image with Prompt Info"
}
