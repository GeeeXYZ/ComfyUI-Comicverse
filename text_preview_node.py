"""
Text Preview Node for ComicVerse custom nodes.

A simple node that displays STRING input and optionally passes it through.
Useful for debugging and visualizing text data in the workflow.
"""

from typing import Dict, Any, Tuple


class TextPreviewNode:
    """
    Preview node that displays STRING input in a multiline text widget.
    Also passes through the text as output for optional downstream connections.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "tooltip": "Connect any STRING output to preview its content",
                    },
                )
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "preview_text"
    CATEGORY = "ComicVerse/Utils"
    OUTPUT_NODE = True  # Mark as output node so it executes even without downstream connections

    def preview_text(self, text: str = "") -> Dict[str, Any]:
        """
        Store the text for display and pass it through as output.
        The frontend widget will show it, and it can be connected to other nodes.
        """
        # Return in the format AlekPet uses: {"string": [...]}
        # This is what onExecuted receives in the frontend
        return {"ui": {"string": [text]}, "result": (text,)}


NODE_CLASS_MAPPINGS = {
    "TextPreviewNode": TextPreviewNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "TextPreviewNode": "Text Preview | ComicVerse",
}

