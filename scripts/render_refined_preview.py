import bpy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output'/'refined'; OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
final='--final' in args
for name,cam,res,samples in [('hero','01 | Hero reference angle',(1800,1500),128),('close_detail','05 | Close detail',(1600,1200),128),('low_angle','02 | Low porcelain study',(1500,1100),96),('top_detail','03 | Top food detail',(1400,1400),96)]:
    if not final and name not in ('hero','close_detail'):continue
    scene.camera=bpy.data.objects[cam]
    scene.render.resolution_x,scene.render.resolution_y=res
    scene.render.resolution_percentage=100 if final else 45
    scene.cycles.samples=samples if final else 24
    scene.cycles.adaptive_threshold=.015 if final else .07
    scene.render.filepath=str(OUT/(name+('.png' if final else '_preview.png')))
    bpy.ops.render.render(write_still=True)
print('REFINED_RENDER_DONE')
