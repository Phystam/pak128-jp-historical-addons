# Simutrans Special Colors & Material Systems

Technical reference for Simutrans reserved colors, night lighting, and shader configuration.

---

## 1. Simutrans Reserved Colors Table

The Simutrans graphics engine (and its compiler `makeobj`) matches color values **strictly and exactly** in a 15-bit RGB space. If a rendered pixel accidentally matches a reserved color, the engine will recolor or erase it at runtime!

### A. Transparency Key
- **RGB**: `(231, 255, 255)` / Hex: `#E7FFFF`
- **Behavior**: `makeobj` converts this exact color into alpha transparency.
- **Rule**: Never use this exact color on models or textures.

### B. Player Color Ramps (Company Liveries)
These colors are dynamically replaced by each player's chosen company colors in-game:
- **Primary Player Color (Blue Ramp - 8 shades)**:
  `RGB(36, 75, 103)`, `(57, 94, 124)`, `(76, 113, 145)`, `(96, 132, 167)`, `(116, 151, 189)`, `(136, 171, 211)`, `(156, 190, 233)`, `(176, 210, 255)`
- **Secondary Player Color (Gold Ramp - 8 shades)**:
  `RGB(123, 88, 3)`, `(142, 111, 4)`, `(161, 134, 5)`, `(180, 157, 7)`, `(198, 180, 8)`, `(217, 203, 10)`, `(236, 226, 11)`, `(255, 249, 13)`

### C. Night Lighting (Glowing Windows & Lamps)
At night, the engine performs an instant palette swap on designated colors:
- Pixels painted with designated daytime colors turn into incandescent yellow, halogen white, fluorescent green, or warm orange after sunset.
- Because `makeobj` compares values against its internal `image_t::rgbtab[]`, a 1-bit drift causes windows to stay black forever.

---

## 2. Why Normal Shaders Fail with Special Colors

If you assign a reserved color to a normal `Principled BSDF` material:
1. Sunlight angle, ambient lighting, shadows, and Blender's Tone Mapping (AgX / Filmic) will blend and shift the output RGB values by several counts.
2. A player-color blue `(36, 75, 103)` becomes `(38, 72, 100)`.
3. The compiled `.pak` treats it as a dead static color rather than a player livery.

### The Solution: Emission Bypass
Special color materials must be configured using pure unlit **Emission** shaders that completely bypass scene lighting and tone mapping:

```python
import bpy

def create_special_color_material(name, rgb_255):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Normalize 0-255 to 0.0-1.0
    r, g, b = [x / 255.0 for x in rgb_255]
    
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = (r, g, b, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat

# Example: Assign Player Color 1 (Primary Blue base)
pc1_base = create_special_color_material("PlayerColor1_Base", (36, 75, 103))
```

*Alternatively, use the addon's built-in helper: `addon.rig.make_special_color_material(bpy, rgb_tuple)`.*

---

## 3. General Material Guidelines (Non-Reserved Surfaces)

For regular walls, roofs, metal, and glass:
- **Base Shader**: Standard `Principled BSDF`.
- **Roughness**: Maintain between **`0.4` and `0.8`** (matte to subtle sheen). Avoid mirror-like specular reflections (`Roughness < 0.2`) as they produce harsh single-pixel specular glints in orthographic sprites.
- **Metallic**: Set to `0.0` for concrete, tile, wood, asphalt, and paint. Use `1.0` with `Roughness = 0.5` only for raw bare metal / chrome.
- **Contrast & Tone**: Slightly increase contrast and darken lower surfaces to compensate for the isometric sun angle (sun elevation $60^\circ$ from South).

---

## 4. Post-Render Color Verification

Always run color validation after rendering:
```python
import bpy
bpy.ops.simutrans.check_colors()
```
If the tool reports accidental hits in regular textures, adjust base color values by $1\%$ to $2\%$ to break the collision.
