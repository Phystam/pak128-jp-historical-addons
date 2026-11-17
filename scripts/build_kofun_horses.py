import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

OUT_DIR = r"g:\マイドライブ\Antigravity\Simutrans\vehicles\kofun_packhorse"
STANDING_PERSON_BLEND = r"g:\マイドライブ\Antigravity\Simutrans\components\yayoi_person_standing\yayoi_person_standing.blend"

HORSE_SCALE = 0.80
PERSON_SCALE = 0.84

os.makedirs(OUT_DIR, exist_ok=True)


def make_mat(name, color, roughness=0.75, metallic=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def get_materials():
    return {
        "coat_0": make_mat("Kiso_Coat_Bay_0", (0.28, 0.085, 0.028), roughness=0.72),
        "coat_1": make_mat("Kiso_Coat_Bay_1", (0.22, 0.065, 0.022), roughness=0.74),
        "coat_2": make_mat("Kiso_Coat_Bay_2", (0.34, 0.115, 0.038), roughness=0.70),
        "coat_dark": make_mat("Kiso_Coat_Dark", (0.12, 0.040, 0.015), roughness=0.75),
        "black": make_mat("Kiso_Black_Hair", (0.018, 0.014, 0.012), roughness=0.85),
        "hoof": make_mat("Kiso_Hoof", (0.075, 0.055, 0.042), roughness=0.65),
        "leather": make_mat("Kofun_Leather", (0.07, 0.032, 0.015), roughness=0.68),
        "aori": make_mat("Kofun_Aori", (0.13, 0.062, 0.035), roughness=0.75),
        "pad": make_mat("Kofun_Saddle_Pad", (0.72, 0.66, 0.56), roughness=0.85),
        "gold": make_mat("Kofun_Gilt_Bronze", (0.78, 0.56, 0.14), roughness=0.32, metallic=0.85),
        "iron": make_mat("Kofun_Iron", (0.32, 0.35, 0.42), roughness=0.40, metallic=0.80),
        "rein": make_mat("Kofun_Rein", (0.76, 0.72, 0.64), roughness=0.80),
        "pottery": make_mat("Kofun_Pottery", (0.48, 0.19, 0.07), roughness=0.70),
        "straw": make_mat("Kofun_Straw_Bale", (0.55, 0.41, 0.15), roughness=0.85),
        "rope": make_mat("Kofun_Rope", (0.24, 0.13, 0.04), roughness=0.88),
        "wood": make_mat("Kofun_Wood", (0.22, 0.11, 0.04), roughness=0.82),
        "cloth": make_mat("Yayoi_White_Cloth", (0.82, 0.72, 0.54), roughness=0.85),
        "cloth_alt": make_mat("Yayoi_Tunic_Alt", (0.68, 0.58, 0.42), roughness=0.85),
        "sash": make_mat("Yayoi_Hemp_Sash", (0.42, 0.28, 0.14), roughness=0.85),
        "skin": make_mat("Yayoi_Skin", (0.68, 0.40, 0.24), roughness=0.72),
        "hair": make_mat("Yayoi_Hair", (0.02, 0.015, 0.012), roughness=0.85),
        "mail_bag": make_mat("Kofun_Mail_Bag", (0.18, 0.08, 0.03), roughness=0.75),
    }


def add_capsule(bm, p0, p1, r0, r1, segs=8, mat_idx=0):
    p0 = Vector(p0)
    p1 = Vector(p1)
    vec = p1 - p0
    if vec.length < 1e-5:
        return
    z_axis = vec.normalized()
    up = Vector((0, 0, 1)) if abs(z_axis.z) < 0.9 else Vector((1, 0, 0))
    x_axis = up.cross(z_axis).normalized()
    y_axis = z_axis.cross(x_axis).normalized()
    rot = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
    before = len(bm.faces)
    rings = 3
    verts_rings = []
    for i in range(rings + 1):
        t = i / rings
        pos = p0.lerp(p1, t)
        r = r0 + (r1 - r0) * t
        ring = [
            bm.verts.new(
                pos + (rot @ Vector((math.cos(2 * math.pi * j / segs) * r,
                                     math.sin(2 * math.pi * j / segs) * r, 0)))
            )
            for j in range(segs)
        ]
        verts_rings.append(ring)
    for i in range(rings):
        for j in range(segs):
            jn = (j + 1) % segs
            bm.faces.new((verts_rings[i][j], verts_rings[i][jn], verts_rings[i + 1][jn], verts_rings[i + 1][j]))
    bm.faces.new(verts_rings[0][::-1])
    bm.faces.new(verts_rings[-1])
    for f in bm.faces[before:]:
        f.material_index = mat_idx


def add_ellipsoid(bm, center, radii, rot_euler=(0, 0, 0), segs=10, rings=6, mat_idx=0):
    before = len(bm.faces)
    mat_t = (
        Matrix.Translation(center)
        @ Matrix.Rotation(rot_euler[2], 4, "Z")
        @ Matrix.Rotation(rot_euler[1], 4, "Y")
        @ Matrix.Rotation(rot_euler[0], 4, "X")
        @ Matrix.Diagonal((*radii, 1.0))
    )
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0, matrix=mat_t)
    for f in bm.faces[before:]:
        f.material_index = mat_idx


def add_box(bm, center, size, rot_euler=(0, 0, 0), mat_idx=0):
    before = len(bm.faces)
    mat_t = (
        Matrix.Translation(center)
        @ Matrix.Rotation(rot_euler[2], 4, "Z")
        @ Matrix.Rotation(rot_euler[1], 4, "Y")
        @ Matrix.Rotation(rot_euler[0], 4, "X")
        @ Matrix.Diagonal((*size, 1.0))
    )
    bmesh.ops.create_cube(bm, size=1.0, matrix=mat_t)
    for f in bm.faces[before:]:
        f.material_index = mat_idx


def add_jar(bm, center, scale=1.0, rot_euler=(0, 0, 0), mat_idx=0, rope_idx=1):
    before = len(bm.faces)
    mat_t = (
        Matrix.Translation(center)
        @ Matrix.Rotation(rot_euler[2], 4, "Z")
        @ Matrix.Rotation(rot_euler[1], 4, "Y")
        @ Matrix.Rotation(rot_euler[0], 4, "X")
    )
    profile = [
        (0.000, 0.015),
        (0.015, 0.028),
        (0.032, 0.030),
        (0.048, 0.016),
        (0.060, 0.023),
        (0.065, 0.021),
    ]
    segs = 8
    rings = []
    for pz, pr in profile:
        ring = [
            bm.verts.new(
                mat_t @ Vector((math.cos(2 * math.pi * j / segs) * pr * scale,
                                math.sin(2 * math.pi * j / segs) * pr * scale,
                                (pz - 0.030) * scale))
            )
            for j in range(segs)
        ]
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(segs):
            jn = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][jn], rings[i + 1][jn], rings[i + 1][j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    for f in bm.faces[before:]:
        f.material_index = mat_idx

    before_r = len(bm.faces)
    r_mat = mat_t @ Matrix.Diagonal((0.032 * scale, 0.032 * scale, 0.005 * scale, 1.0))
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=1.0, matrix=r_mat)
    for f in bm.faces[before_r:]:
        f.material_index = rope_idx


def add_straw_bale(bm, center, radius=0.026, length=0.085, rot_euler=(0, 0, 0), mat_idx=0, rope_idx=1):
    mat_t = (
        Matrix.Translation(center)
        @ Matrix.Rotation(rot_euler[2], 4, "Z")
        @ Matrix.Rotation(rot_euler[1], 4, "Y")
        @ Matrix.Rotation(rot_euler[0], 4, "X")
    )
    before = len(bm.faces)
    segs = 8
    xs = [-0.5 * length, -0.38 * length, 0.0, 0.38 * length, 0.5 * length]
    rs = [0.75 * radius, radius, 1.04 * radius, radius, 0.75 * radius]
    rings = []
    for px, pr in zip(xs, rs):
        ring = [
            bm.verts.new(mat_t @ Vector((px, math.cos(2 * math.pi * j / segs) * pr, math.sin(2 * math.pi * j / segs) * pr)))
            for j in range(segs)
        ]
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(segs):
            jn = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][jn], rings[i + 1][jn], rings[i + 1][j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    for f in bm.faces[before:]:
        f.material_index = mat_idx

    for rx in (-0.28 * length, 0.0, 0.28 * length):
        before_r = len(bm.faces)
        r_mat = mat_t @ Matrix.Translation((rx, 0, 0)) @ Matrix.Diagonal((0.005, radius * 1.08, radius * 1.08, 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=1.0, matrix=r_mat)
        for f in bm.faces[before_r:]:
            f.material_index = rope_idx


def link_to_col(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def build_horse_obj(name, col, mats, loc=(0, 0, 0), yaw=0.0, coat_key="coat_0", stride_phase=0.0, lead_to=None):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    link_to_col(obj, col)
    mat_list = [
        mats[coat_key], mats["coat_dark"], mats["black"], mats["hoof"],
        mats["leather"], mats["aori"], mats["pad"], mats["gold"],
        mats["iron"], mats["rein"],
    ]
    for m in mat_list:
        obj.data.materials.append(m)
    bm = bmesh.new()

    # Body
    add_ellipsoid(bm, (0.00, 0.00, 0.148), (0.125, 0.056, 0.062), segs=12, rings=8, mat_idx=0)
    add_ellipsoid(bm, (0.075, 0.00, 0.152), (0.062, 0.050, 0.058), segs=10, rings=6, mat_idx=0)
    add_ellipsoid(bm, (-0.085, 0.00, 0.155), (0.062, 0.052, 0.056), segs=10, rings=6, mat_idx=0)
    # Neck & Head
    add_capsule(bm, (0.085, 0.0, 0.165), (0.155, 0.0, 0.245), 0.044, 0.030, segs=8, mat_idx=0)
    add_capsule(bm, (0.145, 0.0, 0.250), (0.215, 0.0, 0.210), 0.030, 0.017, segs=8, mat_idx=0)
    add_ellipsoid(bm, (0.212, 0.0, 0.210), (0.018, 0.016, 0.016), segs=8, rings=5, mat_idx=1)
    for sy in (-1, 1):
        add_capsule(bm, (0.142, sy * 0.018, 0.268), (0.148, sy * 0.022, 0.292), 0.008, 0.003, segs=6, mat_idx=0)
    # Mane & Tail
    add_capsule(bm, (0.075, 0.003, 0.195), (0.150, 0.003, 0.268), 0.022, 0.016, segs=6, mat_idx=2)
    add_ellipsoid(bm, (0.155, 0.002, 0.275), (0.018, 0.012, 0.016), segs=6, rings=4, mat_idx=2)
    add_capsule(bm, (-0.135, 0.0, 0.168), (-0.175, 0.0, 0.115), 0.015, 0.020, segs=6, mat_idx=2)
    add_capsule(bm, (-0.175, 0.0, 0.115), (-0.185, 0.0, 0.045), 0.020, 0.012, segs=6, mat_idx=2)
    # Legs
    s1 = math.sin(stride_phase) * 0.016
    s2 = -s1
    legs = [(0.088, -0.032, s1), (0.082, 0.032, s2), (-0.088, -0.032, s2), (-0.095, 0.032, s1)]
    for lx, ly, stride in legs:
        add_capsule(bm, (lx, ly, 0.135), (lx + stride * 0.5, ly, 0.072), 0.022, 0.015, segs=7, mat_idx=0)
        add_capsule(bm, (lx + stride * 0.5, ly, 0.072), (lx + stride, ly, 0.016), 0.015, 0.012, segs=7, mat_idx=2)
        add_capsule(bm, (lx + stride, ly, 0.016), (lx + stride + 0.003, ly, 0.000), 0.013, 0.015, segs=7, mat_idx=3)

    # Kofun Tack
    add_box(bm, (0.005, 0.0, 0.195), (0.095, 0.112, 0.030), mat_idx=6)
    add_box(bm, (0.042, 0.0, 0.222), (0.016, 0.088, 0.032), (0, 0.15, 0), mat_idx=4)
    add_box(bm, (-0.032, 0.0, 0.220), (0.016, 0.088, 0.030), (0, -0.15, 0), mat_idx=4)
    for sy in (-1, 1):
        add_box(bm, (0.005, sy * 0.058, 0.145), (0.095, 0.010, 0.080), (sy * 0.08, 0, 0), mat_idx=5)
        add_box(bm, (0.015, sy * 0.066, 0.110), (0.022, 0.010, 0.025), mat_idx=4)
    add_capsule(bm, (0.152, -0.024, 0.262), (0.152, 0.024, 0.262), 0.006, 0.006, segs=6, mat_idx=4)
    for sy in (-1, 1):
        add_capsule(bm, (0.152, sy * 0.023, 0.260), (0.205, sy * 0.018, 0.215), 0.005, 0.005, segs=6, mat_idx=4)
        add_ellipsoid(bm, (0.165, sy * 0.026, 0.248), (0.008, 0.005, 0.008), segs=6, rings=4, mat_idx=7)
        add_ellipsoid(bm, (0.205, sy * 0.020, 0.212), (0.009, 0.004, 0.009), segs=6, rings=4, mat_idx=8)
        add_capsule(bm, (0.205, sy * 0.020, 0.212), (0.140, sy * 0.035, 0.165), 0.004, 0.004, segs=5, mat_idx=9)
        add_capsule(bm, (0.140, sy * 0.035, 0.165), (0.050, sy * 0.030, 0.195), 0.004, 0.004, segs=5, mat_idx=9)
    add_ellipsoid(bm, (-0.110, 0.0, 0.205), (0.012, 0.012, 0.010), segs=8, rings=5, mat_idx=7)
    for sy in (-1, 1):
        add_capsule(bm, (-0.040, sy * 0.030, 0.195), (-0.110, 0.0, 0.205), 0.005, 0.005, segs=5, mat_idx=4)
        add_capsule(bm, (-0.110, 0.0, 0.205), (-0.115, sy * 0.052, 0.155), 0.005, 0.005, segs=5, mat_idx=4)
        add_capsule(bm, (-0.045, sy * 0.050, 0.175), (-0.138, sy * 0.020, 0.162), 0.005, 0.005, segs=5, mat_idx=4)
        add_ellipsoid(bm, (-0.090, sy * 0.053, 0.168), (0.008, 0.005, 0.008), segs=6, rings=4, mat_idx=7)

    # Optional lead rope to handler's hand (world coords converted to local unscaled coords)
    if lead_to is not None:
        p_local_end = (Vector(lead_to) - Vector(loc)) / HORSE_SCALE
        p_mid = (Vector((0.205, 0.0, 0.210)) + p_local_end) * 0.5 - Vector((0, 0, 0.025))
        add_capsule(bm, (0.205, 0.0, 0.210), p_mid, 0.004, 0.004, segs=5, mat_idx=9)
        add_capsule(bm, p_mid, p_local_end, 0.004, 0.004, segs=5, mat_idx=9)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = loc
    obj.rotation_euler = (0, 0, yaw)
    obj.scale = (HORSE_SCALE, HORSE_SCALE, HORSE_SCALE)
    return obj


def build_handler_obj(name, col, mats, loc=(0, 0, 0), yaw=0.0, alt_cloth=False):
    # Append Yayoi_Person_Standing_Obj or build matching standing handler
    with bpy.data.libraries.load(STANDING_PERSON_BLEND, link=False) as (df, dt):
        dt.objects = ["Yayoi_Person_Standing_Obj"]
    src_obj = dt.objects[0]
    src_obj.name = name
    link_to_col(src_obj, col)
    src_obj.location = loc
    src_obj.rotation_euler = (0, 0, yaw)
    src_obj.scale = (PERSON_SCALE, PERSON_SCALE, PERSON_SCALE)
    if alt_cloth and len(src_obj.data.materials) > 0:
        src_obj.data.materials[0] = mats["cloth_alt"]
    return src_obj


def build_rider_obj(name, col, mats, loc=(0, 0, 0), yaw=0.0, alt_cloth=False):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    link_to_col(obj, col)
    tunic = mats["cloth_alt"] if alt_cloth else mats["cloth"]
    for m in [tunic, mats["sash"], mats["skin"], mats["hair"], mats["mail_bag"]]:
        obj.data.materials.append(m)
    bm = bmesh.new()

    add_capsule(bm, (-0.01, 0.0, 0.215), (0.01, 0.0, 0.310), 0.032, 0.034, segs=8, mat_idx=0)
    add_capsule(bm, (-0.005, 0.0, 0.238), (0.00, 0.0, 0.252), 0.034, 0.034, segs=8, mat_idx=1)
    add_ellipsoid(bm, (0.015, 0.0, 0.345), (0.024, 0.022, 0.026), segs=8, rings=6, mat_idx=2)
    add_ellipsoid(bm, (0.012, 0.0, 0.354), (0.025, 0.023, 0.020), segs=8, rings=5, mat_idx=3)
    for sy in (-1, 1):
        add_ellipsoid(bm, (0.010, sy * 0.025, 0.335), (0.012, 0.010, 0.015), segs=6, rings=4, mat_idx=3)
    for sy in (-1, 1):
        add_capsule(bm, (0.010, sy * 0.036, 0.295), (0.055, sy * 0.028, 0.255), 0.012, 0.010, segs=6, mat_idx=0)
        add_capsule(bm, (0.055, sy * 0.028, 0.255), (0.085, sy * 0.018, 0.245), 0.009, 0.008, segs=6, mat_idx=2)
    for sy in (-1, 1):
        add_capsule(bm, (0.00, sy * 0.045, 0.215), (0.025, sy * 0.062, 0.160), 0.016, 0.013, segs=6, mat_idx=0)
        add_capsule(bm, (0.025, sy * 0.062, 0.160), (0.015, sy * 0.064, 0.105), 0.012, 0.010, segs=6, mat_idx=2)
    add_box(bm, (-0.035, 0.0, 0.265), (0.025, 0.045, 0.045), (0, 0.15, 0), mat_idx=4)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = loc
    obj.rotation_euler = (0, 0, yaw)
    obj.scale = (HORSE_SCALE, HORSE_SCALE, HORSE_SCALE)
    return obj


def build_pottery_load_obj(name, col, mats, loc=(0, 0, 0), yaw=0.0):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    link_to_col(obj, col)
    for m in [mats["pottery"], mats["rope"], mats["wood"]]:
        obj.data.materials.append(m)
    bm = bmesh.new()
    add_box(bm, (0.005, 0.0, 0.228), (0.095, 0.125, 0.012), mat_idx=2)
    for sy in (-1, 1):
        add_jar(bm, (0.025, sy * 0.080, 0.195), scale=1.05, rot_euler=(sy * 0.20, 0, 0), mat_idx=0, rope_idx=1)
        add_jar(bm, (-0.028, sy * 0.078, 0.195), scale=0.95, rot_euler=(sy * 0.20, 0, 0), mat_idx=0, rope_idx=1)
    add_jar(bm, (0.00, 0.0, 0.258), scale=1.10, rot_euler=(0.0, 0.15, 0), mat_idx=0, rope_idx=1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = loc
    obj.rotation_euler = (0, 0, yaw)
    obj.scale = (HORSE_SCALE, HORSE_SCALE, HORSE_SCALE)
    return obj


def build_rice_load_obj(name, col, mats, loc=(0, 0, 0), yaw=0.0):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    link_to_col(obj, col)
    for m in [mats["straw"], mats["rope"]]:
        obj.data.materials.append(m)
    bm = bmesh.new()
    for sy in (-1, 1):
        add_straw_bale(bm, (0.005, sy * 0.075, 0.195), radius=0.030, length=0.115, rot_euler=(sy * 0.18, 0, 0), mat_idx=0, rope_idx=1)
    add_straw_bale(bm, (0.005, 0.00, 0.245), radius=0.032, length=0.120, rot_euler=(0, 0, 0), mat_idx=0, rope_idx=1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = loc
    obj.rotation_euler = (0, 0, yaw)
    obj.scale = (HORSE_SCALE, HORSE_SCALE, HORSE_SCALE)
    return obj


# Formations: (x, y, z) with wider spacing
FORMATIONS = {
    2: [
        (0.06, -0.14, 0.0),
        (-0.04, 0.14, 0.0),
    ],
    4: [
        (0.24, -0.14, 0.0),
        (0.16, 0.14, 0.0),
        (-0.20, -0.14, 0.0),
        (-0.28, 0.14, 0.0),
    ],
    8: [
        (0.58, -0.14, 0.0),
        (0.52, 0.14, 0.0),
        (0.18, -0.14, 0.0),
        (0.12, 0.14, 0.0),
        (-0.22, -0.14, 0.0),
        (-0.28, 0.14, 0.0),
        (-0.62, -0.14, 0.0),
        (-0.68, 0.14, 0.0),
    ],
}

HANDLERS = {
    2: [(0.28, -0.05, 0.0)],
    4: [(0.46, -0.05, 0.0), (0.01, 0.02, 0.0)],
    8: [(0.80, -0.05, 0.0), (0.39, 0.02, 0.0), (-0.01, -0.05, 0.0), (-0.41, 0.02, 0.0)],
}

SPECS = [
    # Cargo (pottery default + rice)
    dict(mode="cargo", count=2, basename="kofun_packhorse_2_cargo", obj_name="Kofun_Packhorse_2_Cargo",
         length=5, speed=8, power=4, weight=1, payload=4, cost=25000, runningcost=8),
    dict(mode="cargo", count=4, basename="kofun_packhorse_4_cargo", obj_name="Kofun_Packhorse_4_Cargo",
         length=8, speed=8, power=8, weight=2, payload=8, cost=48000, runningcost=15),
    dict(mode="cargo", count=8, basename="kofun_packhorse_8_cargo", obj_name="Kofun_Packhorse_8_Cargo",
         length=14, speed=8, power=16, weight=4, payload=16, cost=92000, runningcost=28),
    # Mail (Post)
    dict(mode="post", count=2, basename="kofun_horse_2_post", obj_name="Kofun_Horse_2_Post",
         length=4, speed=15, power=4, weight=1, payload=6, cost=30000, runningcost=10),
    dict(mode="post", count=4, basename="kofun_horse_4_post", obj_name="Kofun_Horse_4_Post",
         length=8, speed=15, power=8, weight=2, payload=12, cost=58000, runningcost=18),
    dict(mode="post", count=8, basename="kofun_horse_8_post", obj_name="Kofun_Horse_8_Post",
         length=14, speed=15, power=16, weight=4, payload=24, cost=112000, runningcost=34),
]

COAT_KEYS = ["coat_0", "coat_1", "coat_2", "coat_0", "coat_2", "coat_1", "coat_0", "coat_1"]


def build_and_render(spec):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.preferences.addon_enable(module="simutrans_blender_kit")

    p = bpy.context.scene.simutrans
    p.pakset = "pak128"
    p.obj_type = "vehicle"
    p.obj_name = spec["obj_name"]
    p.basename = spec["basename"]
    p.out_dir = OUT_DIR
    p.author = "JP Historical Project"
    p.dirs = "8"
    p.waytype = "road"
    p.engine_type = "bio"
    p.speed = spec["speed"]
    p.power = spec["power"]
    p.gear = 100
    p.weight = spec["weight"]
    p.length = spec["length"]
    p.payload = spec["payload"]
    p.cost = spec["cost"]
    p.runningcost = spec["runningcost"]
    p.intro_year = 390
    p.retire_year = 2999
    p.anti_aliasing = True
    p.filter_size = 1.5

    if spec["mode"] == "cargo":
        p.freight = "pottery"
        p.freight_goods = "pottery, rice"
    else:
        p.freight = "Post"
        p.freight_goods = ""

    bpy.ops.simutrans.build_rig()
    bpy.ops.simutrans.create_template()

    mats = get_materials()
    base_col = bpy.data.collections.new("Kofun_Horse_Base")
    bpy.context.scene.collection.children.link(base_col)

    horse_locs = FORMATIONS[spec["count"]]
    handler_locs = HANDLERS[spec["count"]] if spec["mode"] == "cargo" else []

    if spec["mode"] == "cargo":
        f0_col = bpy.data.collections.get("freight_0")
        if f0_col is None:
            f0_col = bpy.data.collections.new("freight_0")
            bpy.context.scene.collection.children.link(f0_col)
        f1_col = bpy.data.collections.get("freight_1")
        if f1_col is None:
            f1_col = bpy.data.collections.new("freight_1")
            bpy.context.scene.collection.children.link(f1_col)

    for idx, h_loc in enumerate(horse_locs):
        yaw = 0.03 * ((idx % 3) - 1)
        phase = idx * 1.1
        coat_key = COAT_KEYS[idx % len(COAT_KEYS)]

        # Lead rope for pair leader
        lead_to = None
        if spec["mode"] == "cargo" and idx % 2 == 0:
            hl = handler_locs[idx // 2]
            lead_to = (hl[0] - 0.02, hl[1], 0.14)

        build_horse_obj(f"Horse_{idx}", base_col, mats, loc=h_loc, yaw=yaw,
                        coat_key=coat_key, stride_phase=phase, lead_to=lead_to)

        if spec["mode"] == "cargo":
            build_pottery_load_obj(f"Pottery_{idx}", f0_col, mats, loc=h_loc, yaw=yaw)
            build_rice_load_obj(f"Rice_{idx}", f1_col, mats, loc=h_loc, yaw=yaw)
        else:
            build_rider_obj(f"Rider_{idx}", base_col, mats, loc=h_loc, yaw=yaw, alt_cloth=(idx % 2 == 1))

    for idx, p_loc in enumerate(handler_locs):
        build_handler_obj(f"Handler_{idx}", base_col, mats, loc=p_loc, yaw=0.0, alt_cloth=(idx % 2 == 1))

    # Apply all transforms
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Save blend
    blend_path = os.path.join(OUT_DIR, f"{spec['basename']}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    # Validate & Render
    bpy.ops.simutrans.validate()
    bpy.ops.simutrans.render_sheet()
    bpy.ops.simutrans.check_colors()
    print(f"Finished {spec['basename']}!")


def main():
    for spec in SPECS:
        build_and_render(spec)
    print("ALL 6 ADDONS GENERATED!")


if __name__ == "__main__":
    main()
