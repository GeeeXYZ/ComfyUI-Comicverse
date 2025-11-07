"""
Text Preview Node for ComicVerse custom nodes.

A simple node that displays STRING input without any output.
Useful for debugging and visualizing text data in the workflow.
"""

from typing import Dict, Any


class TextPreviewNode:
    """
    Display-only node that shows STRING input in a multiline text widget.
    No outputs - purely for visualization and debugging purposes.
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

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "preview_text"
    CATEGORY = "ComicVerse/Utils"
    OUTPUT_NODE = True  # Mark as output node so it executes even without downstream connections

    def preview_text(self, text: str = "") -> Dict[str, Any]:
        """
        Store the text for display. The frontend widget will show it.
        Returns the text in a dict so the UI can access it.
        """
        # Return the text in a format the frontend can access
        return {"ui": {"text": [text]}}


NODE_CLASS_MAPPINGS = {
    "TextPreviewNode": TextPreviewNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "TextPreviewNode": "Text Preview (Comic)",
}

