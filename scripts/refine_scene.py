"""Create a refined reconstruction pass from the saved base scene.

Run after build_scene.py:
blender --background output/Lamian_Reconstruction.blend --python scripts/refine_scene.py
"""
import bpy
import bmesh
import math
import random
from pathlib import Path
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output'
REFINED = OUT / 'Lamian_Reconstruction_Refined.blend'
random.seed(1127)
PI = math.pi
SOUP_Z = .099
scene = bpy.context.scene


def col(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
    return collection


def mat(name, color, rough=.4, subsurface=0, coat=0, transmission=0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Subsurface Weight'].default_value = subsurface
    p.inputs['Subsurface Scale'].default_value = .002
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Transmission Weight'].default_value = transmission
    p.inputs['IOR'].default_value = ior
    return m, p


def add_noise_bump(m, p, scale, distance, strength=.35, detail=5, mapping='Object'):
    nodes, links = m.node_tree.nodes, m.node_tree.links
    coords = nodes.new('ShaderNodeTexCoord')
    tex = nodes.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = scale
    tex.inputs['Detail'].default_value = detail
    tex.inputs['Roughness'].default_value = .62
    links.new(coords.outputs[mapping], tex.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = strength
    bump.inputs['Distance'].default_value = distance
    links.new(tex.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], p.inputs['Normal'])


def mesh_object(name, verts, faces, material, collection, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.validate(clean_customdata=False)
    data.update()
    obj = bpy.data.objects.new(name, data)
    col(collection).objects.link(obj)
    data.materials.append(material)
    for poly in data.polygons:
        poly.use_smooth = smooth
    return obj


def remove_object(obj):
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data and data.users == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Curve):
            bpy.data.curves.remove(data)


def sphere(name, loc, scale, material, collection, segs=18, rings=10, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col(collection).objects.link(obj)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def tube(name, points, radius, material, collection, resolution=3):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 10
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (*co, 1)
    obj = bpy.data.objects.new(name, curve)
    col(collection).objects.link(obj)
    curve.materials.append(material)
    return obj


# 1. Restore natural silhouettes to the photo-derived ingredients.
for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and '| solid reference-matched mesh' in obj.name:
        obj.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value = .025
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        seed = sum(ord(c) for c in obj.name) * .013
        is_beef = obj.name.startswith('Beef')
        is_ear = obj.name.startswith('Wood_ear')
        top = [v for v in bm.verts if v.co.z > SOUP_Z + .0002]
        if top:
            center = sum((v.co for v in top), Vector()) / len(top)
            maxr = max(((v.co.xy - center.xy).length for v in top), default=.01)
        for v in bm.verts:
            co = v.co
            r = ((co.xy - center.xy).length / maxr) if top else 0
            fiber = math.sin((co.x * .62 + co.y) * (530 if is_beef else 330) + seed) * (.00008 if is_beef else .00006)
            large = noise.noise(Vector((co.x * 70 + seed, co.y * 70, 1.7))) * (.0007 if is_beef else .00045)
            small = noise.noise(Vector((co.x * 290, co.y * 290 + seed, .4))) * (.00015 if is_beef else .0001)
            curl = (r ** 2.4) * (.0011 if is_ear else .00055)
            if co.z > SOUP_Z + .0002:
                co.z += large + small + fiber + curl
            # Lower edges naturally sink into broth, not vertical cookie-cutter walls.
            elif r > .8:
                co.z -= .0012 + abs(large) * .7
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # Keep every ingredient inside the glazed inner wall (inner radius ~0.1356 m at broth level).
        limit = .1285
        for v in bm.verts:
            r = math.hypot(v.co.x, v.co.y)
            if r > limit:
                v.co.x *= limit / r
                v.co.y *= limit / r
        bm.to_mesh(obj.data)
        bm.free()
        for modifier in list(obj.modifiers):
            obj.modifiers.remove(modifier)
        bevel = obj.modifiers.new('Soft cooked edge', 'BEVEL')
        bevel.width = .0011 if is_beef else .00075
        bevel.segments = 3
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = math.radians(36)
        sub = obj.modifiers.new('Organic subdivision', 'SUBSURF')
        sub.levels = 1
        sub.render_levels = 2
        obj.modifiers.new('Natural shading', 'WEIGHTED_NORMAL')
        obj['refinement'] = 'surface relief, soft edges and broth contact'

# Beef: roll off the photographed glare and warm the cooked colour in the packed textures.
import numpy as np
for img in bpy.data.images:
    if not img.name.startswith('Beef_') or img.size[0] == 0:
        continue
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    rgb = px[:, :3]
    alpha = px[:, 3] > .5
    lum = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
    lo, hi = (np.percentile(lum[alpha], [3, 97]) if alpha.any() else (.2, .8))
    t = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1) ** 1.15
    # Map the photo's light/dark pattern onto a braised-beef ramp (sRGB pixel values).
    dark = np.array([.20, .095, .055], dtype=np.float32)
    mid = np.array([.36, .19, .11], dtype=np.float32)
    light = np.array([.55, .35, .23], dtype=np.float32)
    ramp_rgb = np.where(t[:, None] < .55,
                        dark + (mid - dark) * (t[:, None] / .55),
                        mid + (light - mid) * ((t[:, None] - .55) / .45))
    rgb = ramp_rgb * .85 + rgb * .15
    px[:, :3] = np.clip(rgb, 0, 1)
    img.pixels.foreach_set(px.ravel())
    img.update()
    img.pack()

# Muscle grain as a shading-only relief, chained after the existing photo bump.
for m in bpy.data.materials:
    if not m.name.startswith('Beef_') or not m.use_nodes:
        continue
    nodes, links = m.node_tree.nodes, m.node_tree.links
    p = nodes['Principled BSDF']
    # Wet with broth: a thin glossy coat over a matte cooked surface.
    p.inputs['Roughness'].default_value = .62
    p.inputs['Subsurface Weight'].default_value = .035
    p.inputs['Coat Weight'].default_value = 0
    p.inputs['Specular IOR Level'].default_value = .28
    for node in nodes:
        if node.type == 'BUMP' and node.inputs['Strength'].default_value > .2:
            node.inputs['Strength'].default_value = .06
    previous = p.inputs['Normal'].links[0].from_socket if p.inputs['Normal'].links else None
    coords = nodes.new('ShaderNodeTexCoord')
    wave = nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'DIAGONAL'
    wave.inputs['Scale'].default_value = 130
    wave.inputs['Distortion'].default_value = 9
    wave.inputs['Detail'].default_value = 4
    links.new(coords.outputs['Object'], wave.inputs['Vector'])
    grain = nodes.new('ShaderNodeBump')
    grain.inputs['Strength'].default_value = .025
    grain.inputs['Distance'].default_value = .00018
    links.new(wave.outputs['Fac'], grain.inputs['Height'])
    if previous:
        links.new(previous, grain.inputs['Normal'])
    links.new(grain.outputs['Normal'], p.inputs['Normal'])

# 2. Replace flat pasta tubes with fuller cooked, slightly flattened noodle bundles.
for obj in list(bpy.data.objects):
    if obj.name.startswith('Submerged noodle strand') or obj.name.startswith('Visible wheat loop'):
        remove_object(obj)
noodle, noodle_p = mat('Hand pulled noodles | refined cooked wheat', (.78, .58, .25), .30, .32, .08)
add_noise_bump(noodle, noodle_p, 230, .00008, .18, 3)
# Inner glaze radius by height (from the bowl profile), so every strand stays inside.
INNER = [(.043, .098), (.059, .112), (.078, .124), (.098, .135), (.110, .142)]


def inner_radius(z):
    if z <= INNER[0][0]:
        return INNER[0][1]
    for (z0, r0), (z1, r1) in zip(INNER, INNER[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return INNER[-1][1]


for n in range(105):
    a = random.uniform(0, 2 * PI)
    base_r = random.uniform(.012, .113)
    turns = random.uniform(.75, 1.6)
    pts = []
    for j in range(64):
        t = j / 63
        angle = a + t * turns * 2 * PI
        r = base_r + .016 * math.sin(t * 3 * PI + n) + .009 * math.sin(t * 11 + n * .7)
        x = r * math.cos(angle)
        y = r * math.sin(angle) * .86
        z = .0875 + .006 * t + .0018 * math.sin(t * 13 + n) + random.uniform(-.0002, .0002)
        if n % 9 == 0:
            z += .0057 * math.sin(t * PI)
        z = min(z, SOUP_Z + .00055)
        if math.hypot(x, y) > inner_radius(z) - .006:
            continue
        pts.append((x, y, z))
    if len(pts) > 8:
        tube(f'Hand pulled noodle {n:03d}', pts, random.uniform(.00065, .00105), noodle, '05_Noodles', 3)

# Small herb pieces and chili flakes break up the large photo-textured surface.
herb, herb_p = mat('Garnish | fresh cilantro', (.035, .13, .018), .42, .12)
chili, chili_p = mat('Garnish | toasted chili flake', (.30, .02, .005), .33, .04, .16)
for i in range(64):
    r = math.sqrt(random.random()) * .122
    a = random.uniform(0, 2 * PI)
    x, y = r * math.cos(a), r * math.sin(a)
    if i < 24:
        sphere(f'Fresh herb fleck {i:03d}', (x, y, SOUP_Z + .0005), (random.uniform(.0012, .0026), random.uniform(.0006, .0014), .0001), herb, '04_Vegetables', 10, 4, (0, 0, random.uniform(0, PI)))
    else:
        sphere(f'Chili flake {i:03d}', (x, y, SOUP_Z + .00052), (random.uniform(.0005, .0012), random.uniform(.00035, .0008), .00008), chili, '02_Broth', 8, 4, (0, 0, random.uniform(0, PI)))

# Spoon: sink the scoop under the broth so the handle rises out of the soup.
for obj in bpy.data.objects:
    if obj.name.startswith('Spoon | concave'):
        obj.location.z -= .0075
    elif obj.name.startswith('Spoon | wide flattened'):
        obj.location.z -= .0055

# Rising steam: a wispy volume, densest just above the broth and fading upward.
steam_mat = bpy.data.materials.new('Steam | rising wisps')
steam_mat.use_nodes = True
nt = steam_mat.node_tree
for node in list(nt.nodes):
    if node.type != 'OUTPUT_MATERIAL':
        nt.nodes.remove(node)
out = nt.nodes['Material Output']
vol = nt.nodes.new('ShaderNodeVolumePrincipled')
vol.inputs['Color'].default_value = (1, 1, 1, 1)
vol.inputs['Anisotropy'].default_value = .35
coords = nt.nodes.new('ShaderNodeTexCoord')
stretch = nt.nodes.new('ShaderNodeVectorMath')
stretch.operation = 'MULTIPLY'
stretch.inputs[1].default_value = (1, 1, .38)
nt.links.new(coords.outputs['Object'], stretch.inputs[0])
wisp = nt.nodes.new('ShaderNodeTexNoise')
wisp.inputs['Scale'].default_value = 16
wisp.inputs['Detail'].default_value = 6
wisp.inputs['Distortion'].default_value = 1.4
nt.links.new(stretch.outputs[0], wisp.inputs['Vector'])
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = .53
ramp.color_ramp.elements[1].position = .76
nt.links.new(wisp.outputs['Fac'], ramp.inputs[0])
xyz = nt.nodes.new('ShaderNodeSeparateXYZ')
nt.links.new(coords.outputs['Object'], xyz.inputs[0])
# Object space spans z -1..1 (unit cylinder scaled); fade = (1 - (z+1)/2)^1.6
rise = nt.nodes.new('ShaderNodeMapRange')
rise.inputs['From Min'].default_value = -1
rise.inputs['From Max'].default_value = 1
rise.inputs['To Min'].default_value = 1
rise.inputs['To Max'].default_value = 0
nt.links.new(xyz.outputs['Z'], rise.inputs['Value'])
fade = nt.nodes.new('ShaderNodeMath')
fade.operation = 'POWER'
fade.inputs[1].default_value = 1.6
nt.links.new(rise.outputs['Result'], fade.inputs[0])
radial_len = nt.nodes.new('ShaderNodeVectorMath')
radial_len.operation = 'LENGTH'
flat = nt.nodes.new('ShaderNodeCombineXYZ')
nt.links.new(xyz.outputs['X'], flat.inputs['X'])
nt.links.new(xyz.outputs['Y'], flat.inputs['Y'])
nt.links.new(flat.outputs[0], radial_len.inputs[0])
radial = nt.nodes.new('ShaderNodeMapRange')
radial.inputs['From Min'].default_value = .45
radial.inputs['From Max'].default_value = 1
radial.inputs['To Min'].default_value = 1
radial.inputs['To Max'].default_value = 0
nt.links.new(radial_len.outputs['Value'], radial.inputs['Value'])
m1 = nt.nodes.new('ShaderNodeMath')
m1.operation = 'MULTIPLY'
nt.links.new(ramp.outputs['Color'], m1.inputs[0])
nt.links.new(fade.outputs[0], m1.inputs[1])
m2 = nt.nodes.new('ShaderNodeMath')
m2.operation = 'MULTIPLY'
nt.links.new(m1.outputs[0], m2.inputs[0])
nt.links.new(radial.outputs['Result'], m2.inputs[1])
density = nt.nodes.new('ShaderNodeMath')
density.operation = 'MULTIPLY'
density.inputs[1].default_value = 6
nt.links.new(m2.outputs[0], density.inputs[0])
nt.links.new(density.outputs[0], vol.inputs['Density'])
nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=2, location=(0, 0, SOUP_Z + .145))
steam = bpy.context.object
steam.name = 'Steam | rising wisps volume'
steam.scale = (.115, .115, .115)
for c in list(steam.users_collection):
    c.objects.unlink(steam)
col('02_Broth').objects.link(steam)
steam.data.materials.append(steam_mat)
steam.visible_shadow = False
# Without this the glass table mirrors the steam as a pale disc beside the bowl.
steam.visible_glossy = False
steam.visible_transmission = False

# 3. Rebuild flatbread as layered, irregular baked pieces.
for obj in list(bpy.data.objects):
    if obj.name.startswith('Flatbread strip'):
        remove_object(obj)
crust, crust_p = mat('Flatbread | blistered golden crust', (.74, .42, .13), .62, .1)
add_noise_bump(crust, crust_p, 95, .0011, .65, 6)
crumb, crumb_p = mat('Flatbread | open layered crumb', (.86, .68, .38), .76, .06)
add_noise_bump(crumb, crumb_p, 155, .0009, .5, 5)
for k in range(9):
    cx = -.163 + k * .023 + random.uniform(-.004, .004)
    cy = .238 + random.uniform(-.018, .018)
    length = random.uniform(.105, .148)
    width = random.uniform(.026, .039)
    verts, faces = [], []
    nx, ny = 14, 38
    for j in range(ny + 1):
        for i in range(nx + 1):
            u = i / nx - .5
            v = j / ny - .5
            edge = .0035 * noise.noise(Vector((j * .27, k * 1.7, 2)))
            x = cx + u * (width + edge)
            y = cy + v * length
            z = .023 + .002 * (1 - abs(u * 2) ** 2) + .0015 * math.sin(j * .55 + k) + v * .025 + .0007 * noise.noise(Vector((i * .8, j * .45, k)))
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nx):
            q = j * (nx + 1) + i
            faces.append((q, q + 1, q + nx + 2, q + nx + 1))
    obj = mesh_object(f'Flatbread layered piece {k:02d}', verts, faces, crust, '07_Bread')
    obj.data.materials.append(crumb)
    solid = obj.modifiers.new('Two-layer bread body', 'SOLIDIFY')
    solid.thickness = .0049
    solid.offset = -1
    solid.material_offset = 1
    bevel = obj.modifiers.new('Rounded baked edge', 'BEVEL')
    bevel.width = .0011
    bevel.segments = 3
    sub = obj.modifiers.new('Organic bread form', 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 2

# 4. Crisper food styling lights, preserving existing camera setup.
# 4b. Porcelain detail: hand-painted cobalt density, iron specks, glaze sheen, bisque foot.
def box_blur(a, r):
    """Separable box blur on HxWxC float array using cumulative sums."""
    out = a
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(out, pad, mode='edge'), axis=axis)
        n = out.shape[axis]
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
        lo = np.take(c, np.arange(0, n), axis=axis)
        out = (hi - lo) / (2 * r + 1)
    return out


def low_noise(h, w, gy, gx, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((gy, gx)).astype(np.float32)
    big = np.kron(g, np.ones((h // gy + 1, w // gx + 1), dtype=np.float32))[:h, :w]
    return box_blur(big[:, :, None], max(2, min(h // gy, w // gx) // 2))[:, :, 0]


for name, seed in (('porcelain_outer.png', 3), ('porcelain_inner.png', 7)):
    img = bpy.data.images.get(name)
    if not img or img.size[0] == 0:
        continue
    w, h = img.size
    px = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[:, :, :3]
    blue = np.clip((rgb[:, :, 2] - rgb[:, :, 0] - .08) * 4, 0, 1)
    # Ink bleeds a little into the glaze.
    soft = box_blur(rgb, 2)
    rgb = rgb * (1 - .45 * blue[:, :, None]) + soft * (.45 * blue[:, :, None])
    # Brush loading varies: some strokes pool dark, others thin out.
    n = low_noise(h, w, 18, 72, seed)
    stroke = .72 + .55 * n
    cobalt = np.array([.06, .15, .46], dtype=np.float32)
    rgb = rgb * (1 - blue[:, :, None] * .6) + (cobalt * stroke[:, :, None]) * (blue[:, :, None] * .6)
    # Warm ivory body with soft cloudiness, not flat white.
    cloud = .985 + .03 * low_noise(h, w, 10, 40, seed + 1)
    ivory = np.array([1.0, .982, .935], dtype=np.float32)
    rgb = rgb * (1 - blue[:, :, None]) * ivory * cloud[:, :, None] + rgb * blue[:, :, None]
    # Tiny iron specks in the body clay.
    rng = np.random.default_rng(seed + 11)
    for _ in range(int(w * h / 5200)):
        y, x = rng.integers(1, h - 2), rng.integers(1, w - 2)
        if blue[y, x] < .2:
            s = rng.integers(1, 3)
            rgb[y:y + s, x:x + s] *= np.array([.45, .40, .36], dtype=np.float32)
    px[:, :, :3] = np.clip(rgb, 0, 1)
    img.pixels.foreach_set(px.ravel())
    img.update()
    img.pack()


def glaze(material, base_rough=.16, coat=.55):
    if not material or not material.use_nodes:
        return
    nodes, links = material.node_tree.nodes, material.node_tree.links
    p = nodes['Principled BSDF']
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = .035
    p.inputs['Coat IOR'].default_value = 1.52
    coords = nodes.new('ShaderNodeTexCoord')
    # Roughness drifts across the glaze (thin spots, wiped areas).
    rn = nodes.new('ShaderNodeTexNoise')
    rn.inputs['Scale'].default_value = 7
    rn.inputs['Detail'].default_value = 3
    links.new(coords.outputs['Object'], rn.inputs['Vector'])
    rmap = nodes.new('ShaderNodeMapRange')
    rmap.inputs['To Min'].default_value = base_rough * .6
    rmap.inputs['To Max'].default_value = base_rough * 1.5
    links.new(rn.outputs['Fac'], rmap.inputs['Value'])
    links.new(rmap.outputs['Result'], p.inputs['Roughness'])
    # Gentle orange-peel waviness of a real kiln-fired glaze.
    wn = nodes.new('ShaderNodeTexNoise')
    wn.inputs['Scale'].default_value = 34
    wn.inputs['Detail'].default_value = 2
    links.new(coords.outputs['Object'], wn.inputs['Vector'])
    wave = nodes.new('ShaderNodeBump')
    wave.inputs['Strength'].default_value = .06
    wave.inputs['Distance'].default_value = .0003
    links.new(wn.outputs['Fac'], wave.inputs['Height'])
    if p.inputs['Normal'].links:
        links.new(p.inputs['Normal'].links[0].from_socket, wave.inputs['Normal'])
    links.new(wave.outputs['Normal'], p.inputs['Normal'])
    links.new(wave.outputs['Normal'], p.inputs['Coat Normal'])


for mname in ('Porcelain | photographed cobalt blossoms', 'Porcelain | inner floral border',
              'Warm ivory porcelain', 'Cobalt oxide pooled rim'):
    glaze(bpy.data.materials.get(mname))
for mname in ('Inner cobalt flowers | clear decal', 'Original bowl lettering | photo decal'):
    m = bpy.data.materials.get(mname)
    if m:
        m.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value = .5
        m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .12

# Unglazed foot ring: real bowls show raw, slightly warm clay where they sat in the kiln.
bisque, bisque_p = mat('Porcelain | unglazed foot ring bisque', (.64, .55, .44), .86)
add_noise_bump(bisque, bisque_p, 420, .00012, .45, 4)
bowl = bpy.data.objects.get('Bowl | continuous ceramic wall and foot')
if bowl:
    bowl.data.materials.append(bisque)
    idx = len(bowl.data.materials) - 1
    for poly in bowl.data.polygons:
        c = poly.center
        r = math.hypot(c.x, c.y)
        if poly.material_index == 0 and c.z < .0068 and .044 < r < .066:
            poly.material_index = idx

# Table glass: faint smudges and wipe marks break up the perfect mirror.
glass = bpy.data.materials.get('Table glass | faint green polished sheet')
if glass:
    nodes, links = glass.node_tree.nodes, glass.node_tree.links
    gp = nodes['Principled BSDF']
    coords = nodes.new('ShaderNodeTexCoord')
    sm = nodes.new('ShaderNodeTexNoise')
    sm.inputs['Scale'].default_value = 5.5
    sm.inputs['Detail'].default_value = 6
    links.new(coords.outputs['Object'], sm.inputs['Vector'])
    smap = nodes.new('ShaderNodeMapRange')
    smap.inputs['From Min'].default_value = .45
    smap.inputs['From Max'].default_value = .75
    smap.inputs['To Min'].default_value = .015
    smap.inputs['To Max'].default_value = .16
    links.new(sm.outputs['Fac'], smap.inputs['Value'])
    links.new(smap.outputs['Result'], gp.inputs['Roughness'])

# Rosewood: tighter grain and pores.
wood = bpy.data.materials.get('Rosewood | directional grain')
if wood:
    for node in wood.node_tree.nodes:
        if node.type == 'TEX_NOISE':
            node.inputs['Detail'].default_value = 8
            node.inputs['Scale'].default_value = 6.5

# 5. Evening warmth: shift every existing light toward a soft tungsten tone.
# The glass sheet only adds a white hotspot on the table; hide it for crisp stills.
glass_sheet = bpy.data.objects.get('Table | solid glass sheet')
if glass_sheet:
    glass_sheet.hide_render = True
for light in bpy.data.objects:
    if light.type == 'LIGHT':
        light.data.energy *= 1.3
        c = light.data.color
        light.data.color = (min(1, c[0] * 1.0), c[1] * .92, c[2] * .8)
world = scene.world
if world and world.use_nodes and 'Background' in world.node_tree.nodes:
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (.80, .74, .66, 1)
    bg.inputs['Strength'].default_value = .6

# Broth: deep chili red with tight, glossy highlights instead of a milky sheen.
broth = bpy.data.materials.get('Red broth | inpainted reference color')
if broth:
    bp = broth.node_tree.nodes['Principled BSDF']
    bp.inputs['Roughness'].default_value = .035
    bp.inputs['Coat Weight'].default_value = 0
    bp.inputs['Transmission Weight'].default_value = 0
    bp.inputs['Subsurface Weight'].default_value = 0
    bp.inputs['Specular IOR Level'].default_value = .3
    for node in broth.node_tree.nodes:
        if node.type == 'VALTORGB':
            node.color_ramp.elements[0].color = (.035, .004, .0002, 1)
            node.color_ramp.elements[1].color = (.22, .030, .0008, 1)
        if node.type == 'MIX_RGB':
            node.inputs[0].default_value = .12
body = bpy.data.materials.get('Broth volume body')
if body:
    body.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.16, .025, .002, 1)

# Remove the amber outline tubes: they read as glowing cartoon outlines around every ingredient.
for obj in list(bpy.data.objects):
    if '| thin wet contact edge' in obj.name:
        remove_object(obj)
veg_edge = bpy.data.materials.get('Vegetable | wet cut edge')
if veg_edge:
    vp = veg_edge.node_tree.nodes['Principled BSDF']
    vp.inputs['Base Color'].default_value = (.17, .19, .05, 1)
    vp.inputs['Subsurface Weight'].default_value = .04

# Chili oil pools: flat amber lenses floating on the broth, catching the light.
oil = bpy.data.materials.get('Chili oil | clear amber thin film')
if oil:
    op = oil.node_tree.nodes['Principled BSDF']
    op.inputs['Base Color'].default_value = (.62, .13, .004, 1)
    op.inputs['Roughness'].default_value = .025
    op.inputs['Transmission Weight'].default_value = .45
    op.inputs['Specular IOR Level'].default_value = .6
    for i in range(48):
        r = math.sqrt(random.random()) * .118
        a = random.uniform(0, 2 * PI)
        size = random.uniform(.002, .0068)
        sphere(f'Chili oil pool {i:03d}', (r * math.cos(a), r * math.sin(a), SOUP_Z + .00012),
               (size, size * random.uniform(.65, 1.0), .00007), oil, '02_Broth', 24, 6,
               (0, 0, random.uniform(0, PI)))
# Dark warm backlight behind the bowl makes the steam readable.
rim = bpy.data.lights.new('Refined | warm steam backlight', 'AREA')
rim.shape = 'DISK'
rim.size = .35
rim.energy = 6
rim.color = (1, .78, .55)
rim_obj = bpy.data.objects.new('Refined | warm steam backlight', rim)
col('11_Lighting').objects.link(rim_obj)
rim_obj.location = (-.05, .55, .33)
rim_obj.rotation_euler = (Vector((0, 0, .16)) - rim_obj.location).to_track_quat('-Z', 'Y').to_euler()
key = bpy.data.lights.new('Refined | narrow overhead broth highlight', 'AREA')
key.shape = 'RECTANGLE'
key.size = .42
key.size_y = .07
key.energy = 3.2
key.color = (1, .91, .79)
key_obj = bpy.data.objects.new('Refined | narrow overhead broth highlight', key)
col('11_Lighting').objects.link(key_obj)
key_obj.location = (.05, -.05, .55)
key_obj.rotation_euler = (math.radians(4), 0, math.radians(34))

# Close-up camera: rim, glaze and food detail.
cd = bpy.data.cameras.new('05 | Close detail')
cd.lens = 70
cd.clip_start = .003
cd.dof.use_dof = True
cd.dof.aperture_fstop = 4.5
cam = bpy.data.objects.new('05 | Close detail', cd)
col('12_Cameras').objects.link(cam)
cam.location = (.13, -.30, .25)
focus = Vector((.03, -.02, .095))
cam.rotation_euler = (focus - cam.location).to_track_quat('-Z', 'Y').to_euler()
cd.dof.focus_distance = (focus - cam.location).length

scene.cycles.volume_step_rate = 2
scene.cycles.samples = 128
scene.cycles.adaptive_threshold = .015
scene.view_settings.look = 'AgX - Punchy'
scene.view_settings.exposure = .45
# The large fills read as milky reflections on the broth; keep their light but hide them from glossy rays.
for name in ('Large window | soft key', 'Ceiling | warm long reflection', 'Right fill | room bounce',
             'Rear separator', 'Refined | warm steam backlight'):
    light = bpy.data.objects.get(name)
    if light:
        light.visible_glossy = False
scene['refined_version'] = 'v0.2 detailed food, noodles, bread and lighting'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(REFINED))
print('REFINED_SCENE_READY', REFINED)
