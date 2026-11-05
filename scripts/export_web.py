"""Export a compact web asset without modifying the original blend."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'public'/'media'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
keep=[]
for c in bpy.data.collections:
    if c.name[:2] in ['01','02','03','04','05','06','07','08','09']:
        for o in c.objects:
            if o.type in ['MESH','CURVE'] and not o.name.startswith(('Steam','Fine tabletop wear','Table | solid glass')):
                keep.append(o)
                for mod in o.modifiers:
                    if mod.type=='SUBSURF':mod.levels=1;mod.render_levels=1
for o in keep:o.select_set(True)
bpy.context.view_layer.objects.active=keep[0]
bpy.ops.object.convert(target='MESH')
# Simplify shader graphs to glTF-compatible PBR while retaining all photo UV maps.
for m in bpy.data.materials:
    if not m.use_nodes:continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if not p:continue
    image_nodes=[n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    for socket in ['Normal','Coat Normal']:
        if socket in p.inputs:
            for link in list(p.inputs[socket].links):m.node_tree.links.remove(link)
    if image_nodes:
        t=image_nodes[0]
        for link in list(p.inputs['Base Color'].links):m.node_tree.links.remove(link)
        m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
    elif p.inputs['Base Color'].links:
        # Procedural shader graphs cannot be exported; bake key colors for the web model.
        for link in list(p.inputs['Base Color'].links):m.node_tree.links.remove(link)
        baked={'Rosewood':(.048,.013,.006),'Warm ivory':(.79,.82,.77),'Cobalt oxide':(.012,.052,.19),
               'Hand pulled':(.78,.58,.25),'Flatbread | blistered':(.74,.42,.13),'Flatbread | open':(.86,.68,.38),
               'Garnish | fresh':(.035,.13,.018),'Garnish | toasted':(.30,.02,.005),'Beef | dark':(.18,.075,.035),
               'Beef | translucent':(.78,.55,.34),'unglazed foot':(.64,.55,.44),'Red broth':(.30,.045,.001),
               'Broth volume':(.16,.025,.002)}
        for key,color in baked.items():
            if key in m.name:p.inputs['Base Color'].default_value=(*color,1);break
    if p.inputs['Roughness'].links:
        # Baked roughness for procedural maps (glass was exporting as roughness 1).
        for link in list(p.inputs['Roughness'].links):m.node_tree.links.remove(link)
        rough={'Table glass':.05,'Porcelain':.16,'Red broth':.05,'Chili oil':.03,'Spoon':.14}
        for key,r in rough.items():
            if key in m.name:p.inputs['Roughness'].default_value=r;break
    if 'clear polypropylene' in m.name:
        p.inputs['Base Color'].default_value=(.75,.85,.82,1)
        p.inputs['Alpha'].default_value=.22;m.surface_render_method='DITHERED'
    if 'amber transmission' in m.name:p.inputs['Base Color'].default_value=(.39,.12,.006,1)
# Porcelain, utensils and food must be opaque: some exporter path was emitting alpha .22.
transparent=('clear polypropylene','amber transmission','faint green polished','clear amber thin film',
             'Fine stock bubbles','Chili oil lens','clear decal','photo decal')
for m in bpy.data.materials:
    if not m.use_nodes:continue
    if any(k in m.name for k in transparent):continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if p and not p.inputs['Alpha'].links:
        p.inputs['Alpha'].default_value=1.0
# Cap image resolution for mobile texture memory.
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>0:
        ratio=min(1,2048/max(im.size))
        if ratio<1:im.scale(round(im.size[0]*ratio),round(im.size[1]*ratio))
bpy.ops.export_scene.gltf(filepath=str(OUT/'lamian.glb'),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_apply=True,export_image_format='AUTO',export_extras=False)
print('WEB_MODEL_READY',OUT/'lamian.glb')
