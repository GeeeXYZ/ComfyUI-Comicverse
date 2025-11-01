#!/usr/bin/env python3
"""
Debug script to check ComfyUI custom node loading
Run this inside your ComfyUI Python environment
"""

import sys
import os

print("=" * 70)
print("ComfyUI Node Loading Debug")
print("=" * 70)

# Add ComfyUI paths
comfy_path = None
for p in sys.path:
    if 'ComfyUI' in p:
        comfy_path = p
        break

if not comfy_path:
    # Try common locations
    possible_paths = [
        '/path/to/ComfyUI',
        'C:/ComfyUI',
        'C:/ComfyUI-Windows-Portable/ComfyUI',
        'ComfyUI',
    ]
    print("\n⚠ ComfyUI not found in Python path")
    print("Please run this script with the same Python that ComfyUI uses:")
    print("  - Activate ComfyUI's virtual environment")
    print("  - Then run: python debug_nodes.py")
else:
    print(f"\n✓ ComfyUI found at: {comfy_path}")

# Check custom_nodes directory
custom_nodes_path = os.path.join(comfy_path, 'custom_nodes') if comfy_path else None
if custom_nodes_path and os.path.exists(custom_nodes_path):
    print(f"\n✓ Custom nodes directory: {custom_nodes_path}")

    # Check our node directory
    our_node_path = os.path.join(custom_nodes_path, 'ComfyUI-ComicVerse')
    if os.path.exists(our_node_path):
        print(f"\n✓ ComicVerse node found at: {our_node_path}")

        # List files
        print("\n📁 Files in ComicVerse directory:")
        for file in sorted(os.listdir(our_node_path)):
            print(f"  - {file}")

        # Check __init__.py
        init_file = os.path.join(our_node_path, '__init__.py')
        if os.path.exists(init_file):
            print(f"\n✓ __init__.py exists")

            # Try to load it
            try:
                sys.path.insert(0, our_node_path)
                import __init__
                print(f"✓ __init__.py imported successfully")

                if hasattr(__init__, 'NODE_CLASS_MAPPINGS'):
                    print(f"\n✓ NODE_CLASS_MAPPINGS found with {len(__init__.NODE_CLASS_MAPPINGS)} nodes:")
                    for key in __init__.NODE_CLASS_MAPPINGS.keys():
                        print(f"  - {key}")
                else:
                    print("\n✗ NODE_CLASS_MAPPINGS not found!")

            except ImportError as e:
                print(f"\n✗ Failed to import __init__.py: {e}")
                import traceback
                traceback.print_exc()
    else:
        print(f"\n✗ ComicVerse node NOT found at: {our_node_path}")
        print(f"\n📁 Custom nodes directory contents:")
        for item in os.listdir(custom_nodes_path):
            item_path = os.path.join(custom_nodes_path, item)
            if os.path.isdir(item_path):
                print(f"  - {item}/ (directory)")
            else:
                print(f"  - {item}")

print("\n" + "=" * 70)
