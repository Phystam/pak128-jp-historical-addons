# Blender MCP Troubleshooting & Pitfall Guide

This guide details common failure modes when operating Blender via MCP and how AI agents should reliably handle or avoid them.

---

## 1. Addon Connection & Version Errors

### Symptoms
- Tool execution fails with connection errors or reports that the addon is outdated.
- `telemetry_consent` returns `null`.

### Resolution
1. Verify with `get_addon_status`.
2. If the tool reports that the addon is outdated or missing, guide the user to run:
   ```bash
   uvx mcp-for-blender install-addon
   ```
3. Remind the user to enable or restart the addon in Blender:
   `Edit > Preferences > Add-ons > Search "Blender MCP" > Enable checkbox`.

---

## 2. Localization Pitfalls (Non-English Blender UIs)

### Problem
If the user's Blender UI is set to Japanese, French, German, etc., node names in the shader editor or modifier names may be translated (e.g., `"プリンシプルBSDF"` or `"Principled BSDF"`). Hardcoded name lookups like:
```python
mat.node_tree.nodes["Principled BSDF"]  # FAILS on non-English UI!
```
will raise `KeyError`.

### Solution
Always look up nodes and items by their internal **`.type`** or iterate over nodes:
```python
bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
```
The `.type` attribute is an internal C enum that NEVER changes across languages.

---

## 3. String Enum Guessing Failures

### Problem
Assigning string enums (e.g., render engines, file formats, blend modes) based on memory or guessing can cause `TypeError`:
```python
bpy.context.scene.render.engine = 'CYCLES_EEVEE' # FAILS: TypeError
```

### Solution
Read available enum values directly from Blender's RNA metadata before setting:
```python
# To inspect valid render engines:
engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]

# Or use try/except:
try:
    bpy.context.scene.render.engine = 'TARGET_ENGINE'
except TypeError as e:
    # e.args contains the list of valid identifiers
    print("Available engines:", e)
```

---

## 4. Context Errors with `bpy.ops`

### Problem
Executing operator calls (`bpy.ops.mesh.primitive_cube_add()`, `bpy.ops.object.join()`, etc.) frequently throws:
`RuntimeError: Operator bpy.ops... failed, context is incorrect`
because Blender operators require an active 3D Viewport window context, which headless or background scripts do not have.

### Solution
1. **Prefer `bpy.data` and `bmesh`**:
   - Creating mesh: `bpy.data.meshes.new(...)` + `bpy.data.objects.new(...)` + `bmesh`.
   - Modifying geometry: Use `bmesh.from_edit_mesh(...)` or `bmesh.ops`.
2. **Context Override (Blender 3.2+)**:
   When `bpy.ops` is unavoidable, override the context:
   ```python
   with bpy.context.temp_override(active_object=target_obj, selected_objects=[target_obj]):
       bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
   ```

---

## 5. `generate_3d` Timeouts & Job Resumption

### Problem
Generative 3D providers usually take 1 to 3 minutes to produce a textured model. The tool default timeout is 45 seconds (`wait_seconds=45`). Calling `generate_3d` with a new prompt every time will trigger duplicate jobs, waste user credits, and leave previous jobs orphaned.

### Solution
Follow the asynchronous resumption pattern:
```
Step 1: generate_3d(prompt="steampunk mechanical owl", wait_seconds=45)
Result: {"status": "in_progress", "job": "job_12345abcdef"}

Step 2: generate_3d(job="job_12345abcdef", name="SteampunkOwl", wait_seconds=45)
Result: Imports the generated model once finished!
```
- NEVER generate a new model if a job ID was returned. Always poll with the existing `job`.
- Do NOT generate full scenes, landscapes, or multi-object rooms in one call. Request single atomic objects only.

---

## 6. Token Budget & Image Cost Management

### Problem
Repeated high-resolution `look` calls accumulate large base64/multimodal images in the conversation transcript, inflating token usage and slowing down subsequent turns.

### Solution
1. **Use `get_scene_info` First**:
   - For positions, bounding boxes, face counts, and names, always query `get_scene_info` (which returns compact text).
2. **Control `look` Image Size**:
   - Use `max_size=512` or `max_size=384` for fast spatial and layout checks.
   - Use `max_size=768` or higher only for final beauty shots or reading fine texture detail.
3. **Use Multi-angle framing**:
   - Instead of calling `look` 4 times from different angles, call it once with `mode="angles", views=["front", "right", "top"]`.

---

## 7. Floating or Buried Imported Models

### Problem
Models downloaded from Sketchfab, Poly Pizza, or generated via AI often have arbitrary scales (e.g. 100x too big or small) and their origin may be located at the geometric center rather than the bottom, causing them to clip through the floor.

### Solution
1. When importing with `import_asset`, always pass `target_size` (e.g. `1.0` for chairs, `0.15` for mugs).
2. Check `ground` field in `get_scene_info(fields=["ground", "placement"])`.
3. If floating or buried, execute the grounding script from `references/python_bpy_snippets.md` to shift `location.z` so the lowest bounding box vertex sits at $Z = 0$.

---

## 8. Telemetry and Privacy Requests

### Problem
The user requests that no screenshots, code, or prompt logs be collected.

### Solution
Call `disable_telemetry(user_prompt=...)` immediately.
Inform the user that telemetry is now disabled and can only be re-enabled from Blender's user preferences menu.
