#!/usr/bin/env python3
"""
Quick check script - verifies file structure without importing ComfyUI-dependent modules
"""

import os
import ast

print("=" * 60)
print("ComicVerse Node Structure Check")
print("=" * 60)

# Check 1: Required files exist
print("\n1. Checking required files...")
required_files = {
    "__init__.py": "Main module registration",
    "nodes/__init__.py": "Nodes package",
    "nodes/comic_asset_library.py": "Node 1: Asset Library",
    "nodes/layout_template_selector.py": "Node 2: Template Selector",
    "nodes/basic_layout_composer.py": "Node 3: Layout Composer",
    "nodes/speech_bubble_generator.py": "Node 4: Speech Bubble",
    "nodes/decorative_text_adder.py": "Node 5: Text Adder",
}

all_exist = True
for filepath, description in required_files.items():
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {filepath}")
    all_exist = all_exist and exists

if not all_exist:
    print("\n✗ ERROR: Missing required files!")
    exit(1)

# Check 2: __init__.py structure
print("\n2. Checking __init__.py structure...")
try:
    with open("__init__.py", "r") as f:
        content = f.read()

    checks = {
        "NODE_CLASS_MAPPINGS": "Node class mappings",
        "NODE_DISPLAY_NAME_MAPPINGS": "Display name mappings",
        "ComicAssetLibraryNode": "Comic Asset Library node",
        "LayoutTemplateSelectorNode": "Layout Template Selector node",
        "BasicLayoutComposerNode": "Basic Layout Composer node",
        "SpeechBubbleGeneratorNode": "Speech Bubble Generator node",
        "DecorativeTextAdderNode": "Decorative Text Adder node",
    }

    for check_str, description in checks.items():
        if check_str in content:
            print(f"  ✓ {description} found")
        else:
            print(f"  ✗ {description} NOT FOUND")
            all_exist = False

except Exception as e:
    print(f"  ✗ Error reading __init__.py: {e}")
    all_exist = False

# Check 3: Node files have required class definitions
print("\n3. Checking node classes...")
node_classes = {
    "nodes/comic_asset_library.py": "ComicAssetLibraryNode",
    "nodes/layout_template_selector.py": "LayoutTemplateSelectorNode",
    "nodes/basic_layout_composer.py": "BasicLayoutComposerNode",
    "nodes/speech_bubble_generator.py": "SpeechBubbleGeneratorNode",
    "nodes/decorative_text_adder.py": "DecorativeTextAdderNode",
}

for filepath, class_name in node_classes.items():
    try:
        with open(filepath, "r") as f:
            content = f.read()

        # Parse to check syntax
        ast.parse(content)

        # Check for class definition
        if f"class {class_name}" in content:
            print(f"  ✓ {class_name} class defined")
        else:
            print(f"  ✗ {class_name} class NOT FOUND")

        # Check for INPUT_TYPES
        if "INPUT_TYPES" in content:
            print(f"    ✓ INPUT_TYPES method found")
        else:
            print(f"    ✗ INPUT_TYPES method missing")

        # Check for RETURN_TYPES
        if "RETURN_TYPES" in content:
            print(f"    ✓ RETURN_TYPES found")
        else:
            print(f"    ✗ RETURN_TYPES missing")

    except SyntaxError as e:
        print(f"  ✗ {class_name} has syntax error: {e}")
        all_exist = False
    except Exception as e:
        print(f"  ✗ Error checking {class_name}: {e}")
        all_exist = False

# Summary
print("\n" + "=" * 60)
if all_exist:
    print("✓ All checks passed! Node structure is correct.")
    print("\nNext steps:")
    print("1. Copy this folder to your ComfyUI/custom_nodes/ directory")
    print("2. Restart ComfyUI")
    print("3. Search for 'Comic' in the node panel")
else:
    print("✗ Some checks failed. Please review the errors above.")
    exit(1)

print("=" * 60)
