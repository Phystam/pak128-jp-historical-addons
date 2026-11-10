# Blender Python (`bpy`) Scripting Cheatsheet for AI Agents

Robust, production-ready Python snippets designed for execution via `execute_blender_code`.

---

## 1. Safety Rules & Conventions

1. **Always wrap operations cleanly and print results**:
   ```python
   import bpy
   # Print objects created or values calculated so the agent gets feedback
   print("Created object:", obj.name)
   ```
2. **Retrieve Nodes by Type, NOT by Name**:
   Node names (like `"Principled BSDF"`) change depending on Blender's UI language. Always use:
   ```python
   principled = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
   ```
3. **Prefer Low-Level Data API over `bpy.ops`**:
   `bpy.ops` depends on the active context (viewport, active window, active object). If the context is wrong, `bpy.ops` throws errors like `RuntimeError: Operator bpy.ops... failed, context is incorrect`.
   Use `bpy.data.objects`, `bpy.data.meshes`, and `bmesh` whenever possible.

---

## 2. Scene Inspection & Diagnostics

### List All Objects with Types and Transforms
```python
import bpy

for obj in bpy.context.scene.objects:
    print(f"[{obj.type}] {obj.name} - Loc: {obj.location}, Rot: {obj.rotation_euler}, Scale: {obj.scale}")
```

### Inspect Material Nodes & Socket Names
```python
import bpy

obj = bpy.context.active_object
if obj and obj.active_material and obj.active_material.use_nodes:
    for node in obj.active_material.node_tree.nodes:
        print(f"Node: {node.name} (type: {node.type})")
        for inp in node.inputs:
            print(f"  Input: {inp.name} (default: {getattr(inp, 'default_value', 'N/A')})")
```

---

## 3. Object Creation & Transformation

### Creating Primitive Meshes Cleanly
```python
import bpy

# Create mesh datablock and object directly without relying on viewport context
mesh = bpy.data.meshes.new(name="CustomCubeMesh")
obj = bpy.data.objects.new(name="MyCube", object_data=mesh)
bpy.context.collection.objects.link(obj)

# Populate geometry using bmesh
import bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.to_mesh(mesh)
bm.free()

obj.location = (0.0, 0.0, 1.0)
print(f"Successfully created: {obj.name} at {obj.location}")
```

### Automatic Grounding (Snap Object Bottom to Z = 0)
When models are imported or generated, their origin may not be at the base. This calculates the world bounding box and aligns the bottom to $Z = 0$:
```python
import bpy
from mathutils import Vector

def ground_object(obj):
    # Ensure world transform matrix is updated
    bpy.context.view_layer.update()
    
    # Calculate lowest world Z coordinate from bounding box corners
    matrix_world = obj.matrix_world
    bbox_corners = [matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_z = min(corner.z for corner in bbox_corners)
    
    # Shift object up/down so min_z aligns with 0.0
    obj.location.z -= min_z
    bpy.context.view_layer.update()
    print(f"Grounded '{obj.name}': shifted Z by {-min_z:.4f}m. New location: {obj.location}")

active_obj = bpy.context.active_object
if active_obj:
    ground_object(active_obj)
```

### Scaling Object to Exact Target Size (BBox Dimensions)
```python
import bpy
from mathutils import Vector

def set_max_dimension(obj, target_size_meters):
    bpy.context.view_layer.update()
    dims = obj.dimensions
    max_dim = max(dims.x, dims.y, dims.z)
    if max_dim <= 0.0001:
        print("Object has negligible size, skipping scale.")
        return
    scale_factor = target_size_meters / max_dim
    obj.scale *= scale_factor
    bpy.context.view_layer.update()
    print(f"Scaled '{obj.name}' by {scale_factor:.4f} to fit {target_size_meters}m. Current dimensions: {obj.dimensions}")

# Example: scale active object to 1.5m
if bpy.context.active_object:
    set_max_dimension(bpy.context.active_object, 1.5)
```

---

## 4. Materials & Shaders

### Creating a PBR Material with Color and Roughness
```python
import bpy

def create_pbr_material(name, base_color=(0.8, 0.2, 0.2, 1.0), roughness=0.4, metallic=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    # Find Principled BSDF by type
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
        
    # Compatible across Blender 3.x and 4.x
    if "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = base_color
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
        
    return mat

obj = bpy.context.active_object
if obj and obj.type == 'MESH':
    mat = create_pbr_material("RedGlossy", base_color=(0.9, 0.1, 0.1, 1.0), roughness=0.15)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(f"Assigned material '{mat.name}' to '{obj.name}'")
```

### Adding an Emission Shader
```python
import bpy

mat = bpy.data.materials.new(name="GlowingCore")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()

output = nodes.new(type="ShaderNodeOutputMaterial")
emission = nodes.new(type="ShaderNodeEmission")
emission.inputs["Color"].default_value = (0.2, 0.8, 1.0, 1.0)
emission.inputs["Strength"].default_value = 5.0

mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
```

---

## 5. Lighting & Camera Setup

### Create a Three-Point Lighting Rig
```python
import bpy
import math

def add_light(name, light_type, location, energy, color=(1.0, 1.0, 1.0)):
    light_data = bpy.data.lights.new(name=name, type=light_type)
    light_data.energy = energy
    light_data.color = color
    light_obj = bpy.data.objects.new(name=name, object_data=light_data)
    light_obj.location = location
    bpy.context.collection.objects.link(light_obj)
    return light_obj

# Key Light (Strong, Warm)
add_light("KeyLight", 'AREA', (4.0, -4.0, 5.0), energy=800.0, color=(1.0, 0.95, 0.9))

# Fill Light (Softer, Cool)
add_light("FillLight", 'AREA', (-4.0, -3.0, 3.0), energy=300.0, color=(0.85, 0.9, 1.0))

# Rim/Back Light (Behind subject)
add_light("RimLight", 'POINT', (0.0, 5.0, 4.0), energy=600.0, color=(1.0, 1.0, 1.0))

print("Created 3-point lighting setup.")
```

### Point Camera at Target Object
```python
import bpy

camera_obj = bpy.data.objects.get("Camera")
target_obj = bpy.context.active_object

if camera_obj and target_obj:
    # Remove existing TrackTo constraints if any
    for c in camera_obj.constraints:
        if c.type == 'TRACK_TO':
            camera_obj.constraints.remove(c)
            
    track = camera_obj.constraints.new(type='TRACK_TO')
    track.target = target_obj
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'
    bpy.context.view_layer.update()
    print(f"Tracking '{target_obj.name}' with camera '{camera_obj.name}'.")
```

---

## 6. Rendering & Output Configuration

### Safe Render Engine and Output Resolution Setup
```python
import bpy

scene = bpy.context.scene

# Safely set render engine
valid_engines = [item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
print("Available render engines:", valid_engines)

# Use Cycles or EEVEE
target_engine = 'CYCLES' if 'CYCLES' in valid_engines else valid_engines[0]
scene.render.engine = target_engine

# Output Settings
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100

# Set image format safely
formats = [i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties["file_format"].enum_items]
if "PNG" in formats:
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

print(f"Configured render settings: Engine={scene.render.engine}, Res={scene.render.resolution_x}x{scene.render.resolution_y}")
```

---

## 7. Modifiers & Mesh Operations

### Add Subdivision Surface & Smooth Shading
```python
import bpy

obj = bpy.context.active_object
if obj and obj.type == 'MESH':
    # Smooth Shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
        
    # Subsurf modifier
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 2
    subsurf.render_levels = 2
    print(f"Applied smooth shading and Subsurf modifier to '{obj.name}'")
```

### Join Selected Mesh Objects Safely
```python
import bpy

# Select multiple objects
mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and "Part" in o.name]
if len(mesh_objs) > 1:
    bpy.ops.object.select_all(action='DESELECT')
    for o in mesh_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    print(f"Joined {len(mesh_objs)} objects into '{mesh_objs[0].name}'")
```
