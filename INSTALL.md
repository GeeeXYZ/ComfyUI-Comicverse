# ComicVerse Nodes - Installation Guide

## Installation Steps

### 1. Copy to ComfyUI Custom Nodes Directory

**For Standard ComfyUI Installation:**
```bash
# Copy the entire ComicVerse-Nodes folder to ComfyUI's custom_nodes directory
cp -r ComicVerse-Nodes /path/to/ComfyUI/custom_nodes/
```

**For Portable ComfyUI:**
```bash
# If using a portable version, copy to:
cp -r ComicVerse-Nodes ./ComfyUI-Windows-Portable/ComfyUI/custom_nodes/
```

### 2. Restart ComfyUI

After copying, restart your ComfyUI server. The nodes should appear in the node list under the "ComicVerse" category.

### 3. Install Font Files (Optional)

The decorative text and speech bubble features work best with custom fonts:

1. Navigate to `ComicVerse-Nodes/fonts/`
2. Replace the placeholder `.ttf` files with actual font files
3. Restart ComfyUI

**Recommended Free Fonts:**
- **Handwriting**: Kalam, Caveat, Patrick Hand
- **Bold**: Open Sans Bold, Roboto Bold
- **Cartoon**: Comic Neue, Bangers, Luckiest Guy

**Sources:**
- Google Fonts: https://fonts.google.com
- DaFont: https://www.dafont.com
- Font Squirrel: https://www.fontsquirrel.com

### 4. Verify Installation

1. Open ComfyUI
2. In the node search bar, type "Comic"
3. You should see all 5 ComicVerse nodes:
   - Comic Asset Library
   - Layout Template Selector
   - Basic Layout Composer
   - Speech Bubble Generator
   - Decorative Text Adder

## Troubleshooting

### Nodes Not Showing Up

**Check:**
1. The `ComicVerse-Nodes` folder is in the correct `custom_nodes` directory
2. All Python files are present and not corrupted
3. ComfyUI has been restarted
4. Check the ComfyUI console for any error messages

### Font-Related Errors

**If you see font loading errors:**
1. Ensure font files are actual `.ttf` or `.otf` format (not `.ttc`)
2. Check file permissions (font files should be readable)
3. The node will fall back to system defaults if custom fonts fail

### Import Errors

**Common Dependencies:**
- `torch`: ComfyUI already includes this
- `Pillow` (PIL): ComfyUI already includes this
- `numpy`: ComfyUI already includes this
- `json`: Built-in Python module
- `os`: Built-in Python module

If you encounter import errors, ensure ComfyUI is properly installed with all dependencies.

### Version Compatibility

- **ComfyUI**: Version compatible with latest stable release
- **Python**: 3.10 or higher
- **Pillow**: Latest version (included with ComfyUI)

## Directory Structure

```
ComicVerse-Nodes/
├── __init__.py                    # Node registration
├── README.md                      # Project overview
├── INSTALL.md                     # This file
├── nodes/
│   ├── __init__.py
│   ├── comic_asset_library.py     # Node 1: Material management
│   ├── layout_template_selector.py # Node 2: Template selection
│   ├── basic_layout_composer.py   # Node 3: Layout composition
│   ├── speech_bubble_generator.py # Node 4: Speech bubbles
│   └── decorative_text_adder.py   # Node 5: Decorative text
└── fonts/
    ├── handwriting.ttf            # Placeholder - replace with actual font
    ├── black_bold.ttf             # Placeholder - replace with actual font
    ├── cartoon.ttf                # Placeholder - replace with actual font
    └── README.txt                 # Font installation guide
```

## Next Steps

After installation, check out the example workflow in README.md to get started!
