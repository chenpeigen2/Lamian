"""Render deliverables and inspect the saved self-contained scene."""
import bpy
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output'
scene=bpy.context.scene
scene.render.resolution_percentage=100
scene.cycles.samples=72
scene.cycles.adaptive_threshold=.018
scene.render.filepath=str(OUT/'hero.png')
scene.camera=bpy.data.objects['01 | Hero reference angle']
bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['02 | Low porcelain study']
scene.render.resolution_x=1500;scene.render.resolution_y=1100
scene.cycles.samples=56
scene.render.filepath=str(OUT/'low_angle.png')
bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['03 | Top food detail']
scene.render.resolution_x=1400;scene.render.resolution_y=1400
scene.render.filepath=str(OUT/'top_detail.png')
bpy.ops.render.render(write_still=True)
report={
 'blender':bpy.app.version_string,
 'objects':len(scene.objects),
 'mesh_objects':sum(o.type=='MESH' for o in scene.objects),
 'curves':sum(o.type=='CURVE' for o in scene.objects),
 'materials':len(bpy.data.materials),
 'cameras':[o.name for o in scene.objects if o.type=='CAMERA'],
 'images':[{'name':im.name,'packed':bool(im.packed_file),'size':list(im.size)} for im in bpy.data.images if im.type=='IMAGE'],
 'estimated_bowl_diameter_m':.298,
 'method':scene.get('reconstruction_method'),
 'nonfinite_vertices':0,
}
import math
for o in scene.objects:
 if o.type=='MESH':
  report['nonfinite_vertices']+=sum(not all(math.isfinite(c) for c in v.co) for v in o.data.vertices)
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
# Short bounded arc rather than hiding the estimated back-side detail behind a full turn.
scene.camera=bpy.data.objects['04 | Orbit animation']
scene.render.resolution_x=800;scene.render.resolution_y=640
scene.cycles.samples=20;scene.cycles.adaptive_threshold=.075
for i in range(36):
 scene.frame_set(1+i)
 import math
 from mathutils import Vector
 a=-math.pi/2+i/35*math.radians(75)
 scene.camera.location=(.49*math.cos(a),.49*math.sin(a),.32)
 scene.camera.rotation_euler=(Vector((0,0,.075))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(OUT/'orbit_frames'/f'{i:03d}.png')
 bpy.ops.render.render(write_still=True)
print('DELIVERABLES_RENDERED',json.dumps(report))
