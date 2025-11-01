#!/usr/bin/env python3
"""
ComicVerse Node Installation Diagnostic Script
Checks for common issues that prevent nodes from appearing in ComfyUI
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {filepath}")
    return exists

def check_python_syntax(filepath):
    """Check if a Python file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, filepath, 'exec')
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    print("=" * 60)
    print("ComicVerse Node Installation Diagnostic")
    print("=" * 60)
    print()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Node Directory: {base_dir}")
    print()

    # Check required files
    print("1. Checking Required Files:")
    print("-" * 60)
    required_files = [
        ("__init__.py", "Main registration file"),
        ("nodes/__init__.py", "Nodes package init"),
        ("nodes/comic_asset_library.py", "Node 1: Comic Asset Library"),
        ("nodes/layout_template_selector.py", "Node 2: Layout Template Selector"),
        ("nodes/basic_layout_composer.py", "Node 3: Basic Layout Composer"),
        ("nodes/speech_bubble_generator.py", "Node 4: Speech Bubble Generator"),
        ("nodes/decorative_text_adder.py", "Node 5: Decorative Text Adder"),
    ]

    all_files_exist = True
    for filename, description in required_files:
        filepath = os.path.join(base_dir, filename)
        exists = check_file_exists(filepath, description)
        all_files_exist = all_files_exist and exists

    print()

    if not all_files_exist:
        print("✗ ERROR: Some required files are missing!")
        print("  Please ensure you copied the complete ComicVerse-Nodes folder.")
        return False

    # Check Python syntax
    print("2. Checking Python Syntax:")
    print("-" * 60)
    all_syntax_ok = True
    for filename, description in required_files:
        if filename.endswith('.py'):
            filepath = os.path.join(base_dir, filename)
            is_ok, msg = check_python_syntax(filepath)
            status = "✓" if is_ok else "✗"
            print(f"{status} {description}: {msg}")
            all_syntax_ok = all_syntax_ok and is_ok

    print()

    if not all_syntax_ok:
        print("✗ ERROR: Syntax errors found in Python files!")
        return False

    # Check __init__.py content
    print("3. Checking __init__.py Content:")
    print("-" * 60)
    init_file = os.path.join(base_dir, "__init__.py")
    try:
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if "NODE_CLASS_MAPPINGS" not in content:
            print("✗ NODE_CLASS_MAPPINGS not found in __init__.py")
            return False
        else:
            print("✓ NODE_CLASS_MAPPINGS found")

        if "NODE_DISPLAY_NAME_MAPPINGS" not in content:
            print("✗ NODE_DISPLAY_NAME_MAPPINGS not found in __init__.py")
            return False
        else:
            print("✓ NODE_DISPLAY_NAME_MAPPINGS found")

    except Exception as e:
        print(f"✗ Error reading __init__.py: {e}")
        return False

    print()
    print("=" * 60)
    print("✓ All checks passed!")
    print("=" * 60)
    print()
    print("If nodes still don't appear in ComfyUI:")
    print()
    print("1. Ensure this folder is in ComfyUI's custom_nodes directory")
    print("2. Restart ComfyUI completely (stop and start the server)")
    print("3. Check ComfyUI console for error messages")
    print("4. Verify you're using ComfyUI (not other UIs like AUTOMATIC1111)")
    print()
    print("Expected ComfyUI custom_nodes path examples:")
    print("  - Windows: C:\\ComfyUI\\custom_nodes\\")
    print("  - Mac/Linux: ~/ComfyUI/custom_nodes/")
    print("  - Portable: ComfyUI-Windows-Portable\\ComfyUI\\custom_nodes\\")
    print()

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
