"""
ComicVerse Nodes - ComfyUI Custom Nodes for Comic Layout
A collection of nodes for semi-automatic comic panel layout and design.

Author: ComicVerse Team
Version: 0.1
"""

from nodes.comic_asset_library import ComicAssetLibraryNode
from nodes.layout_template_selector import LayoutTemplateSelectorNode
from nodes.basic_layout_composer import BasicLayoutComposerNode
from nodes.speech_bubble_generator import SpeechBubbleGeneratorNode
from nodes.decorative_text_adder import DecorativeTextAdderNode

# Node class mappings - Required by ComfyUI
NODE_CLASS_MAPPINGS = {
    "ComicAssetLibrary": ComicAssetLibraryNode,
    "LayoutTemplateSelector": LayoutTemplateSelectorNode,
    "BasicLayoutComposer": BasicLayoutComposerNode,
    "SpeechBubbleGenerator": SpeechBubbleGeneratorNode,
    "DecorativeTextAdder": DecorativeTextAdderNode,
}

# Display name mappings - Optional but recommended
NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicAssetLibrary": "Comic Asset Library",
    "LayoutTemplateSelector": "Layout Template Selector",
    "BasicLayoutComposer": "Basic Layout Composer",
    "SpeechBubbleGenerator": "Speech Bubble Generator",
    "DecorativeTextAdder": "Decorative Text Adder",
}

# Web directory for additional resources - Optional
WEB_DIRECTORY = "./web"

# Optional: Add nodes to specific categories
CATEGORY_NAMES = {
    "ComicAssetLibrary": "ComicVerse/Library",
    "LayoutTemplateSelector": "ComicVerse/Library",
    "BasicLayoutComposer": "ComicVerse/Layout",
    "SpeechBubbleGenerator": "ComicVerse/Layout",
    "DecorativeTextAdder": "ComicVerse/Layout",
}
