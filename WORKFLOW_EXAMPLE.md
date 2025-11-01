# ComicVerse Nodes - Workflow Example

## Complete Workflow

Here's a step-by-step guide to using all ComicVerse nodes in a complete comic layout workflow:

```
1. Load Images → 2. Select Template → 3. Auto Layout → 4. Add Bubbles → 5. Add Text → 6. Final Output
   (Node 1)           (Node 2)            (Node 3)         (Node 4)        (Node 5)
```

## Detailed Steps

### Step 1: Load Images (Comic Asset Library Node)

**Purpose**: Import and manage comic panel images

**Inputs**:
- Connect image outputs from any ComfyUI image generation node (e.g., Stable Diffusion, Load Image)
- You can connect up to 20 images

**Outputs**:
- `selected_images`: Batch of images ready for layout
- `selected_count`: Number of images loaded

**UI Behavior**:
- Images appear as a grid of thumbnails
- Each image has a checkbox for selection
- Select the images you want to include in your comic

**Best Practices**:
- Use images of similar aspect ratios for best results
- You can connect images from different sources (AI generation, uploads, etc.)
- The node will automatically deduplicate identical images

### Step 2: Select Template (Layout Template Selector Node)

**Purpose**: Choose a layout template and configure basic parameters

**Inputs**:
- `template_type`: Choose from:
  - **2横版** (2 Horizontal): Two panels side by side
  - **2竖版** (2 Vertical): Two panels stacked vertically
  - **4格经典** (4-Grid Classic): 2x2 grid layout
  - **3格斜切** (3-Grid Diagonal): Three panels with diagonal split
  - **自由网格** (Free Grid): Three columns of equal width
- `grid_margin`: Grid spacing in pixels (1-20, default: 5)
- `background_color`: Background color in hex format (#RRGGBB, default: #FFFFFF for white)

**Outputs**:
- `template_config`: JSON string containing layout configuration

**Best Practices**:
- Match template count to your image count
- Use larger margins (10-15px) for clean, professional look
- White background (#FFFFFF) works best for most comics

### Step 3: Compose Layout (Basic Layout Composer Node)

**Purpose**: Generate the initial comic layout

**Inputs**:
- `images`: Connect from Node 1 output
- `template_config`: Connect from Node 2 output
- `layout_mode`: Choose:
  - **自动排版** (Auto Layout): Automatically positions images
  - **手动拖拽** (Manual Drag): For future drag-and-drop editing

**Outputs**:
- `layout_image`: Composed layout image
- `element_coords`: JSON with position coordinates of each panel

**Processing Logic**:
- Creates a 1080x1920px canvas
- Resizes and positions each image to fit its grid
- Maintains aspect ratios
- Applies margins and background color

**Best Practices**:
- Start with "自动排版" mode
- Ensure image count matches template grid count
- View the output to verify positioning before adding bubbles/text

### Step 4: Add Speech Bubbles (Speech Bubble Generator Node)

**Purpose**: Add dialogue bubbles to your comic panels

**Inputs**:
- `base_image`: Connect from Node 3 output
- `target_image_index`: Which panel the bubble belongs to (0-indexed)
- `bubble_text`: The dialogue text (supports `\n` for line breaks)
- `bubble_style`: Choose from:
  - **圆形** (Oval): Classic speech bubble shape
  - **尖角** (Pointed): Speech bubble with tail pointing to character
  - **云状** (Cloud): Fluffy, thought-bubble style
- `bubble_position_x`: X coordinate of bubble top-left corner
- `bubble_position_y`: Y coordinate of bubble top-left corner
- `bubble_color`: Bubble fill color (hex format)
- `text_color`: Text color (hex format)

**Outputs**:
- `image_with_bubbles`: Image with the new bubble added
- `bubble_coords`: Position coordinates of the bubble

**Text Size Calculation**:
- Width = (max characters per line × 12) + 40 pixels
- Height = (number of lines × 25) + 40 pixels
- Minimum size: 200×100 pixels

**Best Practices**:
- Use index 0 for the first panel, 1 for the second, etc.
- Add one bubble at a time for clarity (chain multiple nodes)
- Position bubbles away from panel edges
- Use contrasting colors for readability

**Multiple Bubbles**:
To add multiple bubbles, duplicate this node and chain them:
```
Layout → Bubble1 → Bubble2 → Bubble3
```

### Step 5: Add Decorative Text (Decorative Text Adder Node)

**Purpose**: Add onomatopoeia, sound effects, and decorative text

**Inputs**:
- `input_image`: Connect from Node 3 or Node 4 output
- `text_content`: The text to add (e.g., "BOOM!", "WHOOSH", "突然")
- `font_style`: Choose from:
  - **手写体** (Handwriting): Casual, handwritten style
  - **黑体** (Bold): Bold sans-serif
  - **卡通体** (Cartoon): Comic book style
- `text_size`: Font size in pixels (10-100, default: 30)
- `text_color`: Text color (hex format)
- `text_position_x`: X coordinate of text top-left corner
- `text_position_y`: Y coordinate of text top-left corner

**Outputs**:
- `final_image`: Final image with decorative text

**Text Effects**:
- **Outline**: Automatic black outline for readability
- **Positioning**: Pixel-perfect positioning
- **Multi-line**: Supports line breaks in text

**Best Practices**:
- Use larger sizes (40-60px) for impact
- Place text where it doesn't obscure important content
- Use high-contrast colors
- Keep text content concise and impactful

**Font Files**:
For best results, add custom fonts to the `fonts/` directory:
- `handwriting.ttf`: For casual, handwritten effects
- `black_bold.ttf`: For bold emphasis
- `cartoon.ttf`: For comic-style text

## Complete Workflow Diagram

```
[Load Image Node] ──┐
[Load Image Node] ──┤
[Load Image Node] ──┼───► [Comic Asset Library] ──► [Layout Template Selector]
[Load Image Node] ──┤                           │
[Load Image Node] ──┘                           ▼
                                      [Basic Layout Composer] ──► [Speech Bubble Generator] ──► [Decorative Text Adder] ──► Final Output
```

## Tips & Tricks

### 1. Image Preparation
- **Aspect Ratio**: Use images with similar aspect ratios for consistent layouts
- **Resolution**: 512×512 or higher for best quality
- **Format**: PNG or JPG both work

### 2. Template Selection
- **2x2 Grid**: Perfect for 4-panel comics
- **3-Panel**: Great for comedic timing
- **Diagonal**: Dynamic, action-oriented layouts

### 3. Bubble Placement
- Don't cover character faces
- Point tails toward speaking characters
- Leave breathing room around text
- Use different sizes for emphasis

### 4. Text Styling
- **Sound Effects**: "BOOM!", "CRASH!", "SNIFF"
- **Emotion**: "Ugh...", "Phew!", "Whoa!"
- **Emphasis**: "突然!" (Suddenly!), "えええ!" (Eeeh!)

### 5. Color Guidelines
- **Bubbles**: White or light colors for readability
- **Text**: Dark colors for contrast
- **Accent**: Red or bright colors for impact

## Advanced Usage

### Chaining Multiple Bubbles
```
Layout → Bubble1 (Panel 1) ──┐
           └─► Bubble2 (Panel 1) ──► Final
```

### Multi-Step Text Addition
```
Layout + Bubble → Text1 (Sound Effect) ──► Text2 (Narration) ──► Final
```

### Template Experimentation
Try different templates with the same images to see which works best for your story pacing!

## Troubleshooting

**Problem**: Images not appearing in layout
**Solution**: Check that image count matches template grid count

**Problem**: Bubbles too small/large
**Solution**: Adjust bubble text length or modify bubble_position coordinates

**Problem**: Text not showing
**Solution**: Ensure font files are properly installed or check text color/position

**Problem**: Layout too tight
**Solution**: Increase grid_margin in template selector

For more help, check INSTALL.md for common issues.
