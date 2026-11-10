# Simutrans 3D Modeling Guidelines & Standards

Standardized geometric, dimensional, and aesthetic rules for creating Simutrans assets in Blender.

---

## 1. Coordinate System & Scale Rules

- **Tile Unit**: $1 \text{ tile} = 20\text{m} \times 20\text{m}$ in real-world dimensions.
- **World Origin**: Center of the ground surface at $(0, 0, 0)$.
- **Ground Level**:
  - The base/contact surface of buildings, roads, and track must sit precisely at $Z = 0.0$.
  - Vehicles sit with wheel/rail contact at $Z = 0.0$.
- **Footprint Sizing (Buildings)**:
  - **Standard $1 \times 1$ Tile**: Keep total building dimensions between **$16\text{m} \times 16\text{m}$ and $18\text{m} \times 18\text{m}$**. This reserves $1\text{m}$ to $2\text{m}$ of margin around the perimeter for sidewalks, gardens, or road clearances.
  - **Townhouses / Row Buildings (Machiya, Terraces)**: May extend to the full $20\text{m}$ boundary along the shared wall axes to connect seamlessly with neighboring structures.
- **Watercraft & Ships (Draft / Waterline)**:
  - Ships sit in water up to the waterline ($Z = 0.0$).
  - **Omit geometry below the waterline entirely**: The hull beneath the water surface is never visible in-game. Do not model or render submerged hulls.
- **Transform Application (Mandatory)**:
  - Before rendering or checking bounds, **always apply all transforms**:
    ```python
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ```
  - An unapplied scale or rotation distorts the orthographic camera framing and bounding box calculation.

---

## 2. Low-Resolution Isometric Exaggeration (Critical Rule)

### The Mathematics of Simutrans Pixel Scale
Simutrans uses a 2:1 dimetric/isometric projection where a square tile is drawn as a diamond:
- In `pak128`, a $20\text{m} \times 20\text{m}$ tile diamond spans **128px wide** and **64px high**.
- One $20\text{m}$ edge of the tile projects onto the screen as a diagonal spanning **64px horizontally** and **32px vertically**.
- **Effective Horizontal Resolution**:
  $$\frac{20\text{m}}{64\text{px}} = 0.3125\text{m/px} = 31.25\text{cm/px}$$
- **Effective Vertical Resolution**:
  $$\frac{20\text{m}}{32\text{px}} = 0.625\text{m/px} = 62.5\text{cm/px}$$

> [!WARNING]
> Because **1 horizontal pixel represents $\approx 31.25\text{cm}$** (in `pak128`; $\approx 62.5\text{cm}$ in `pak64`), any realistic detail smaller than $30\text{cm}$ is sub-pixel ($< 1\text{px}$) and will be completely smeared or erased by anti-aliasing.
> To produce readable edges, shadows, and contours, you must **deliberately exaggerate silhouettes and relief to at least $1\text{--}2\text{ pixels}$ ($30\text{--}60\text{cm}$)**.

| Architectural Feature | Real-world Dimension | Simutrans Exaggerated Modeling Rule |
| :--- | :--- | :--- |
| **Window Panes & Reveals** | 3 - 5 cm deep | **Recess window panes by at least 30 - 45 cm** ($\approx 1\text{--}1.5\text{px}$) into the wall to cast a distinct 1-pixel shadow. |
| **Window Frames & Mullions** | 5 - 10 cm wide | **Make visible frames/mullions at least 30 - 40 cm wide** ($\approx 1\text{px}$); otherwise, omit fine multi-pane grids and simplify to a single large glass plane. |
| **Roof Eaves & Fascia** | 10 - 15 cm | **Give eaves, verges, and gutters a 35 - 50 cm overhang and thickness** ($\approx 1\text{--}1.5\text{px}$) to avoid jagged single-pixel roof edges. |
| **Parapets & Balconies** | 10 - 15 cm | **Give parapet walls and railings at least 35 - 50 cm thickness** for clear boundary definition. |
| **HVAC & Rooftop Units** | 60 - 90 cm | **Scale outdoor air conditioning units, chillers, and water tanks 1.5x - 2.0x larger** (approx. $1.2\text{--}1.5\text{m}$ across) so their blocky silhouette registers as 4–5 pixels across. |
| **Stairs & Steps** | 15 cm riser | **Consolidate small steps** into larger 30 - 40 cm step blocks. |

---

## 3. Mesh Cleanup & Hidden Surface Removal

- **Delete Ground Bottom Faces**:
  - Delete any bottom-facing polygon lying at $Z = 0$ or inside foundations. It is never visible and wastes memory.
- **Remove Internal/Buried Geometry**:
  - If two volumes intersect (e.g. chimney through a roof, interior room walls), eliminate hidden internal faces.
- **Manifold Surfaces**:
  - Keep meshes clean: avoid stray vertices, non-manifold edges, or inverted face normals. Run `bpy.ops.mesh.normals_make_consistent(inside=False)` if lighting looks uneven.

---

## 4. Reusable Components Structure

Small recurring props should not be built from scratch every time:
- Save universal props (air conditioners, electrical cubicles, bicycles, vending machines, fences, wells, trees) in individual `.blend` files inside `components/<component_name>/`.
- Include a `component.json` metadata file if needed.
- Use `bpy.ops.simutrans.insert_component(...)` to link or append them into the project.

---

## 5. Menu Button Icon Specifications (32×32px)

When creating ways, infrastructure, or depot/stop objects (`way`, `way_obj`, `tunnel`, `bridge`, `stop`, `extension`, `depot`, `roadsign`/`signal`), a **32×32 pixel menu button icon** must be generated and added to the `.dat` via `icon=...`.

### Layer & Formatting Rules
- **Canvas Size**: 32 × 32 px.
- **Background**: Solid fill `#fafafa`.
- **Bottom Color Bar (7px)**: Fill the bottom 7px with the category indicator:
  - 一般 (general): `#656765`
  - 土地関連 (land): `#1b813e`
  - 線路 (track): `#cb4042`
  - リニア (maglev): `#f05e1c`
  - トラム (tram_track): `#f19483`
  - ナローゲージ (narrowgauge): `#e16b8c`
  - 道路 (road): `#77429d`
  - 船舶 (water): `#113285`
  - 飛行機 (air): `#58b2dc`
- **Border**: 1px outer frame blended in **Multiply mode** using `#8a8a8a`.
- **Artwork Placement**: Use the **North-South view** of the object, scaled to fit inside the upper region with a **1px to 2px clearance** inside the border.
- *Detailed specification and Python generator script: see [menu_icon_rules.md](./menu_icon_rules.md).*
