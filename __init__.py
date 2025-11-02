"""
ComicVerse Nodes - ComfyUI Custom Nodes for Comic Layout
Comic Assets Library with delete/pending deletion feature
"""

from .comicverse_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./js"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
