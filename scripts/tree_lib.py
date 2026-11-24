"""
Reusable Pak128 Botanical Tree Modeling & 5-Season Surface Rendering Library
============================================================================

Builds multi-angle alpha-cutout leaf-cluster trees (`pine`, `broadleaf`, `cedar`,
`sakura`) in Blender 5.2 / EEVEE Next with:
  - Volume-unified custom split normals (`normals_split_custom_set_from_vertices`)
    so flat foliage cards shade seamlessly as a cohesive organic volume
  - Vertex color attribute `Col` (`R`=cavity AO, `G`=card tint var, `B`=crown height)
  - Sharp binary cutout foliage shader (`DITHERED` + micro-bump + world noise dapple)
  - 5-season pak128-calibrated palettes (including bare-branch winter `s=2` and snow `s=4`)
  - Soft non-shadow-casting radial grounding shade pad (`BLENDED` + `LightPath`)

Intended to stay standalone and importable from any Simutrans asset builder.
"""

import math
import os
import random
import bmesh
import bpy
from mathutils import Vector, Matrix

BASE_DIR = r"g:\マイドライブ\Antigravity\Simutrans"
TEX_DIR = os.path.join(BASE_DIR, "Texture")

TREE_MAT_KEYS = [
    "trunk",               # 0: Organic tapered bark & branches
    "pine_foliage",        # 1: Layered evergreen pine boughs
    "broadleaf_foliage",   # 2: Seasonal broadleaf canopy (Kunugi/Zelkova)
    "cedar_foliage",       # 3: Tall dark conifer canopy (Sugi/Hinoki)
    "sakura_foliage",      # 4: Mountain cherry (blossom+bronze leaves in spring s=3)
    "shadow_pad",          # 5: Soft radial grounding shade pad under crown
]
TREE_MAT_IDX = {k: i for i, k in enumerate(TREE_MAT_KEYS)}

KIND_TO_MAT_KEY = {
    "pine": "pine_foliage",
    "broadleaf": "broadleaf_foliage",
    "deciduous": "broadleaf_foliage",
    "cedar": "cedar_foliage",
    "sakura": "sakura_foliage",
}


def _load_tex_image(filename):
    path = os.path.join(TEX_DIR, filename)
    norm = os.path.normpath(path)
    for img in bpy.data.images:
        if os.path.normpath(img.filepath) == norm:
            return img
    return bpy.data.images.load(path, check_existing=True)


def _rgba_mix_mul(nt, col_a, col_b_rgba):
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if isinstance(col_b_rgba, (tuple, list)):
        mix.inputs[7].default_value = tuple(col_b_rgba)
    else:
        nt.links.new(col_b_rgba, mix.inputs[7])
    nt.links.new(col_a, mix.inputs[6])
    return mix.outputs[2]


def _rgba_mix_blend(nt, fac_sock, col_a, col_b):
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    nt.links.new(fac_sock, mix.inputs["Factor"])
    if isinstance(col_a, (tuple, list)):
        mix.inputs[6].default_value = tuple(col_a)
    else:
        nt.links.new(col_a, mix.inputs[6])
    if isinstance(col_b, (tuple, list)):
        mix.inputs[7].default_value = tuple(col_b)
    else:
        nt.links.new(col_b, mix.inputs[7])
    return mix.outputs[2]


def _make_bark_mat(name, tint, snow=False):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.92
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.10

    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.2, 2.2, 2.2)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = _load_tex_image("丸太_樹皮.png")
    tx.projection = "BOX"
    tx.projection_blend = 0.22
    tx.extension = "REPEAT"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])

    base_col = _rgba_mix_mul(nt, tx.outputs["Color"], (*tint, 1.0))

    if snow:
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 8.0
        noise.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(geom.outputs["Normal"], sep.inputs["Vector"])

        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[1].default_value = 0.5
        mul_n = nt.nodes.new("ShaderNodeMath")
        mul_n.operation = "MULTIPLY"
        mul_n.inputs[1].default_value = 0.16
        add_n = nt.nodes.new("ShaderNodeMath")
        add_n.operation = "ADD"
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.52
        mul_c = nt.nodes.new("ShaderNodeMath")
        mul_c.operation = "MULTIPLY"
        mul_c.inputs[1].default_value = 0.72

        nt.links.new(noise.outputs["Fac"], sub.inputs[0])
        nt.links.new(sub.outputs["Value"], mul_n.inputs[0])
        nt.links.new(sep.outputs["Z"], add_n.inputs[0])
        nt.links.new(mul_n.outputs["Value"], add_n.inputs[1])
        nt.links.new(add_n.outputs["Value"], gt.inputs["Value"])
        nt.links.new(gt.outputs["Value"], mul_c.inputs[0])

        base_col = _rgba_mix_blend(nt, mul_c.outputs["Value"], base_col, (0.84, 0.87, 0.92, 1.0))

    nt.links.new(base_col, bsdf.inputs["Base Color"])
    return mat


def _make_foliage_mat(name, tex_filename, tint, alt_tint=None, alpha_thresh=0.44,
                      winter_thin=0.0, snow=False, snow_threshold=0.62, cov=0.92):
    """
    Create alpha-cutout EEVEE Next foliage shader with:
      - UVMap texture + bilinear-bleed CLIP sampling
      - Vertex Col attribute (`X`=cavity AO, `Y`=card variation, `Z`=crown height)
      - Subtle 3D world-space macro color dapple & bump micro-relief
      - Crisp binary Alpha cutout (`DITHERED`), optional seasonal leaf thinning, snow caps
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"

    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.90
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.08

    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = _load_tex_image(tex_filename)
    tx.extension = "CLIP"
    tx.interpolation = "Linear"
    nt.links.new(uv.outputs["UV"], tx.inputs["Vector"])

    # Vertex color Col: X=AO, Y=CardVar, Z=HeightNorm
    vcol = nt.nodes.new("ShaderNodeAttribute")
    vcol.attribute_name = "Col"
    sep_c = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(vcol.outputs["Color"], sep_c.inputs["Vector"])

    # 3D world-space canopy dapple noise (breaks up repetitive card colors across tree)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 14.0
    noise.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    mr_dap = nt.nodes.new("ShaderNodeMapRange")
    mr_dap.inputs["From Min"].default_value = 0.30
    mr_dap.inputs["From Max"].default_value = 0.70
    mr_dap.inputs["To Min"].default_value = 0.84
    mr_dap.inputs["To Max"].default_value = 1.14
    mr_dap.clamp = True
    nt.links.new(noise.outputs["Fac"], mr_dap.inputs["Value"])

    # Combine AO * CardVar * WorldDapple scalar
    mul_vc = nt.nodes.new("ShaderNodeMath")
    mul_vc.operation = "MULTIPLY"
    nt.links.new(sep_c.outputs["X"], mul_vc.inputs[0])
    nt.links.new(sep_c.outputs["Y"], mul_vc.inputs[1])

    mul_shade = nt.nodes.new("ShaderNodeMath")
    mul_shade.operation = "MULTIPLY"
    nt.links.new(mul_vc.outputs["Value"], mul_shade.inputs[0])
    nt.links.new(mr_dap.outputs["Result"], mul_shade.inputs[1])

    # Seasonal tint (optionally mottled between primary tint & alt_tint e.g. autumn foliage)
    if alt_tint is not None:
        n_var = nt.nodes.new("ShaderNodeTexNoise")
        n_var.inputs["Scale"].default_value = 6.5
        n_var.inputs["Detail"].default_value = 2.5
        nt.links.new(tc.outputs["Object"], n_var.inputs["Vector"])
        mr_t = nt.nodes.new("ShaderNodeMapRange")
        mr_t.inputs["From Min"].default_value = 0.36
        mr_t.inputs["From Max"].default_value = 0.64
        mr_t.clamp = True
        nt.links.new(n_var.outputs["Fac"], mr_t.inputs["Value"])
        tint_sock = _rgba_mix_blend(nt, mr_t.outputs["Result"], (*tint, 1.0), (*alt_tint, 1.0))
        base_col = _rgba_mix_mul(nt, tx.outputs["Color"], tint_sock)
    else:
        base_col = _rgba_mix_mul(nt, tx.outputs["Color"], (*tint, 1.0))

    # Apply AO * CardVar * WorldDapple as RGB multiplier
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mul_shade.outputs["Value"], comb.inputs["X"])
    nt.links.new(mul_shade.outputs["Value"], comb.inputs["Y"])
    nt.links.new(mul_shade.outputs["Value"], comb.inputs["Z"])
    lit_col = _rgba_mix_mul(nt, base_col, comb.outputs["Vector"])

    # Micro-bump from leaf texture luminance + fine noise
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(tx.outputs["Color"], bw.inputs["Color"])
    n_bump = nt.nodes.new("ShaderNodeTexNoise")
    n_bump.inputs["Scale"].default_value = 18.0
    n_bump.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], n_bump.inputs["Vector"])
    add_b = nt.nodes.new("ShaderNodeMath")
    add_b.operation = "ADD"
    nt.links.new(bw.outputs["Val"], add_b.inputs[0])
    nt.links.new(n_bump.outputs["Fac"], add_b.inputs[1])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.32
    bump.inputs["Distance"].default_value = 0.035
    nt.links.new(add_b.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Snow overlay on upper canopy surfaces in winter snow (s=4)
    if snow:
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        sep_n = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geom.outputs["Normal"], sep_n.inputs["Vector"])

        m_nz = nt.nodes.new("ShaderNodeMath")
        m_nz.operation = "MULTIPLY"
        m_nz.inputs[1].default_value = 0.65
        nt.links.new(sep_n.outputs["Z"], m_nz.inputs[0])

        m_ht = nt.nodes.new("ShaderNodeMath")
        m_ht.operation = "MULTIPLY"
        m_ht.inputs[1].default_value = 0.42
        nt.links.new(sep_c.outputs["Z"], m_ht.inputs[0])

        sub_sn = nt.nodes.new("ShaderNodeMath")
        sub_sn.operation = "SUBTRACT"
        sub_sn.inputs[1].default_value = 0.5
        nt.links.new(noise.outputs["Fac"], sub_sn.inputs[0])
        m_sn = nt.nodes.new("ShaderNodeMath")
        m_sn.operation = "MULTIPLY"
        m_sn.inputs[1].default_value = 0.24
        nt.links.new(sub_sn.outputs["Value"], m_sn.inputs[0])

        add1 = nt.nodes.new("ShaderNodeMath")
        add1.operation = "ADD"
        nt.links.new(m_nz.outputs["Value"], add1.inputs[0])
        nt.links.new(m_ht.outputs["Value"], add1.inputs[1])

        add2 = nt.nodes.new("ShaderNodeMath")
        add2.operation = "ADD"
        nt.links.new(add1.outputs["Value"], add2.inputs[0])
        nt.links.new(m_sn.outputs["Value"], add2.inputs[1])

        gt_s = nt.nodes.new("ShaderNodeMath")
        gt_s.operation = "GREATER_THAN"
        gt_s.inputs[1].default_value = snow_threshold
        nt.links.new(add2.outputs["Value"], gt_s.inputs["Value"])

        mul_cov = nt.nodes.new("ShaderNodeMath")
        mul_cov.operation = "MULTIPLY"
        mul_cov.inputs[1].default_value = cov
        nt.links.new(gt_s.outputs["Value"], mul_cov.inputs[0])

        lit_col = _rgba_mix_blend(nt, mul_cov.outputs["Value"], lit_col, (0.84, 0.87, 0.92, 1.0))

    nt.links.new(lit_col, bsdf.inputs["Base Color"])

    # Sharp binary alpha cutout + optional winter leaf thinning
    if winter_thin > 0.0:
        n_thin = nt.nodes.new("ShaderNodeTexNoise")
        n_thin.inputs["Scale"].default_value = 5.5
        n_thin.inputs["Detail"].default_value = 2.0
        nt.links.new(tc.outputs["Object"], n_thin.inputs["Vector"])

        mr_th = nt.nodes.new("ShaderNodeMapRange")
        mr_th.inputs["From Min"].default_value = 0.34
        mr_th.inputs["From Max"].default_value = 0.66
        mr_th.clamp = True
        nt.links.new(n_thin.outputs["Fac"], mr_th.inputs["Value"])

        mul_a = nt.nodes.new("ShaderNodeMath")
        mul_a.operation = "MULTIPLY"
        nt.links.new(tx.outputs["Alpha"], mul_a.inputs[0])
        nt.links.new(mr_th.outputs["Result"], mul_a.inputs[1])

        gt_a = nt.nodes.new("ShaderNodeMath")
        gt_a.operation = "GREATER_THAN"
        gt_a.inputs[1].default_value = winter_thin
        nt.links.new(mul_a.outputs["Value"], gt_a.inputs["Value"])
        nt.links.new(gt_a.outputs["Value"], bsdf.inputs["Alpha"])
    else:
        gt_a = nt.nodes.new("ShaderNodeMath")
        gt_a.operation = "GREATER_THAN"
        gt_a.inputs[1].default_value = alpha_thresh
        nt.links.new(tx.outputs["Alpha"], gt_a.inputs["Value"])
        nt.links.new(gt_a.outputs["Value"], bsdf.inputs["Alpha"])

    return mat


def _make_shadow_pad_mat(name, snow=False):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    nt = mat.node_tree
    nt.nodes.clear()

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if snow:
        bsdf.inputs["Base Color"].default_value = (0.22, 0.26, 0.34, 1.0)
        max_alpha = 0.20
    else:
        bsdf.inputs["Base Color"].default_value = (0.03, 0.05, 0.02, 1.0)
        max_alpha = 0.28
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0

    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs["Vector"])

    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.interpolation_type = "SMOOTHSTEP"
    mr.clamp = True
    mr.inputs["From Min"].default_value = 0.04
    mr.inputs["From Max"].default_value = 0.96
    mr.inputs["To Min"].default_value = max_alpha
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["X"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Alpha"])

    # Never cast own shadow onto ground diamond
    lp = nt.nodes.new("ShaderNodeLightPath")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[2])

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def create_tree_materials():
    """Create and return `{tree_slot_key: {season_0..4: Material}}`."""
    mats = {k: {} for k in TREE_MAT_KEYS}
    for s in range(5):
        snow = (s == 4)
        mats["trunk"][s] = _make_bark_mat(f"TreeLib_Trunk_S{s}", (0.64, 0.56, 0.48), snow=snow)

        # Pine: lush deep Japanese evergreen
        p_tint = (0.19, 0.34, 0.14) if s in (0, 3) else (0.16, 0.29, 0.12)
        mats["pine_foliage"][s] = _make_foliage_mat(
            f"TreeLib_Pine_S{s}", "foliage_pine_cluster.png",
            tint=p_tint, snow=snow, snow_threshold=0.60, cov=0.92,
        )

        # Cedar: darker cool conifer green
        c_tint = (0.15, 0.28, 0.14) if s in (0, 3) else (0.13, 0.24, 0.12)
        mats["cedar_foliage"][s] = _make_foliage_mat(
            f"TreeLib_Cedar_S{s}", "foliage_pine_cluster.png",
            tint=c_tint, snow=snow, snow_threshold=0.58, cov=0.92,
        )

        # Broadleaf (5-season natural palette)
        if s == 0:
            mats["broadleaf_foliage"][s] = _make_foliage_mat(
                "TreeLib_Broad_S0", "foliage_broadleaf_cluster.png",
                tint=(0.24, 0.41, 0.14), alt_tint=(0.28, 0.46, 0.16),
            )
        elif s == 1:
            mats["broadleaf_foliage"][s] = _make_foliage_mat(
                "TreeLib_Broad_S1", "foliage_broadleaf_cluster.png",
                tint=(0.62, 0.28, 0.08), alt_tint=(0.74, 0.44, 0.11),
            )
        elif s == 2:
            mats["broadleaf_foliage"][s] = _make_foliage_mat(
                "TreeLib_Broad_S2", "foliage_broadleaf_cluster.png",
                tint=(0.30, 0.21, 0.12), alt_tint=(0.36, 0.25, 0.15),
                winter_thin=0.56,
            )
        elif s == 3:
            mats["broadleaf_foliage"][s] = _make_foliage_mat(
                "TreeLib_Broad_S3", "foliage_broadleaf_cluster.png",
                tint=(0.33, 0.50, 0.17), alt_tint=(0.39, 0.54, 0.20),
            )
        else:
            mats["broadleaf_foliage"][s] = _make_foliage_mat(
                "TreeLib_Broad_S4", "foliage_broadleaf_cluster.png",
                tint=(0.25, 0.20, 0.15), winter_thin=0.36,
                snow=True, snow_threshold=0.56, cov=0.92,
            )

        # Sakura: natural cherry blossom + bronze young leaf spray in Spring (s=3); shares broadleaf look otherwise
        if s == 3:
            mats["sakura_foliage"][s] = _make_foliage_mat(
                "TreeLib_Sakura_S3", "foliage_sakura_cluster.png",
                tint=(0.92, 0.86, 0.88),
            )
        else:
            mats["sakura_foliage"][s] = mats["broadleaf_foliage"][s]

        mats["shadow_pad"][s] = _make_shadow_pad_mat(
            f"TreeLib_Shadow_S{s}", snow=snow,
        )
    return mats


def apply_tree_season(bpy_mod, tree_mats, season_idx):
    """Switch materials on all objects managed by tree_lib."""
    for ob in bpy_mod.data.objects:
        if ob.type != "MESH" or not ob.get("is_tree_lib"):
            continue
        for i, key in enumerate(TREE_MAT_KEYS):
            if i < len(ob.data.materials):
                ob.data.materials[i] = tree_mats[key][season_idx]


# ==============================================================================
# World-Space Geometry Builders (Tapered Limbs, Crossed Leaf Cards, Custom Normals)
# ==============================================================================
def _add_branch_tube(bm, uv_layer, vert_meta, points, radii, segments=6, mat_idx=0):
    """Extrude a smooth curved tapered branch/trunk along `points` in world coordinates."""
    rings = []
    n_pts = len(points)
    for k, (pt, rad) in enumerate(zip(points, radii)):
        p = Vector(pt)
        if k == 0:
            t_vec = (Vector(points[1]) - p).normalized()
        elif k == n_pts - 1:
            t_vec = (p - Vector(points[-2])).normalized()
        else:
            t_vec = (Vector(points[k + 1]) - Vector(points[k - 1])).normalized()
        up_ref = Vector((0.0, 0.0, 1.0)) if abs(t_vec.z) < 0.92 else Vector((1.0, 0.0, 0.0))
        u_vec = t_vec.cross(up_ref).normalized()
        v_vec = t_vec.cross(u_vec).normalized()

        ring = []
        for si in range(segments):
            ang = 2.0 * math.pi * si / segments
            offset = (u_vec * math.cos(ang) + v_vec * math.sin(ang)) * rad
            vx = bm.verts.new(p + offset)
            n_dir = offset.normalized()
            vert_meta.append(("trunk", n_dir, (0.8, 1.0, 0.5, 1.0)))
            ring.append(vx)
        rings.append(ring)

    for k in range(n_pts - 1):
        r0, r1 = rings[k], rings[k + 1]
        for si in range(segments):
            ni = (si + 1) % segments
            f = bm.faces.new((r0[si], r0[ni], r1[ni], r1[si]))
            f.material_index = mat_idx
            f.smooth = True
            for lp in f.loops:
                lp[uv_layer].uv = (0.0, 0.0)


def _add_leaf_quad(bm, uv_layer, vert_meta, center, quat_mat, half_w, half_h,
                   mat_idx, custom_n, col_rgba):
    local = [
        Vector((-half_w, -half_h, 0.0)),
        Vector(( half_w, -half_h, 0.0)),
        Vector(( half_w,  half_h, 0.0)),
        Vector((-half_w,  half_h, 0.0)),
    ]
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    vs = []
    for p in local:
        v = bm.verts.new(center + (quat_mat @ p))
        vert_meta.append(("foliage", custom_n, col_rgba))
        vs.append(v)
    f = bm.faces.new(vs)
    f.material_index = mat_idx
    f.smooth = True
    for lp, uv_val in zip(f.loops, uvs):
        lp[uv_layer].uv = uv_val


def _add_tuft(bm, uv_layer, vert_meta, center, lobe_center, crown_center, crown_z0, crown_z1,
              card_w, card_h, mat_idx, rng, flat_mode=False, z_bias=0.28):
    """
    Place 2 intersecting rotated foliage cards at `center` with unified volumetric normal
    and baked cavity AO (`Col.R`) + random variation (`Col.G`) + normalized crown height (`Col.B`).
    """
    c_vec = Vector(center)
    cr_c = Vector(crown_center)
    lb_c = Vector(lobe_center)

    v_cr = c_vec - cr_c
    d_cr = v_cr.length
    n_cr = v_cr.normalized() if d_cr > 1e-4 else Vector((0.0, 0.0, 1.0))

    v_lb = c_vec - lb_c
    d_lb = v_lb.length
    n_lb = v_lb.normalized() if d_lb > 1e-4 else n_cr

    n_blend = (0.55 * n_cr + 0.45 * n_lb + Vector((0.0, 0.0, z_bias))).normalized()

    # Baked cavity AO: darker toward crown core and underside, brighter at outer top perimeter
    zn = max(0.0, min(1.0, (c_vec.z - crown_z0) / max(0.05, crown_z1 - crown_z0)))
    rad_n = min(1.0, d_lb / max(0.05, card_w * 0.85))
    ao = max(0.52, min(1.08, 0.52 + 0.30 * rad_n + 0.26 * zn))
    c_var = rng.uniform(0.86, 1.14)
    col_rgba = (ao, c_var, zn, 1.0)

    yaw = rng.uniform(0.0, 2.0 * math.pi)
    for plane_i in range(2):
        if flat_mode:
            pitch = math.radians(rng.uniform(12.0, 28.0) if plane_i == 0 else rng.uniform(48.0, 68.0))
            roll = math.radians(rng.uniform(-16.0, 16.0))
            dyaw = yaw + (0.0 if plane_i == 0 else rng.uniform(1.2, 2.0))
        else:
            pitch = math.radians(rng.uniform(32.0, 68.0))
            roll = math.radians(rng.uniform(-22.0, 22.0))
            dyaw = yaw + plane_i * (math.pi * 0.5) + rng.uniform(-0.25, 0.25)

        rot = Matrix.Rotation(dyaw, 3, "Z") @ Matrix.Rotation(pitch, 3, "X") @ Matrix.Rotation(roll, 3, "Y")
        _add_leaf_quad(bm, uv_layer, vert_meta, c_vec, rot, card_w * 0.5, card_h * 0.5, mat_idx, n_blend, col_rgba)


def _add_ground_shadow_pad(bm, uv_layer, vert_meta, tx, ty, tz, r_in, r_out, mat_idx, segs=16):
    r0 = []
    r1 = []
    n_up = Vector((0.0, 0.0, 1.0))
    for i in range(segs):
        ang = 2.0 * math.pi * i / segs
        ca, sa = math.cos(ang), math.sin(ang)
        r0.append(bm.verts.new((tx + r_in * ca, ty + r_in * sa, tz + 0.001)))
        vert_meta.append(("pad", n_up, (1.0, 1.0, 0.0, 1.0)))
        r1.append(bm.verts.new((tx + r_out * ca, ty + r_out * sa, tz + 0.001)))
        vert_meta.append(("pad", n_up, (1.0, 1.0, 0.0, 1.0)))

    # Center cap
    f_c = bm.faces.new(r0)
    f_c.material_index = mat_idx
    for lp in f_c.loops:
        lp[uv_layer].uv = (0.0, 0.5)

    for i in range(segs):
        ni = (i + 1) % segs
        f = bm.faces.new((r0[i], r1[i], r1[ni], r0[ni]))
        f.material_index = mat_idx
        for lp, u in zip(f.loops, ((0.0, 0.5), (1.0, 0.5), (1.0, 0.5), (0.0, 0.5))):
            lp[uv_layer].uv = u


# ==============================================================================
# Archetype Crown Builders
# ==============================================================================
def _build_pine_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng):
    mat_leaf = TREE_MAT_IDX["pine_foliage"]
    lean_x = rng.uniform(-0.045, 0.045) * scale
    lean_y = rng.uniform(-0.045, 0.045) * scale

    trunk_pts = [
        (tx, ty, tz),
        (tx + lean_x * 0.35, ty + lean_y * 0.35, tz + 0.11 * scale),
        (tx + lean_x * 0.85, ty + lean_y * 0.65, tz + 0.22 * scale),
        (tx + lean_x * 1.15, ty + lean_y * 1.05, tz + 0.33 * scale),
    ]
    trunk_rad = [0.032 * scale, 0.022 * scale, 0.017 * scale, 0.010 * scale]
    _add_branch_tube(bm, uv_layer, vert_meta, trunk_pts, trunk_rad, segments=6, mat_idx=TREE_MAT_IDX["trunk"])

    # 4 asymmetric horizontal boughs + central overlapping cloud pads
    pad_specs = [
        (0.0,   0.075, 0.27, 0.125, 0.055),
        (-0.070, -0.042, 0.24, 0.115, 0.050),
        (0.068, -0.055, 0.31, 0.115, 0.050),
        (0.005,  0.005, 0.37, 0.145, 0.060),
    ]
    base_ang = rng.uniform(0.0, 2.0 * math.pi)
    ca, sa = math.cos(base_ang), math.sin(base_ang)
    crown_c = (tx + lean_x * 0.7, ty + lean_y * 0.7, tz + 0.31 * scale)
    z0_c, z1_c = tz + 0.20 * scale, tz + 0.44 * scale

    for idx, (ox, oy, oz, pr, ph) in enumerate(pad_specs):
        rx = tx + (ox * ca - oy * sa) * scale + lean_x * 0.8
        ry = ty + (ox * sa + oy * ca) * scale + lean_y * 0.8
        rz = tz + oz * scale
        attach_z = tz + min(0.30, oz - 0.04) * scale
        _add_branch_tube(
            bm, uv_layer, vert_meta,
            [(tx + lean_x * 0.8, ty + lean_y * 0.8, attach_z), (rx, ry, rz - 0.015 * scale)],
            [0.013 * scale, 0.006 * scale], segments=5, mat_idx=TREE_MAT_IDX["trunk"],
        )
        n_tufts = 9 if idx == 3 else 7
        for ti in range(n_tufts):
            ang = 2.0 * math.pi * ti / n_tufts + rng.uniform(-0.3, 0.3)
            rr = 0.0 if ti == 0 else rng.uniform(0.25, 0.92) * pr * scale
            pt = (
                rx + rr * math.cos(ang),
                ry + rr * math.sin(ang),
                rz + rng.uniform(-0.55, 0.75) * ph * scale,
            )
            c_sz = rng.uniform(0.115, 0.155) * scale
            _add_tuft(bm, uv_layer, vert_meta, pt, (rx, ry, rz), crown_c, z0_c, z1_c,
                      c_sz, c_sz, mat_leaf, rng, flat_mode=True, z_bias=0.45)


def _build_deciduous_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng, mat_leaf):
    lean_x = rng.uniform(-0.025, 0.025) * scale
    lean_y = rng.uniform(-0.025, 0.025) * scale
    fork_pt = (tx + lean_x, ty + lean_y, tz + 0.18 * scale)

    _add_branch_tube(
        bm, uv_layer, vert_meta,
        [(tx, ty, tz), (tx + lean_x * 0.4, ty + lean_y * 0.4, tz + 0.09 * scale), fork_pt],
        [0.034 * scale, 0.024 * scale, 0.019 * scale],
        segments=6, mat_idx=TREE_MAT_IDX["trunk"],
    )

    # 5 main diverging limbs (visible through bare twigs in winter s=2!)
    b_ang0 = rng.uniform(0.0, 2.0 * math.pi)
    lobes = [(fork_pt[0], fork_pt[1], tz + 0.37 * scale, 0.125 * scale)]  # high central lobe
    for bi in range(4):
        ang = b_ang0 + bi * (math.pi * 0.5) + rng.uniform(-0.30, 0.30)
        reach = rng.uniform(0.09, 0.125) * scale
        lz = tz + rng.uniform(0.25, 0.33) * scale
        lobe_c = (fork_pt[0] + reach * math.cos(ang), fork_pt[1] + reach * math.sin(ang), lz)
        lobes.append((*lobe_c, rng.uniform(0.095, 0.120) * scale))

        mid_pt = (fork_pt[0] + 0.55 * reach * math.cos(ang), fork_pt[1] + 0.55 * reach * math.sin(ang), tz + 0.22 * scale)
        _add_branch_tube(bm, uv_layer, vert_meta, [fork_pt, mid_pt, lobe_c],
                         [0.015 * scale, 0.010 * scale, 0.006 * scale],
                         segments=5, mat_idx=TREE_MAT_IDX["trunk"])
        # Secondary twig fork for richer winter silhouette
        tw_ang = ang + rng.choice([-0.55, 0.55])
        tw_end = (lobe_c[0] + 0.055 * scale * math.cos(tw_ang), lobe_c[1] + 0.055 * scale * math.sin(tw_ang), lz + 0.055 * scale)
        _add_branch_tube(bm, uv_layer, vert_meta, [mid_pt, tw_end],
                         [0.008 * scale, 0.004 * scale], segments=4, mat_idx=TREE_MAT_IDX["trunk"])

    # Central upward leader
    _add_branch_tube(bm, uv_layer, vert_meta, [fork_pt, (fork_pt[0], fork_pt[1], tz + 0.36 * scale)],
                     [0.014 * scale, 0.006 * scale], segments=5, mat_idx=TREE_MAT_IDX["trunk"])

    crown_c = (fork_pt[0], fork_pt[1], tz + 0.31 * scale)
    z0_c, z1_c = tz + 0.18 * scale, tz + 0.48 * scale

    for li, (lx, ly, lz, lrad) in enumerate(lobes):
        n_tufts = 9 if li == 0 else 7
        for ti in range(n_tufts):
            theta = rng.uniform(0.0, 2.0 * math.pi)
            cos_p = rng.uniform(-0.75, 0.92)
            sin_p = math.sqrt(max(0.0, 1.0 - cos_p * cos_p))
            rr = rng.uniform(0.28, 0.96) * lrad
            pt = (lx + rr * sin_p * math.cos(theta), ly + rr * sin_p * math.sin(theta), lz + rr * cos_p * 0.85)
            c_sz = rng.uniform(0.115, 0.165) * scale
            _add_tuft(bm, uv_layer, vert_meta, pt, (lx, ly, lz), crown_c, z0_c, z1_c,
                      c_sz, c_sz, mat_leaf, rng, flat_mode=False, z_bias=0.30)


def _build_cedar_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng):
    mat_leaf = TREE_MAT_IDX["cedar_foliage"]
    _add_branch_tube(
        bm, uv_layer, vert_meta,
        [(tx, ty, tz), (tx, ty, tz + 0.14 * scale), (tx, ty, tz + 0.32 * scale), (tx, ty, tz + 0.50 * scale)],
        [0.032 * scale, 0.022 * scale, 0.015 * scale, 0.006 * scale],
        segments=6, mat_idx=TREE_MAT_IDX["trunk"],
    )

    crown_c = (tx, ty, tz + 0.33 * scale)
    z0_c, z1_c = tz + 0.12 * scale, tz + 0.56 * scale
    tiers = [
        (0.15, 0.115, 8),
        (0.22, 0.105, 8),
        (0.29, 0.092, 7),
        (0.36, 0.075, 6),
        (0.43, 0.055, 5),
        (0.50, 0.028, 4),
    ]
    for zt, rad_t, n_t in tiers:
        wz = tz + zt * scale
        a0 = rng.uniform(0.0, 2.0 * math.pi)
        for ti in range(n_t):
            ang = a0 + 2.0 * math.pi * ti / n_t + rng.uniform(-0.22, 0.22)
            rr = rng.uniform(0.45, 0.96) * rad_t * scale
            pt = (tx + rr * math.cos(ang), ty + rr * math.sin(ang), wz + rng.uniform(-0.015, 0.015) * scale)
            c_sz = rng.uniform(0.095, 0.135) * scale * max(0.65, 1.0 - (zt - 0.15) * 0.75)
            _add_tuft(bm, uv_layer, vert_meta, pt, (tx, ty, wz), crown_c, z0_c, z1_c,
                      c_sz, c_sz, mat_leaf, rng, flat_mode=False, z_bias=0.35)


# ==============================================================================
# Public Tree Builder Entrypoint
# ==============================================================================
def add_tree_object(col, tx, ty, tz=0.0, kind="pine", scale=1.0, seed=1,
                    tree_mats=None, season_init=0, name=None):
    """
    Build a pak128 botanical tree object directly in world space with custom split
    normals, `Col` vertex attributes, and grounding pad.
    `kind`: "pine", "broadleaf" ("deciduous"), "cedar", or "sakura".
    """
    if tree_mats is None:
        tree_mats = create_tree_materials()

    k_norm = kind.lower()
    if k_norm == "deciduous":
        k_norm = "broadleaf"
    if k_norm not in KIND_TO_MAT_KEY:
        raise ValueError(f"Unknown tree kind: {kind!r}")

    rng = random.Random(seed)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    vert_meta = []  # parallel list: (tag, Vector normal, (ao, var, znorm, 1.0))

    if k_norm == "pine":
        _build_pine_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng)
        pad_r = 0.185 * scale
    elif k_norm == "cedar":
        _build_cedar_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng)
        pad_r = 0.145 * scale
    elif k_norm == "sakura":
        _build_deciduous_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng, TREE_MAT_IDX["sakura_foliage"])
        pad_r = 0.175 * scale
    else:
        _build_deciduous_geometry(bm, uv_layer, vert_meta, tx, ty, tz, scale, rng, TREE_MAT_IDX["broadleaf_foliage"])
        pad_r = 0.175 * scale

    _add_ground_shadow_pad(bm, uv_layer, vert_meta, tx, ty, tz, r_in=0.02 * scale, r_out=pad_r,
                           mat_idx=TREE_MAT_IDX["shadow_pad"], segs=16)

    bm.normal_update()
    bm.verts.ensure_lookup_table()
    # Extract geometric smooth normals for trunk & pad, and blended volume normals for foliage
    vert_normals = []
    flat_cols = []
    for i, v in enumerate(bm.verts):
        tag, custom_n, col_rgba = vert_meta[i]
        if tag == "foliage":
            vert_normals.append((custom_n.x, custom_n.y, custom_n.z))
        else:
            vn = v.normal
            if vn.length > 1e-6:
                vert_normals.append((vn.x, vn.y, vn.z))
            else:
                vert_normals.append((custom_n.x, custom_n.y, custom_n.z))
        flat_cols.extend(col_rgba)

    ob_name = name or f"Tree_{k_norm}_{seed}"
    mesh = bpy.data.meshes.new(ob_name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()

    for key in TREE_MAT_KEYS:
        mesh.materials.append(tree_mats[key][season_init])

    col_attr = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    col_attr.data.foreach_set("color", flat_cols)

    for p in mesh.polygons:
        p.use_smooth = True
    mesh.normals_split_custom_set_from_vertices(vert_normals)

    ob = bpy.data.objects.new(ob_name, mesh)
    ob["is_tree_lib"] = True
    ob["tree_kind"] = k_norm
    col.objects.link(ob)
    return ob
