"""Build the editable reference-derived noodle scene in Blender 5.2.
Run: blender --background --python scripts/build_scene.py -- --render preview
"""
import bpy
import math
import random
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT=Path(__file__).resolve().parent.parent
ASSETS=ROOT/'assets'
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
random.seed(34)
PI=math.pi
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for data in list(bpy.data.materials): bpy.data.materials.remove(data)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.length_unit='CENTIMETERS'

COL={}
for name in ['01_Porcelain','02_Broth','03_Beef','04_Vegetables','05_Noodles','06_Spoon','07_Bread','08_Tea','09_Table','10_Interior','11_Lighting','12_Cameras']:
    c=bpy.data.collections.new(name); scene.collection.children.link(c); COL[name]=c

def move(obj,collection):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    COL[collection].objects.link(obj)
    return obj

def mesh(name,verts,faces,mat,collection,uvs=None):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); COL[collection].objects.link(ob)
    if mat:me.materials.append(mat)
    if uvs:
        layer=me.uv_layers.new(name='ReferenceUV')
        for p in me.polygons:
            for li in p.loop_indices:layer.data[li].uv=uvs[me.loops[li].vertex_index]
    for p in me.polygons:p.use_smooth=True
    return ob

def simple(name,color,rough=.3,metal=0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    return m,p

def image_mat(name,file,rough=.3,bump=.0001,subsurface=0):
    m,p=simple(name,(.6,.5,.4),rough)
    n=m.node_tree.nodes; l=m.node_tree.links
    t=n.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(str(ASSETS/file),check_existing=True)
    l.new(t.outputs['Color'],p.inputs['Base Color'])
    if bump:
        b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.28; b.inputs['Distance'].default_value=bump
        l.new(t.outputs['Color'],b.inputs['Height']); l.new(b.outputs['Normal'],p.inputs['Normal'])
    if subsurface:
        p.inputs['Subsurface Weight'].default_value=subsurface
        p.inputs['Subsurface Radius'].default_value=(.7,.35,.16)
        p.inputs['Subsurface Scale'].default_value=.003
    return m,p,t

def noise_bump(m,p,scale,dist,strength=.25,detail=3):
    n=m.node_tree.nodes; l=m.node_tree.links
    tx=n.new('ShaderNodeTexNoise'); tx.inputs['Scale'].default_value=scale; tx.inputs['Detail'].default_value=detail
    co=n.new('ShaderNodeTexCoord'); l.new(co.outputs['Generated'],tx.inputs['Vector'])
    bu=n.new('ShaderNodeBump'); bu.inputs['Distance'].default_value=dist; bu.inputs['Strength'].default_value=strength
    l.new(tx.outputs['Fac'],bu.inputs['Height']); l.new(bu.outputs['Normal'],p.inputs['Normal'])
    return tx

def cube(name,loc,size,mat,col,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move(o,col)
    if mat:o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Soft real edges','BEVEL'); b.width=bevel; b.segments=3
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def lathe(name,profile,mats,col,segments=192):
    verts=[]; faces=[]; uv=[]
    for j,(r,z) in enumerate(profile):
        for i in range(segments+1):
            a=2*PI*i/segments
            verts.append((r*math.cos(a),r*math.sin(a),z)); uv.append((i/segments,j/(len(profile)-1)))
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*(segments+1)+i; faces.append((a,a+1,a+segments+2,a+segments+1))
    ob=mesh(name,verts,faces,None,col,uv)
    for m in mats:ob.data.materials.append(m)
    return ob

def tube(name,points,radius,mat,col,res=3):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=12
    cu.bevel_depth=radius; cu.bevel_resolution=res
    sp=cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for p,co in zip(sp.points,points):p.co=(*co,1)
    ob=bpy.data.objects.new(name,cu); COL[col].objects.link(ob); cu.materials.append(mat)
    return ob

def sphere(name,loc,scale,mat,col,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    o=move(bpy.context.object,col); o.name=name; o.scale=scale; o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=True
    return o

# Fully revolved wall with continuous interior, rounded lip and an open foot ring.
outer,op,_=image_mat('Porcelain | photographed cobalt blossoms','porcelain_outer.png',.16,.000035)
op.inputs['Coat Weight'].default_value=.3; op.inputs['Coat Roughness'].default_value=.12
inner,ip,_=image_mat('Porcelain | inner floral border','porcelain_inner.png',.17,.000025)
ip.inputs['Coat Weight'].default_value=.3
white,wp=simple('Warm ivory porcelain',(.79,.82,.77),.14); wp.inputs['Coat Weight'].default_value=.35
cobalt,cp=simple('Cobalt oxide pooled rim',(.012,.052,.19),.18); cp.inputs['Coat Weight'].default_value=.4
profile=[(.001,.010),(.047,.010),(.051,.008),(.052,.002),(.061,.002),(.063,.006),(.064,.012),(.073,.016),(.084,.024),(.096,.037),(.108,.052),(.120,.071),(.131,.091),(.141,.109),(.146,.115),(.148,.116),(.149,.114),(.147,.111),(.142,.110),(.135,.098),(.124,.078),(.112,.059),(.098,.043),(.084,.032),(.066,.026),(.04,.023),(.001,.023)]
bowl=lathe('Bowl | continuous ceramic wall and foot',profile,[outer,inner,cobalt,white],'01_Porcelain',256)
# Custom vertical UVs preserve artwork position rather than stretching the whole profile.
layer=bowl.data.uv_layers.active
for poly in bowl.data.polygons:
    j=poly.index//256
    poly.material_index=0 if j<14 else 2 if j<18 else 1 if j<24 else 3
    for li in poly.loop_indices:
        v=bowl.data.vertices[bowl.data.loops[li].vertex_index].co
        old=layer.data[li].uv
        u=old.x
        vv=1-(v.z-.012)/.104 if j<18 else 1-(.110-v.z)/.016
        layer.data[li].uv=(u,vv)
sub=bowl.modifiers.new('Porcelain curvature','SUBSURF'); sub.levels=2; sub.render_levels=2
bowl['diameter_cm']=29.8; bowl['estimated_from_reference']=True
# Three fine glazed rings, not metal trim.
for r,z,rr in [(.148,.1145,.00105),(.1457,.116,.00065),(.138,.105,.00028)]:
    tube('Hand glazed cobalt ring',[(r*math.cos(a*2*PI/256),r*math.sin(a*2*PI/256),z) for a in range(257)],rr,cobalt,'01_Porcelain',4)

# Inner blue blossoms are a separately conformed underglaze decal band.
floral,flp,flt=image_mat('Inner cobalt flowers | clear decal','flower_decal.png',.18,0)
floral.surface_render_method='DITHERED'
floral.node_tree.links.new(flt.outputs['Alpha'],flp.inputs['Alpha'])
v=[];f=[];uv=[]
for k in range(26):
    for j in range(7):
        z=.1008+j/6*.009
        r=.135+(z-.098)*(.007/.012)-.00032
        for i in range(17):
            a=(k+i/16)*2*PI/26
            v.append((r*math.cos(a),r*math.sin(a),z));uv.append((i/16,j/6))
    base=k*7*17
    for j in range(6):
        for i in range(16):
            a=base+j*17+i;f.append((a,a+17,a+18,a+1))
mesh('Bowl | conforming inner floral underglaze',v,f,floral,'01_Porcelain',uv)

# Photo-derived decal on the bowl's far side, set in a curved conforming patch.
logo,lp,lt=image_mat('Original bowl lettering | photo decal','bowl_logo.png',.18,0)
logo.surface_render_method='DITHERED'
logo.node_tree.links.new(lt.outputs['Alpha'],lp.inputs['Alpha'])
verts=[]; uv=[]; faces=[]
for j in range(25):
    z=.025+j/24*.068
    r=.084+(z-.025)/.068*.048
    for i in range(65):
        a=.25+i/64*1.45
        verts.append(((r+.00055)*math.cos(a),(r+.00055)*math.sin(a),z)); uv.append((i/64,j/24))
for j in range(24):
    for i in range(64):
        a=j*65+i; faces.append((a,a+1,a+66,a+65))
mesh('Bowl | original China noodle lettering',verts,faces,logo,'01_Porcelain',uv)

# Liquid: slightly translucent turbid broth, independent oil and meniscus geometry.
broth,bp,bt=image_mat('Red broth | inpainted reference color','broth_color.jpg',.19,0)
bp.inputs['IOR'].default_value=1.333
bp.inputs['Roughness'].default_value=.24
bp.inputs['Transmission Weight'].default_value=.06
bp.inputs['Coat Weight'].default_value=.12
bp.inputs['Coat Roughness'].default_value=.09
n=broth.node_tree.nodes; l=broth.node_tree.links
# Separate photographed illumination from liquid albedo: use an amber color ramp.
for link in list(bp.inputs['Base Color'].links):l.remove(link)
co=n.new('ShaderNodeTexCoord')
liquid_noise=n.new('ShaderNodeTexNoise');liquid_noise.inputs['Scale'].default_value=4.5;liquid_noise.inputs['Detail'].default_value=2.5
l.new(co.outputs['Generated'],liquid_noise.inputs['Vector'])
liquid_ramp=n.new('ShaderNodeValToRGB')
liquid_ramp.color_ramp.elements[0].position=.22;liquid_ramp.color_ramp.elements[0].color=(.16,.025,.001,1)
liquid_ramp.color_ramp.elements[1].position=.80;liquid_ramp.color_ramp.elements[1].color=(.66,.20,.003,1)
l.new(liquid_noise.outputs['Fac'],liquid_ramp.inputs[0])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[0].default_value=.20
l.new(bt.outputs['Color'],mix.inputs[1]);l.new(liquid_ramp.outputs['Color'],mix.inputs[2]);l.new(mix.outputs[0],bp.inputs['Base Color'])
tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=75; tex.inputs['Detail'].default_value=3
bu=n.new('ShaderNodeBump'); bu.inputs['Strength'].default_value=.10; bu.inputs['Distance'].default_value=.000045
l.new(tex.outputs['Fac'],bu.inputs['Height']); l.new(bu.outputs['Normal'],bp.inputs['Normal'])
soup_z=.099; soup_r=.1352
verts=[(0,0,soup_z)]; uv=[(.5,.5)]; faces=[]
steps=160; rings=28
for j in range(1,rings+1):
    r=soup_r*j/rings
    for i in range(steps):
        a=2*PI*i/steps
        z=soup_z+.00005*math.sin(a*11+r*430)+.0009*(j/rings)**18
        verts.append((r*math.cos(a),r*math.sin(a),z)); uv.append((.5+r*math.cos(a)/(.135*2),.5+r*math.sin(a)/(.135*2)))
for i in range(steps):faces.append((0,1+i,1+(i+1)%steps))
for j in range(rings-1):
    for i in range(steps):
        a=1+j*steps+i; b=1+j*steps+(i+1)%steps
        faces.append((a+steps,b+steps,b,a))
mesh('Broth | continuous shallow rippled surface',verts,faces,broth,'02_Broth',uv)
# Geometry directly below the liquid prevents an empty bowl at grazing views.
body,bod=simple('Broth volume body',(.36,.069,.004),.24)
stock=lathe('Opaque turbid stock below surface',[(.001,.035),(.076,.035),(.096,.047),(.111,.065),(.122,.083),(.133,.098),(.001,.098)],[body],'02_Broth',128)
oil,oilp=simple('Chili oil | clear amber thin film',(.70,.20,.007),.075)
oilp.inputs['Transmission Weight'].default_value=.28; oilp.inputs['IOR'].default_value=1.46
bubble,bup=simple('Fine stock bubbles',(.56,.23,.023),.11); bup.inputs['Transmission Weight'].default_value=.25
for i in range(130):
    a=random.uniform(0,2*PI); r=random.uniform(.03,.133)
    x,y=r*math.cos(a),r*math.sin(a)
    size=random.uniform(.0003,.0015)
    sphere('Chili oil lens %03d'%i,(x,y,soup_z+.00010),(size,size*random.uniform(.7,1.3),.000055),oil,'02_Broth',12,6)
for i in range(95):
    a=random.uniform(0,2*PI); r=random.uniform(.129,.135)
    size=random.uniform(.0003,.00085)
    sphere('Meniscus microbubble %03d'%i,(r*math.cos(a),r*math.sin(a),soup_z+.0002),(size,size,size*.4),bubble,'02_Broth',12,6)

# Food surfaces are multi-ring, double-sided, domed meshes, not camera-facing planes.
beefside,bsp=simple('Beef | cooked edge and connective tissue',(.30,.22,.14),.31)
bsp.inputs['Subsurface Weight'].default_value=.14; bsp.inputs['Subsurface Scale'].default_value=.002
noise_bump(beefside,bsp,110,.00025,.55)
vegside,vsp=simple('Vegetable | wet cut edge',(.30,.36,.065),.19)
vsp.inputs['Subsurface Weight'].default_value=.12; vsp.inputs['Subsurface Scale'].default_value=.003
mushside,msp=simple('Wood ear | gelatinous brown edge',(.025,.009,.003),.13)

def make_food(item):
    name=item['name']; points=item['polygon']; bbox=item['bbox']; h=item['height']
    # Densify each observed edge, preserving the traced outline and UV registration.
    dense=[]
    for i,(x,y) in enumerate(points):
        xx,yy=points[(i+1)%len(points)]
        for k in range(6):dense.append((x+(xx-x)*k/6,y+(yy-y)*k/6))
    center=(sum(x for x,y in dense)/len(dense),sum(y for x,y in dense)/len(dense))
    cnt=len(dense); v=[]; uv=[]
    for ring in range(9):
        f=ring/8
        for i,(px,py) in enumerate(dense):
            u=center[0]+(px-center[0])*f; w=center[1]+(py-center[1])*f
            x=(u-1024)/1024*.135; y=(1024-w)/1024*.135
            wave=.0004*math.sin(x*420+y*180)+.00022*math.cos(y*540)
            dome=.0016*(1-f*f) if name.startswith('Beef') else .0023*math.sin(f*PI)
            z=soup_z+h*.4+dome+wave
            v.append((x,y,z)); uv.append(((u-bbox[0])/bbox[2],1-(w-bbox[1])/bbox[3]))
    faces=[]
    for j in range(8):
        for i in range(cnt):
            a=j*cnt+i; b=j*cnt+(i+1)%cnt
            faces.append((a+cnt,b+cnt,b,a))
    bottom=len(v)
    for i in range(cnt):
        x,y,z=v[8*cnt+i]; v.append((x,y,soup_z-.001)); uv.append(uv[8*cnt+i])
    start_side=len(faces)
    for i in range(cnt):faces.append((8*cnt+i,8*cnt+(i+1)%cnt,bottom+(i+1)%cnt,bottom+i))
    faces.append(tuple(reversed(range(bottom,bottom+cnt))))
    rough=.39 if name.startswith('Beef') else .23 if 'ear' in name else .30
    mat,p,t=image_mat(name+' | original food surface',name+'.png',rough,.00027 if name.startswith('Beef') else .00016,.13)
    p.inputs['Coat Weight'].default_value=.08; p.inputs['Coat Roughness'].default_value=.22
    col='03_Beef' if name.startswith('Beef') else '04_Vegetables'
    ob=mesh(name+' | solid reference-matched mesh',v,faces,mat,col,uv)
    side=beefside if name.startswith('Beef') else mushside if 'ear' in name else vegside
    # Fine irregular wet meniscus hugs each ingredient silhouette.
    edge=[]
    for px,py in dense:
        x=(px-1024)/1024*.135;y=(1024-py)/1024*.135
        edge.append((x,y,soup_z+.00017))
    edge.append(edge[0])
    tube(name+' | thin wet contact edge',edge,.00020,oil,'02_Broth',2)
    ob.data.materials.append(side)
    for p in ob.data.polygons:
        if p.index>=start_side:p.material_index=1
    ob['reference']='Photo 4, perspective rectified'; ob['solid_thickness_m']=h
    return ob
for item in json.loads((ASSETS/'ingredients.json').read_text()):make_food(item)

noodle,np=simple('Hand pulled noodles | cooked wheat',(.75,.59,.26),.27)
np.inputs['Subsurface Weight'].default_value=.22; np.inputs['Subsurface Scale'].default_value=.002
for i in range(58):
    pts=[]; a=random.uniform(0,2*PI); offset=random.uniform(.015,.097)
    for j in range(45):
        t=j/44*2*PI
        x=.031*math.cos(t)+offset*math.cos(a)
        y=.025*math.sin(t)+offset*math.sin(a)
        z=.091+.0025*math.sin(t*2+i)
        if x*x+y*y<.128**2:pts.append((x,y,z))
    if len(pts)>3:tube('Submerged noodle strand %02d'%i,pts,.00095,noodle,'05_Noodles',2)
# A few visible looped noodles near the back and the right of the beef.
for i in range(9):
    pts=[]
    x0=.048+i*.0021; y0=.014+math.sin(i)*.008
    for j in range(26):
        t=j/25*PI*1.65
        pts.append((x0+.013*math.cos(t),y0+.019*math.sin(t),.0992+.0006*math.sin(t)))
    tube('Visible wheat loop %02d'%i,pts,.00072,noodle,'05_Noodles',3)

# Soup spoon: concave scoop plus a broad elliptical-section handle.
v=[]; f=[]
for j in range(19):
    r=j/18
    for i in range(65):
        a=i/64*2*PI
        x=-.086+.017*r*math.cos(a); y=.026+.025*r*math.sin(a)
        z=.100-.006*(1-r*r)
        v.append((x,y,z))
for j in range(18):
    for i in range(64):
        a=j*65+i; f.append((a,a+1,a+66,a+65))
sp=mesh('Spoon | concave ceramic scoop',v,f,white,'06_Spoon')
sol=sp.modifiers.new('Real ceramic thickness','SOLIDIFY'); sol.thickness=.002
su=sp.modifiers.new('Rounded spoon lip','SUBSURF'); su.levels=2
v=[]; f=[]
side=Vector((.82,-.12,.56)).normalized()
normal=Vector((.06,.99,.12)).normalized()
for j in range(57):
    t=j/56
    center=Vector((-.095-.089*t,.038+.012*t,.103+.128*t+.008*t*t))
    # Narrow waist, wider rounded end, sealed into an elliptical ceramic section.
    cap=math.sqrt(max(.004,1-((t-.94)/.06)**2)) if t>.94 else 1
    width=(.0045+.005*t+.004*math.exp(-((t-.86)/.16)**2))*cap
    for i in range(25):
        a=2*PI*i/24
        pos=center+side*width*math.cos(a)+normal*.0020*math.sin(a)
        v.append(tuple(pos))
for j in range(56):
    for i in range(24):
        a=j*25+i;f.append((a,a+1,a+26,a+25))
f.append(tuple(reversed(range(25))));f.append(tuple(range(56*25,57*25)))
handle=mesh('Spoon | wide flattened porcelain handle',v,f,white,'06_Spoon')
su=handle.modifiers.new('Polished handle contour','SUBSURF');su.levels=2

# Breads on a glazed square plate behind the main bowl.
plate=cube('Bread plate | rounded white ceramic',(-.065,.237,.008),(.25,.17,.012),white,'07_Bread',.015)
# Low raised rim on all four sides.
for loc,size in [((-.065,.318,.014),(.24,.010,.010)),((-.065,.156,.014),(.24,.010,.010)),((-.184,.237,.014),(.010,.15,.010)),((.054,.237,.014),(.010,.15,.010))]:cube('Bread plate raised lip',loc,size,white,'07_Bread',.004)
bread,breadp,breadt=image_mat('Flatbread | toasted photographic crumb','bread_color.jpg',.58,.0008,.12)
crumb,crumbp=simple('Flatbread torn edge',(.68,.48,.21),.68)
noise_bump(crumb,crumbp,65,.001,.7)
for k in range(8):
    cx=-.158+k*.026+random.uniform(-.003,.003); cy=.234+random.uniform(-.018,.018); cz=.025+random.uniform(0,.012)
    length=random.uniform(.12,.155); width=random.uniform(.025,.041)
    verts=[]; uv=[]; faces=[]; nx=12; ny=34
    for j in range(ny+1):
        for i in range(nx+1):
            x=(i/nx-.5)*width; y=(j/ny-.5)*length
            z=cz+.0022*math.sin(i*1.9+j*.7+k)+.001*math.sin(j*2)+y*.19
            verts.append((cx+x,cy+y,z));uv.append((i/nx,j/ny))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    o=mesh('Flatbread strip %02d'%k,verts,faces,bread,'07_Bread',uv)
    o.data.materials.append(crumb)
    so=o.modifiers.new('Layered bread thickness','SOLIDIFY');so.thickness=.0035;so.material_offset=1
    be=o.modifiers.new('Soft baked edges','BEVEL');be.width=.0008;be.segments=2
    su=o.modifiers.new('Natural bread curvature','SUBSURF');su.levels=1

# Ribbed thin plastic tea cup with an independent amber liquid volume.
plastic,pp=simple('Cup | thin clear polypropylene',(.94,.97,.93),.13)
pp.inputs['Transmission Weight'].default_value=1;pp.inputs['IOR'].default_value=1.46
cup=lathe('Tea cup | double wall and rolled rim',[(.001,.002),(.027,.002),(.029,.004),(.036,.085),(.038,.089),(.0385,.091),(.037,.092),(.0358,.09),(.035,.085),(.028,.005),(.001,.004)],[plastic],'08_Tea',128)
cup.location=(.242,.173,.001)
tea,tp=simple('Tea | amber transmission',(.60,.22,.018),.12)
tp.inputs['Transmission Weight'].default_value=.65;tp.inputs['IOR'].default_value=1.333
absorb=tea.node_tree.nodes.new('ShaderNodeVolumeAbsorption'); absorb.inputs['Color'].default_value=(.67,.25,.026,1);absorb.inputs['Density'].default_value=9
tea.node_tree.links.new(absorb.outputs['Volume'],tea.node_tree.nodes.get('Material Output').inputs['Volume'])
t=lathe('Tea | closed amber liquid',[(.001,.005),(.0275,.005),(.0345,.071),(.001,.071)],[tea],'08_Tea',128);t.location=cup.location
for j in range(20):
    z=.01+j*.0035; r=.029+z/.085*.007
    pts=[(.242+r*math.cos(a*2*PI/128),.173+r*math.sin(a*2*PI/128),z+.001) for a in range(129)]
    tube('Cup concentric pressed rib',pts,.00022,plastic,'08_Tea',2)
# White paper collar from the reference cup.
collar,cap=simple('Cup white upper collar',(.84,.86,.81),.35)
c=lathe('Cup | white collar',[(.0367,.079),(.0378,.089),(.038,.091)],[collar],'08_Tea',128);c.location=cup.location
chop,chp=simple('Black lacquer chopsticks',(.008,.010,.009),.24)
for i in range(2):
    o=cube('Resting chopstick %d'%i,(.245,.178+i*.009,.099+i*.001),(.28,.004,.004),chop,'08_Tea',.001)
    o.rotation_euler[2]=-.24

# Glass-topped reddish wooden lattice, with joinery and subtle wood grain.
wood,woodp=simple('Rosewood | directional grain',(.12,.032,.014),.30)
n=wood.node_tree.nodes;l=wood.node_tree.links
coord=n.new('ShaderNodeTexCoord'); mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(3,65,12)
l.new(coord.outputs['Generated'],mapping.inputs[0])
nt=n.new('ShaderNodeTexNoise');nt.inputs['Scale'].default_value=4;nt.inputs['Detail'].default_value=3;nt.inputs['Roughness'].default_value=.7
l.new(mapping.outputs[0],nt.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(.025,.006,.002,1);ramp.color_ramp.elements[1].position=.82;ramp.color_ramp.elements[1].color=(.22,.067,.025,1)
l.new(nt.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],woodp.inputs['Base Color'])
b=n.new('ShaderNodeBump');b.inputs['Distance'].default_value=.00022;b.inputs['Strength'].default_value=.22;l.new(nt.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],woodp.inputs['Normal'])
woodp.inputs['Coat Weight'].default_value=.3
for i in range(-7,8):
    cube('Lattice long rail %d'%i,(0,i*.095,-.024),(1.35,.022,.026),wood,'09_Table',.004)
    o=cube('Lattice cross rail %d'%i,(i*.095,0,-.03),(.022,1.35,.027),wood,'09_Table',.003)
    o.rotation_euler[2]=0
for loc,size in [((0,-.67,-.036),(1.43,.06,.06)),((0,.67,-.036),(1.43,.06,.06)),((-.69,0,-.036),(.06,1.34,.06)),((.69,0,-.036),(.06,1.34,.06))]:cube('Table heavy timber frame',loc,size,wood,'09_Table',.005)
glass,gp=simple('Table glass | faint green polished sheet',(.92,.97,.93),.09)
gp.inputs['Transmission Weight'].default_value=1;gp.inputs['IOR'].default_value=1.51
cube('Table | solid glass sheet',(0,0,-.004),(1.42,1.39,.008),glass,'09_Table',.0015)
# Hairline scratches are restrained geometry, not a white noise overlay.
scratch,scp=simple('Glass hairline marks',(.55,.62,.58),.29)
for i in range(38):
    x=random.uniform(-.5,.5);y=random.uniform(-.5,.5);length=random.uniform(.008,.06)
    tube('Fine tabletop wear %02d'%i,[(x,y,.000035),(x+length,y+length*.17,.000035)],.000008,scratch,'09_Table',0)
# Floor visible through the grid.
floor,fp=simple('Restaurant | pale tile',(.65,.66,.57),.44)
cube('Floor',(0,0,-.77),(8,8,.04),floor,'10_Interior',.001)
grout,grp=simple('Tile grout',(.36,.37,.32),.8)
for i in range(-8,9):
    cube('Tile joint X',(i*.5,0,-.749),( .002,8,.0005),grout,'10_Interior')
    cube('Tile joint Y',(0,i*.5,-.749),(8,.002,.0005),grout,'10_Interior')
# Background tables and chairs, deliberately simple but physically present for reflections.
wall,wlp=simple('Restaurant plaster',(.64,.65,.57),.8)
cube('Back wall',(0,2.5,.55),(7,.05,3),wall,'10_Interior',.01)
for x in [-1.0,.12,1.25]:
    cube('Background table',(x,1.5,-.05),(.85,.58,.05),wood,'10_Interior',.015)
    for sx in [-.32,.32]:
        for sy in [-.2,.2]:cube('Background table leg',(x+sx,1.5+sy,-.41),(.045,.045,.68),wood,'10_Interior',.003)
    for y in [1.12,1.88]:
        cube('Chair seat',(x,y,-.35),(.37,.34,.04),wood,'10_Interior',.01)
        cube('Chair back top',(x,y+.11,.12),(.38,.035,.085),wood,'10_Interior',.008)
        for dx in [-.15,.15]:cube('Chair back post',(x+dx,y+.11,-.12),(.032,.032,.55),wood,'10_Interior',.004)
        for dx in [-.14,.14]:
            for dy in [-.11,.11]:cube('Chair leg',(x+dx,y+dy,-.55),(.03,.03,.39),wood,'10_Interior',.003)
# Dark cabinet and yellow product boxes from the restaurant reference.
dark,dk=simple('Dark painted refrigerator',(.038,.045,.043),.3)
cube('Fridge body',(-1.40,2.03,.10),(.55,.37,1.65),dark,'10_Interior',.02)
yellow,yp=simple('Yellow stacked cartons',(.69,.46,.015),.55)
for j in range(5):
    for i in range(2):cube('Shelf carton',(-1.54+i*.24,1.827,-.49+j*.27),(.19,.015,.22),yellow,'10_Interior',.004)

# Soft broad sources, shaped like restaurant ceiling fixtures and a daylight window.
world=bpy.data.worlds.new('Neutral restaurant ambient');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.77,.83,.86,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.42
scene.world=world

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,power,color,size,target,shape='DISK',size_y=None):
    data=bpy.data.lights.new(name,'AREA');data.energy=power*.14;data.color=color;data.shape=shape;data.size=size
    if size_y and shape=='RECTANGLE':data.size_y=size_y
    o=bpy.data.objects.new(name,data);COL['11_Lighting'].objects.link(o);o.location=loc;aim(o,target);return o
area('Large window | soft key',(-.40,-.28,.75),22,(.89,.96,1),.26,(0,0,.08),'RECTANGLE',.55)
area('Ceiling | warm long reflection',(.18,.38,.83),26,(1,.88,.70),.50,(0,0,.08),'RECTANGLE',.13)
area('Right fill | room bounce',(.6,-.05,.42),12,(.85,1,.95),.4,(0,0,.07))
area('Rear separator',(-.25,.70,.48),12,(1,.92,.80),.32,(0,0,.05))

# Cameras include a high reference-matching view and a lower ceramic detail view.
def camera(name,loc,target,lens=48):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);COL['12_Cameras'].objects.link(o);o.location=loc;aim(o,target);d.lens=lens;d.clip_start=.003;d.clip_end=100
    d.dof.use_dof=True;d.dof.focus_distance=(Vector(target)-o.location).length;d.dof.aperture_fstop=7.1;return o
hero=camera('01 | Hero reference angle',(.025,-.49,.36),(0,.020,.080),49)
low=camera('02 | Low porcelain study',(.015,-.48,.265),(0,.025,.075),47)
top=camera('03 | Top food detail',(0,-.16,.56),(0,0,.09),53)
# A real orbit camera with a looping 120-frame movement; still rendering uses hero.
orbit=camera('04 | Orbit animation',(.30,-.41,.31),(0,0,.07),49)
target=bpy.data.objects.new('Orbit focus | bowl center',None);COL['12_Cameras'].objects.link(target);target.location=(0,0,.075)
track=orbit.constraints.new('TRACK_TO');track.target=target;track.track_axis='TRACK_NEGATIVE_Z';track.up_axis='UP_Y'
for frame in [1,31,61,91,121]:
    a=-PI/2+(frame-1)/120*2*PI
    orbit.location=(.49*math.cos(a),.49*math.sin(a),.32)
    aim(orbit,(0,0,.075));orbit.keyframe_insert(data_path='location',frame=frame);orbit.keyframe_insert(data_path='rotation_euler',frame=frame)
if orbit.animation_data and orbit.animation_data.action:
    pass
scene.camera=hero
scene.frame_start=1;scene.frame_end=120;scene.render.fps=24
scene.render.engine='CYCLES'
scene.cycles.device='CPU';scene.cycles.samples=96
scene.cycles.use_denoising=True
scene.cycles.adaptive_threshold=.025
scene.cycles.max_bounces=10;scene.cycles.transmission_bounces=7;scene.cycles.transparent_max_bounces=8
scene.render.resolution_x=1800;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=0
# Useful interactive starting view: material preview and selected main bowl.
for o in bpy.context.selected_objects:o.select_set(False)
bowl.select_set(True);bpy.context.view_layer.objects.active=bowl
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.region_3d.view_perspective='CAMERA'
scene['reconstruction_method']='Reference-guided 2.5D/3D hybrid: full ceramic, utensils, noodles, table; photo-textured solid ingredient meshes. Not a photogrammetric scan.'
scene['reference_scale']='Estimated bowl outer diameter 29.8 cm; no calibration object in source.'
scene['source_video']='74cfb5759273a55d9f0fe0d24c63dc00.mp4, 9.67 seconds'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lamian_Reconstruction.blend'))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lamian_Reconstruction.blend'))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--render' in args:
    mode=args[args.index('--render')+1]
    if mode=='preview':
        scene.render.resolution_percentage=50;scene.cycles.samples=24;scene.cycles.adaptive_threshold=.07
        scene.render.filepath=str(OUT/'preview.png')
    else:scene.render.filepath=str(OUT/'hero.png')
    bpy.ops.render.render(write_still=True)
print('SCENE_READY',str(OUT/'Lamian_Reconstruction.blend'))
