# Simutrans Blender Kit API Reference

Exhaustive reference for driving the `simutrans_blender_kit` Blender addon programmatically via `execute_blender_code`.

---

## 1. Scene Properties (`bpy.context.scene.simutrans`)

All configurations are stored in the custom PropertyGroup at `bpy.context.scene.simutrans`.

### Core / Universal Settings
| Property | Type | Options / Default | Description |
| :--- | :--- | :--- | :--- |
| `pakset` | Enum | `"pak64"`, `"pak128"` (default), `"pak192"`, `"pak256"` | Target pakset scale and tile pixel resolution. |
| `obj_type` | Enum | `"vehicle"` (default), `"building"`, `"way"`, `"wayobj"`, `"roadsign"`, `"tunnel"`, `"bridge"`, `"factory"` | Kind of object being authored. Dictates render headings, layer split, and .dat emission. |
| `obj_name` | String | `"My_Object"` | Name written into the .dat definition (`name=...`). |
| `basename` | String | `"vehicle"` | Base filename for the exported image sheet and .dat file. |
| `out_dir` | String | `"//simutrans"` | Output directory path. **Always set an absolute path** when running via scripts to prevent resolution failures. |
| `author` | String | `""` | Author credit written into .dat (`copyright=...`). |
| `dirs` | Enum | `"8"` (default, asymmetric), `"4"` (symmetric) | Number of directional headings to render. |
| `intro_year` | Int | `1900` | Introduction year for the object in-game. |

---

### Building Properties (`obj_type == "building"`)
| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `size_x` | Int | `1` (1..8) | Number of tiles along East axis. |
| `size_y` | Int | `1` (1..8) | Number of tiles along South axis. |
| `layouts` | Int | `0` (0..4) | Number of rotation layouts. `0` lets engine decide (1 for square footprint, 2 otherwise; use 4 for all 4 rotations). |
| `btype` | Enum | `"res"` | Building category: `"res"`, `"com"`, `"ind"`, `"cur"`, `"tow"`, `"stop"`, `"depot"`, `"extension"`. |
| `level` | Int | `1` | Demand level; sets default capacity (`level * 32`). |
| `chance` | Int | `100` (0..100) | Probability weight for city generator (0 = never spawn automatically). |
| `seasons` | Int | `1` (1, 2, 4, 5) | Number of seasonal variants (never 3). Uses collections `season_1`, `season_2`, etc. |
| `phases` | Int | `1` (1..16) | Number of animation frames. Uses collections `phase_1`, `phase_2`, etc. |
| `enables_pax` | Bool | `False` | For stops: accepts passengers. |
| `enables_post` | Bool | `False` | For stops: accepts mail. |
| `enables_ware` | Bool | `False` | For stops: accepts freight goods. |

---

### Vehicle Properties (`obj_type == "vehicle"`)
| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `waytype` | Enum | `"track"` | Vehicle waytype: `"track"`, `"road"`, `"water"`, `"air"`, `"monorail_track"`, `"maglev_track"`, `"narrowgauge_track"`, `"tram_track"`. |
| `engine_type` | Enum | `"diesel"` | Engine type: `"steam"`, `"diesel"`, `"electric"`, `"bio"`, `"sail"`, `"hydrogene"`, `"fuel_cell"`, `"battery"`. |
| `speed` | Int | `100` (km/h) | Maximum operating speed. |
| `power` | Int | `0` (kW) | Power output (`0` turns it into an unpowered wagon/trailer). |
| `weight` | Int | `20` (tons) | Vehicle unladen weight. |
| `length` | Int | `8` (1..16) | Length in 1/16th tile units (8 = half a tile, 16 = full tile). |
| `payload` | Int | `0` | Freight / passenger carrying capacity. |
| `freight` | String | `"None"` | Good carried (e.g. `"Passagiere"`, `"Post"`, `"Kohle"`). |
| `freight_goods`| String | `""` | Comma-separated goods for wagons with visual load states (`freight_0`, `freight_1`). |
| `cost` | Int | `1000000` | Purchase cost in cents. |
| `runningcost` | Int | `100` | Maintenance cost per km. |
| `constraint_prev`| String | `""` | Valid leading vehicles (`constraint[prev][0]=...`). |
| `constraint_next`| String | `""` | Valid trailing vehicles (`constraint[next][0]=...`). |

---

### Factory Properties (`obj_type == "factory"`)
| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `factory_mapcolor` | Int | `1` (0..254) | Minimap dot color index (required by engine). |
| `factory_productivity`| Int | `10` | Production rate per step. |
| `factory_location` | Enum | `"Land"` | Placement site: `"Land"`, `"water"`, `"city"`, `"river"`, `"shore"`, `"forest"`. |
| `factory_output_good` | String | `""` | Output product name (must match pakset good). Empty = pure consumer. |
| `factory_output_capacity`| Int | `40` | Output warehouse storage (> 10). |
| `factory_input_good` | String | `""` | Input resource required. Empty = raw extractor. |

---

### Ways, Catenary, Signs, Tunnels & Bridges
| Property | Type | Default | Used By | Description |
| :--- | :--- | :--- | :--- | :--- |
| `topspeed` | Int | `50` | Way, Wayobj | Speed limit of the track/road/catenary. |
| `maintenance` | Int | `100` | Way, Wayobj, Bridge, Tunnel | Monthly maintenance cost. |
| `own_waytype` | Enum | `"electrified_track"`| Wayobj | What the catenary grants (e.g. electrification). |
| `is_signal` | Bool | `False` | Roadsign | True for block signal, False for simple roadsign. |
| `states` | Int | `1` (1..8) | Roadsign | Number of aspects (State 0 is Red). Collections `state_0`, `state_1`. |
| `max_length` | Int | `0` | Bridge | Maximum span in tiles (0 = unlimited). |
| `max_height` | Int | `4` | Bridge | Maximum clearance height above ground. |
| `pillar_distance` | Int | `0` | Bridge | Interval for support pillars in tiles. |
| `tunnel_way` | String | `""` | Tunnel | Internal way cross-reference name. |

---

## 2. Operators (`bpy.ops.simutrans.*`)

### Rigging & Setup
- `bpy.ops.simutrans.build_rig()`:
  Creates/updates the Simutrans isometric orthographic camera (`SIMUTRANS_CAM`) and screen-locked sunlight (`SIMUTRANS_SUN`). Configures render resolution according to selected `pakset`.
- `bpy.ops.simutrans.create_template()`:
  Generates the standardized collection structure required for the selected `obj_type` and creates visual bounding empty guides in `SIMUTRANS_GUIDES`. Idempotent: does not touch or delete artist meshes.

### Scene Validation & Color Check
- `bpy.ops.simutrans.validate()`:
  Performs pre-flight checks: confirms model bounds fit tile dimensions, origin is at ground level, no empty required collections exist.
- `bpy.ops.simutrans.check_colors()`:
  Scans rendered sprite sheets for accidental occurrences of Simutrans reserved colors (Player colors 1 & 2, transparency key `#E7FFFF`, and night light colors).

### Rendering & Output Generation
- `bpy.ops.simutrans.preview()`:
  Renders a single heading through the official render pipeline for quick framing checks.
- `bpy.ops.simutrans.preview_sheet()`:
  Renders all 8 headings and assembles them into a single labeled contact sheet.
- `bpy.ops.simutrans.render_sheet()`:
  Executes the full render pipeline across all required headings and layers, cuts and aligns tiles, packs the final sprite sheet PNG, and emits the companion `.dat` file.
- `bpy.ops.simutrans.write_dat()`:
  Regenerates and rewrites the `.dat` file from current scene properties without re-rendering images.
- `bpy.ops.simutrans.night_preview()`:
  Generates a night-mode simulation preview showing which pixels light up after dark.
- `bpy.ops.simutrans.compile_pak()`:
  Invokes `makeobj` to compile the generated `.dat` and sprite sheet into a playable `.pak` file.

### Variants & Consists
- `bpy.ops.simutrans.variant_add()`: Creates a new color/material/visibility variant.
- `bpy.ops.simutrans.variant_apply(name="...")`: Applies the variant's overrides to the viewport.
- `bpy.ops.simutrans.variant_clear()`: Restores the base scene materials and visibility.
- `bpy.ops.simutrans.render_variants()`: Batch-renders all configured variants into separate sheets and .dat blocks.
- `bpy.ops.simutrans.consist_check()`: Validates train composition rules and checks for broken vehicle couplings.
- `bpy.ops.simutrans.consist_apply()`: Writes calculated coupling constraints to the active vehicle.

### Components
- `bpy.ops.simutrans.refresh_components()`: Rescans the `components/` workspace directory for reusable `.blend` assets.
- `bpy.ops.simutrans.insert_component(name="...")`: Links/appends a component (e.g. well, HVAC, AC unit, tree) into the active scene.
