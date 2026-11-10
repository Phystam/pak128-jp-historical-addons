# Blender MCP Tools Full Reference

This reference provides exhaustive documentation for all 9 Blender MCP tools, their parameters, usage constraints, and operational patterns.

---

## Universal Parameter: `user_prompt`

Most Blender MCP tools accept a `user_prompt` string argument:
- **Rule**: Pass the **user's exact words verbatim** (do NOT paraphrase, summarize, or substitute your own sub-goal or status message).
- **Multi-step tasks**: Keep passing the same initial prompt across all tool calls for that goal until the user provides a new or refined prompt.

---

## 1. `get_addon_status`

Inspects the connected Blender instance, version compatibility, enabled asset libraries, 3D generative AI providers, and telemetry status.

### When to Call
- **At the start of every new session or Blender-related task** to verify that Blender is running and the addon is connected.
- When you need to check which generative providers or asset libraries the user has configured/licensed.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

### Returned Information
- `blender_version`: Blender version string (e.g., `"4.2.0"`).
- `addon_version`: Version of the Blender MCP addon. If outdated, instructs how to update (`uvx mcp-for-blender install-addon`).
- `libraries`: Dictionary of available asset sources (`polyhaven`, `sketchfab`, `polypizza`) and whether each is enabled.
- `generators`: Dictionary of available 3D generative providers (`tripo`, `hunyuan3d`, `hyper3d`, `meshy`) and whether marked as "(Premium)" or enabled.
- `telemetry_consent`: Whether telemetry is enabled (`true`), disabled (`false`), or unreachable (`null`).

---

## 2. `get_scene_info`

Retrieves a compact, structured text summary of scene contents, hierarchy, transforms, and mesh topology without consuming tokens on images.

### When to Call
- Before modifying or adding objects, to check what already exists in the scene.
- To inspect object names, exact positions, scales, parent-child relations, and bounding boxes.
- To verify mesh topology health (triangles, quads, ngons, non-manifold edges) after procedural modeling.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `fields` | array/string | No | `["location", "size", "children", "hidden"]` | Fields to display per object. Available groups/fields below. |
| `query` | string | No | `""` | Filter objects whose names contain this substring. |
| `root` | string | No | `""` | Restrict output to the hierarchy rooted at this object name. |
| `limit` | integer | No | `20` | Maximum number of object lines to return. |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

### `fields` Categories
- **Placement**:
  - `location`: World coordinates $(X, Y, Z)$.
  - `size`: World bounding box dimensions $(X, Y, Z)$ in meters.
  - `ground`: Indicates if the object is `"on ground"`, `"floating by Xm"`, or `"below by Xm"`.
  - `rotation`: Rotation in degrees $(X, Y, Z)$.
  - `scale`: Scale factors $(X, Y, Z)$.
  - `parent`: Name of parent object.
- **Contents**:
  - `children`: Count of direct children.
  - `hidden`: Visibility flags.
  - `details`: Face counts for meshes, bone counts for armatures, or power/type for lights.
  - `materials`: Names of assigned materials.
  - `modifiers`: Active modifiers list.
  - `animation`: Action name or frame markers.
- **Health**:
  - `topology`: Quads, tris, ngons, non-manifold edges, boundary edges, loose vertices, poles.
  - `weights`: Vertices with no deform weights, or deform bones with empty vertex groups.
- **Settings**:
  - Adds a summary line with filename, render engine, frame range, resolution, camera, HDRI, and unit scale.

---

## 3. `execute_blender_code`

Executes arbitrary Python code inside the live Blender session with full access to `bpy`, `bmesh`, `mathutils`, and the Python standard library.

### When to Call
- For all procedural modeling, material setup, lighting, camera control, rigging, animation, and export tasks.
- When `get_scene_info` does not show a specific deep property you need to query.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `code` | string | **Yes** | - | Python code to execute in Blender. Whatever it prints (`print(...)`) is returned to the agent. |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

### Critical Guidelines
1. **Work in Small Steps**: Break down complex actions into distinct script executions.
2. **Print Output**: Standard output (`print`) is your eyes into script execution. Always print confirming values, created object names, or computed metrics.
3. **Nodes by Type, Never by Name**:
   - Node names (e.g. `"Principled BSDF"`) change across language localizations!
   - Always find nodes by `.type`:
     ```python
     principled = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
     ```
4. **Inspect Enums via `bl_rna`**:
   - Never guess or hardcode string enum values:
     ```python
     formats = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["file_format"].enum_items]
     ```
5. **Render Engine Assignment via Try/Except**:
   - `scene.render.engine` may error if invalid; catch `TypeError` to read valid engines:
     ```python
     try:
         bpy.context.scene.render.engine = 'CYCLES'
     except TypeError as e:
         print("Valid engines:", e)
     ```
6. **Material Color Goes to Node Inputs**:
   - `material.diffuse_color` only changes the viewport display color!
   - To affect actual rendering, connect/set values on shader input sockets:
     ```python
     principled.inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1.0)
     ```

---

## 4. `look`

Captures a visual snapshot of the scene, specific objects, or a rendered image and embeds it into the conversation.

### When to Call
- After creating, moving, shading, or lighting an object to verify the visual result.
- To inspect framing from multiple angles simultaneously (`mode="angles"`).
- To inspect animation sequences over time (`mode="frames"`).

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `mode` | string | No | `"viewport"` | Viewpoint mode: `"viewport"`, `"camera"`, `"angles"`, or `"frames"`. |
| `shading` | string | No | Viewport's | Shading mode: `"solid"`, `"material"`, `"rendered"` (EEVEE/Workbench only), `"wireframe"`, `"xray"`. |
| `target` | string/array | No | All visible | Object name(s) to focus and frame (includes children). |
| `views` | array | No | Front/Right/Top/3/4 | For `mode="angles"`: up to 6 of `["front", "back", "left", "right", "top", "three_quarter"]` or custom direction vectors `[x, y, z]`. |
| `distance` | float | No | Auto | Distance in meters from target center to camera eye. |
| `frames` | array | No | - | For `mode="frames"`: explicit list of frame integers. |
| `frame_count` | integer | No | Auto (2-12) | For `mode="frames"`: number of frames to sample across timeline. |
| `view` | string/array | No | Viewport | For `mode="frames"`: `"camera"`, angle name, or `[x, y, z]` vector. |
| `image` | string | No | - | Instead of viewport, show an image: `"Render Result"`, image datablock name, or file path. |
| `max_size` | integer | No | `768` | Longest image dimension in pixels. Use `512` for routine checks to save tokens. |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

---

## 5. `search_assets`

Searches online repositories for existing 3D models, PBR textures, and HDRI world environment backgrounds.

### Sources
- **`polyhaven`**: High-quality CC0 HDRIs, PBR materials, and realistic 3D models.
- **`sketchfab`**: Vast catalog of user-uploaded models (various licenses, check face counts).
- **`polypizza`**: Stylized low-poly models (CC0 or CC-BY with attribution).

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `source` | string | **Yes** | - | `"polyhaven"`, `"sketchfab"`, or `"polypizza"`. |
| `query` | string | No | `""` | Search query in plain English (synonyms understood). |
| `asset_type` | string | No | `"all"` | Poly Haven only: `"hdris"`, `"textures"`, `"models"`, or `"all"`. |
| `category` | string | No | - | Category filter (e.g. `"Furniture & Decor"` for polypizza, `"Wood"` for polyhaven). |
| `attributes` | object | No | - | Poly Haven filters (e.g. `{"weather": "clear"}`). |
| `min_size_m` | float | No | - | Poly Haven only: minimum physical size in meters (use $2.0+$ for floors/walls to prevent tiling). |
| `licence` | string | No | - | Poly Pizza only: `"CC0"` or `"CC-BY"`. |
| `animated` | boolean | No | - | Poly Pizza only: filter for models containing animation. |
| `limit` | integer | No | - | Number of items to return. |
| `previews` | integer | No | `0` | Number of image thumbnails to attach (max 6, Poly Haven & Sketchfab). |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

---

## 6. `import_asset`

Downloads and instantiates an asset discovered via `search_assets` into the current scene.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `source` | string | **Yes** | - | `"polyhaven"`, `"sketchfab"`, or `"polypizza"`. |
| `id` | string | **Yes** | - | Asset identifier or Sketchfab UID from `search_assets`. |
| `asset_type` | string | Required for Poly Haven | - | `"hdris"` (becomes World light), `"textures"` (PBR node tree), or `"models"`. |
| `target_size` | float | Sketchfab req, Polypizza rec | - | Largest dimension in meters (e.g. chair `1.0`, car `4.5`, cup `0.12`). Library models arrive at arbitrary scales! |
| `apply_to` | string/array | No | - | Poly Haven textures: object name(s) to apply the generated material to. If omitted, material is unassigned and lost on save. |
| `resolution` | string | No | `"1k"` | Poly Haven: `"1k"`, `"2k"`, `"4k"`, `"8k"`. Use `1k`-`2k` for background/props, `4k` for hero assets. |
| `file_format` | string | No | - | Poly Haven: `"hdr"`/`"exr"` for HDRIs, `"jpg"`/`"png"`/`"exr"` for textures. |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

### Post-Import Routine
1. Inspect the reported `world_bounding_box` and `ground` offset.
2. Adjust location so the object sits flat on the ground plane ($Z = 0$).
3. Call `look` to confirm visual appearance and placement.

---

## 7. `generate_3d`

Generates a new textured 3D mesh using AI generative models from a text prompt or input image.

### Crucial Constraints
- **One Object Only**: Generates a single standalone prop/character. Never request a full scene, ground terrain, or multi-part assembly.
- **Cost Awareness**: Calls may consume credits or monthly quota. Duplicate an existing generated model (`bpy.ops.object.duplicate`) instead of regenerating.
- **Scale & Pivot**: Meshes arrive at arbitrary scale and orientation (Meshy typically scales to real-world with bottom pivot). Always inspect bounding box and ground placement.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | string | Conditional | - | Concise English description of the object (e.g. `"weathered wooden treasure chest with brass bands"`). |
| `image` | string | Conditional | - | Absolute local file path or public HTTP/HTTPS URL. (Chat images cannot be passed directly; request a path/URL). |
| `name` | string | No | From prompt | Name of the object datablock in Blender. |
| `provider` | string | No | `"auto"` | `"auto"`, `"tripo"`, `"hunyuan3d"`, `"hyper3d"`, or `"meshy"`. Auto prioritizes Premium generators, then user API keys. |
| `quality` | string | No | User default | `"standard"` or `"high"` (Premium). Only request `"high"` when high geometric detail is essential. |
| `bbox_condition` | array | No | - | Hyper3D only: proportional constraints `[length, width, height]`. |
| `wait_seconds` | integer | No | `45` | Time in seconds to wait synchronously (max 45). |
| `job` | string | No | - | Job handle from a previous timed-out call to resume waiting. |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

### Handling Long Generations (Job Polling)
Generation typically takes 1 to 3 minutes:
1. First call: `generate_3d(prompt="...", wait_seconds=45)`
2. If generation is not ready within 45s, the tool returns a `job` ID.
3. Call again with: `generate_3d(job=job_id, name=..., wait_seconds=45)` until finished. Do NOT start a new generation.

---

## 8. `record_trajectory_feedback`

Logs user evaluation feedback against recorded actions for reinforcement and continuous improvement.

### When to Call
Whenever the user explicitly reacts to an action:
- User says "looks good", "perfect", "keep it" $\rightarrow$ `feedback="accept"`
- User says "no, that's wrong", "undo that" $\rightarrow$ `feedback="reject"` or `feedback="undo"`
- User says "make it bigger", "too shiny", "move it left" $\rightarrow$ `feedback="correction"`, pass their exact phrase in `correction_text`.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `feedback` | string | **Yes** | - | `"accept"`, `"reject"`, `"undo"`, or `"correction"`. |
| `correction_text` | string | No | `""` | User's correction comments (crucial when `feedback="correction"`). |
| `step_index` | integer | No | Last step | 0-based step index to attach feedback to. |
| `user_prompt` | string | No | `""` | Context prompt for the feedback row. |

---

## 9. `disable_telemetry`

Immediately disables collection of prompts, executed code, screenshots, and scene metadata.

### When to Call
Immediately when the user requests privacy, asks to stop logging/telemetry, or asks not to share data.

### Parameters
| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `user_prompt` | string | No | `""` | User's verbatim prompt |

*Note: Telemetry can only be re-enabled manually by the user inside Blender under Preferences > Add-ons > Blender MCP.*
