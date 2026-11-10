# Simutrans Blender Kit Automation Recipes

End-to-end Python automation scripts designed to be executed via `execute_blender_code`.

---

## Recipe 1: Complete Building Creation & Render Pipeline

This recipe sets up a $1 \times 1$ residential building, builds the camera/sun rig, validates the geometry, renders the 4 rotation sheets, and writes the `.dat` file.

```python
import bpy
import os

# 1. Configure Simutrans Scene Properties
props = bpy.context.scene.simutrans
props.pakset = "pak128"
props.obj_type = "building"
props.btype = "res"
props.obj_name = "Modern_Apartment_1x1"
props.basename = "apartment_1x1"
props.author = "Antigravity"
props.size_x = 1
props.size_y = 1
props.layouts = 4          # Render all 4 rotational viewpoints
props.level = 3            # Demand level (capacity = 3 * 32 = 96)
props.chance = 100
props.intro_year = 1980

# Use absolute path for output!
output_dir = os.path.abspath("output/apartment_1x1")
os.makedirs(output_dir, exist_ok=True)
props.out_dir = output_dir

# 2. Build Camera & Lighting Rig
bpy.ops.simutrans.build_rig()

# 3. Create Required Collection Hierarchy
bpy.ops.simutrans.create_template()

# 4. Finalize Geometry Transforms (Apply Location/Rotation/Scale)
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 5. Validate Scene Setup
bpy.ops.simutrans.validate()

# 6. Render Full Sprite Sheet & Emit .dat
bpy.ops.simutrans.render_sheet()

# 7. Check for Accidental Reserved Colors
bpy.ops.simutrans.check_colors()

print(f"Building pipeline finished! Sheet and .dat saved to: {output_dir}")
```

---

## Recipe 2: Railway Vehicle Pipeline (Train / Wagon)

Sets up an 8-heading asymmetric diesel locomotive with speed, power, weight, and coupling constraints.

```python
import bpy
import os

props = bpy.context.scene.simutrans
props.pakset = "pak128"
props.obj_type = "vehicle"
props.waytype = "track"
props.engine_type = "diesel"
props.obj_name = "Class_66_Loco"
props.basename = "class_66"
props.dirs = "8"           # 8 asymmetric directions
props.speed = 120          # 120 km/h
props.power = 2400         # 2400 kW
props.weight = 126         # 126 tons
props.length = 12          # 12/16ths of a tile
props.payload = 0
props.cost = 4500000       # cents
props.runningcost = 320
props.intro_year = 1998

output_dir = os.path.abspath("output/class_66")
os.makedirs(output_dir, exist_ok=True)
props.out_dir = output_dir

# Rig & Template
bpy.ops.simutrans.build_rig()
bpy.ops.simutrans.create_template()

# Apply Transforms
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Preview single heading first
bpy.ops.simutrans.preview()

# Full Render
bpy.ops.simutrans.render_sheet()
bpy.ops.simutrans.check_colors()
print(f"Vehicle pipeline complete: {output_dir}")
```

---

## Recipe 3: Inserting Reusable Components

Automates placing rooftop air-conditioner units or props from `components/`:

```python
import bpy

# Rescan available components
bpy.ops.simutrans.refresh_components()

# Example: insert an existing component by name
try:
    bpy.ops.simutrans.insert_component(name="well")
    print("Inserted 'well' component successfully.")
except Exception as e:
    print(f"Component insertion note: {e}")
```

---

## Recipe 4: Compiling to `.pak` via `makeobj`

Once the sprite sheet and `.dat` have been exported:

```python
import bpy

# Run makeobj compiler
try:
    bpy.ops.simutrans.compile_pak()
    print("Compiled .pak file successfully!")
except Exception as e:
    print(f"Makeobj execution: {e}")
```
