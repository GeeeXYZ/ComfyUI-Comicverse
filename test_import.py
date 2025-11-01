#!/usr/bin/env python3
"""
Test script to verify ComicVerse nodes can be imported correctly
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing ComicVerse Node Imports...")
print("=" * 60)

# Test 1: Import __init__.py
print("\n1. Testing __init__.py import...")
try:
    from __init__ import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    print(f"   ✓ NODE_CLASS_MAPPINGS loaded: {len(NODE_CLASS_MAPPINGS)} nodes")
    print(f"   ✓ NODE_DISPLAY_NAME_MAPPINGS loaded: {len(NODE_DISPLAY_NAME_MAPPINGS)} nodes")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 2: Import each node class
print("\n2. Testing individual node imports...")
nodes = [
    ("ComicAssetLibraryNode", "nodes.comic_asset_library"),
    ("LayoutTemplateSelectorNode", "nodes.layout_template_selector"),
    ("BasicLayoutComposerNode", "nodes.basic_layout_composer"),
    ("SpeechBubbleGeneratorNode", "nodes.speech_bubble_generator"),
    ("DecorativeTextAdderNode", "nodes.decorative_text_adder"),
]

for class_name, module_name in nodes:
    try:
        module = __import__(module_name, fromlist=[class_name])
        node_class = getattr(module, class_name)
        print(f"   ✓ {class_name} imported successfully")

        # Check required attributes
        if hasattr(node_class, 'INPUT_TYPES'):
            print(f"     - INPUT_TYPES: {type(node_class.INPUT_TYPES)}")
        if hasattr(node_class, 'RETURN_TYPES'):
            print(f"     - RETURN_TYPES: {node_class.RETURN_TYPES}")
        if hasattr(node_class, 'FUNCTION'):
            print(f"     - FUNCTION: {node_class.FUNCTION}")

    except Exception as e:
        print(f"   ✗ {class_name} import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Test 3: Verify NODE_CLASS_MAPPINGS contains all nodes
print("\n3. Verifying NODE_CLASS_MAPPINGS consistency...")
expected_keys = {
    "ComicAssetLibrary",
    "LayoutTemplateSelector",
    "BasicLayoutComposer",
    "SpeechBubbleGenerator",
    "DecorativeTextAdder",
}

actual_keys = set(NODE_CLASS_MAPPINGS.keys())
if expected_keys == actual_keys:
    print(f"   ✓ All {len(expected_keys)} nodes registered correctly")
else:
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if missing:
        print(f"   ✗ Missing nodes: {missing}")
    if extra:
        print(f"   ✗ Extra nodes: {extra}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All tests passed! Nodes are ready for ComfyUI.")
print("=" * 60)
