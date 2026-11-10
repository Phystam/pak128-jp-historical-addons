# Simutrans Menu Button Icon Specifications (32x32)

Guidelines and automation specifications for generating 32x32 menu button icons (`icon` property in `.dat`) for roads, rails, infrastructure, and transport objects.

---

## 1. Overview & Applicability

In Simutrans, infrastructure and tool objects placed via the construction menus require an in-game toolbar icon.
Applicable objects include:
- **`way`** (roads, tracks, runways, waterways)
- **`way_obj` / catenary** (overhead lines, third rails)
- **`tunnel`** (tunnel portals)
- **`bridge`** (bridges)
- **`building` (stops, extensions, depots)**: stations, bus stops, docks, airport stops, extensions, train/car/ship/aircraft depots
- **`roadsign` / signals**: block signals, presignals, road signs

---

## 2. Icon Canvas & Layer Specifications (32x32)

Every menu icon must be exactly **32 × 32 pixels** and adhere to the following layer hierarchy:

| Element | Specifications | Details |
| :--- | :--- | :--- |
| **Canvas Size** | 32 × 32 px | RGBA image. |
| **Background** | Single solid color: `#fafafa` | Fills the entire 32×32 canvas background. |
| **Subject Artwork** | Rendered model preview (North-South / Isometric view) | Scaled down to fit within the upper/central area. **Must maintain a 1px to 2px clearance** inside the 1px border. |
| **Category Color Bar** | Bottom **7px** height ($Y=25\text{--}31$ or $Y=0\text{--}6$) | Solid fill across the bottom 7px representing the transport type. |
| **Border (Outline)** | **1px border** with `#8a8a8a` in **Multiply blend mode** | Surrounds the outer 1px perimeter ($X=0, 31$, $Y=0, 31$). In multiply mode, it subtly tints the background and darkens the color bar edges. |

```
 0 ------------------------------ 31
0 +------------------------------+   ^
  | [1px Border #8a8a8a Multiply]|   |
  |  +------------------------+  |   |
  |  | 1-2px Margin           |  |   |
  |  |                        |  |   | 25px: Background (#fafafa)
  |  |   [Subject Artwork]    |  |   |       + Subject Artwork
  |  |   (North-South view)   |  |   |
  |  |                        |  |   |
  |  +------------------------+  |   |
24+------------------------------+   v
25| [Way Category Color Bar]     |   ^  7px: Category Bar (Solid Color)
31+------------------------------+   v  + 1px Multiply Border overlay
```

---

## 3. Way Category Color Bar Palette

The bottom 7px bar uses standardized categorical hex colors corresponding to the way/system type:

| Category | Way Type Identifier | Color Name / Meaning | Hex Code | RGB |
| :--- | :--- | :--- | :--- | :--- |
| **線路 (track)** | `track` | 弁柄色 (Railway Red) | `#cb4042` | `(203, 64, 66)` |
| **道路 (road)** | `road` | 古代紫 (Road Purple) | `#77429d` | `(119, 66, 157)` |
| **リニア (maglev)** | `maglev_track` | 柿色 (Maglev Orange) | `#f05e1c` | `(240, 94, 28)` |
| **トラム (tram_track)** | `tram_track` | 甚三紅 (Tram Coral Pink) | `#f19483` | `(241, 148, 131)` |
| **ナローゲージ (narrowgauge)** | `narrowgauge_track` | 躑躅色 (Narrowgauge Rose) | `#e16b8c` | `(225, 107, 140)` |
| **船舶 (water)** | `water` | 濃藍 (Water Navy) | `#113285` | `(17, 50, 133)` |
| **飛行機 (air)** | `air` | 千草色 (Aviation Sky Blue) | `#58b2dc` | `(88, 178, 220)` |
| **土地関連 (land)** | Landscape, Slope, Climate | 常磐色 (Terra Green) | `#1b813e` | `(27, 129, 62)` |
| **一般 (general)** | General tools, edit, utilities | 錫色 (General Slate Grey) | `#656765` | `(101, 103, 101)` |

---

## 4. Subject Artwork Placement & Sizing

1. **Orientation**:
   - Use the **North-South (N-S)** facing view of the way, tunnel portal, signal, or stop.
2. **Padding & Margin**:
   - The artwork must not touch the 1px border.
   - Leave **1px to 2px of breathing space** between the outer border and the object silhouette.
   - Vertically, the artwork sits inside the upper 25px region (above the 7px color bar).
3. **Contrast & Simplification**:
   - Because the subject area is roughly $28 \times 22\text{px}$, ensure high contrast. Thin lines should be sharpened or rendered with anti-aliasing against `#fafafa`.

---

## 5. Python Automation Script (Pillow / PIL)

You can generate or compose this icon programmatically in Python using PIL/Pillow:

```python
from PIL import Image, ImageDraw

COLOR_BAR_MAP = {
    "general": "#656765",
    "land": "#1b813e",
    "track": "#cb4042",
    "maglev": "#f05e1c",
    "tram": "#f19483",
    "narrowgauge": "#e16b8c",
    "road": "#77429d",
    "water": "#113285",
    "air": "#58b2dc",
}

def create_menu_icon(subject_image_path, category="track", output_path="icon.png"):
    # 1. Base 32x32 canvas with #fafafa
    icon = Image.new("RGBA", (32, 32), "#fafafa")
    draw = ImageDraw.Draw(icon)
    
    # 2. Draw 7px color bar at the bottom (y=25 to 31)
    bar_color = COLOR_BAR_MAP.get(category.lower(), "#656765")
    draw.rectangle([0, 25, 31, 31], fill=bar_color)
    
    # 3. Paste subject artwork (scaled with 1-2px margin inside upper 25px area)
    if subject_image_path:
        subject = Image.open(subject_image_path).convert("RGBA")
        # Max bounding box for subject: width 28 (x=2..29), height 21 (y=2..22)
        subject.thumbnail((28, 21), Image.Resampling.LANCZOS)
        # Center horizontally and vertically within upper region
        paste_x = 2 + (28 - subject.width) // 2
        paste_y = 2 + (21 - subject.height) // 2
        icon.alpha_composite(subject, (paste_x, paste_y))
        
    # 4. Apply 1px border in Multiply mode with #8a8a8a
    border_layer = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
    border_draw = ImageDraw.Draw(border_layer)
    # Draw 1px hollow frame with #8a8a8a
    border_draw.rectangle([0, 0, 31, 31], outline="#8a8a8a", width=1)
    
    # Multiply blend mode: (A * B) / 255
    from PIL import ImageChops
    final_icon = ImageChops.multiply(icon.convert("RGB"), border_layer.convert("RGB"))
    
    final_icon.save(output_path)
    return output_path
```

---

## 6. Integration with `.dat` File

In the object's `.dat` file, specify the icon image reference using `icon`:
```ini
obj=way
name=MyTrack
...
icon=my_track_icon.0.0
```
When compiled with `makeobj`, `makeobj` extracts the 32×32 graphic and registers it into the corresponding tool bar menu.
