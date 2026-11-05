"""Extract reference-derived textures, food silhouettes and video contact sheet."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)
photos = sorted(ROOT.glob('*.jpg'))
photos = [p for p in photos if p.name.startswith('\u5fae\u4fe1')]
source = Image.open(photos[3]).convert('RGB').resize((2000, 1500))
src = np.array(source)
# Four measured cardinal points of the soup surface, in reference photograph 4.
H = cv2.getPerspectiveTransform(np.float32([[1000,380],[1640,850],[1030,1370],[415,850]]), np.float32([[1024,0],[2048,1024],[1024,2048],[0,1024]]))
rectified = cv2.warpPerspective(src, H, (2048,2048), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
Image.fromarray(rectified).save(OUT/'soup_albedo.jpg', quality=98)
regions = [
 ('Beef_crown', [(992,481),(1115,468),(1190,481),(1180,565),(1156,644),(1115,731),(1064,772),(988,781),(881,748),(816,710),(798,672),(820,610),(890,542)], .0065),
 ('Beef_front', [(797,792),(878,776),(959,801),(1034,845),(1062,906),(1117,1006),(1138,1082),(1098,1093),(1006,1042),(931,1030),(833,1007),(745,972),(665,938),(648,918),(714,860)], .0045),
 ('Beef_right', [(1120,682),(1177,689),(1230,738),(1275,806),(1256,873),(1207,922),(1169,936),(1105,908),(1090,845),(1051,803)], .004),
 ('Beef_left', [(710,708),(762,698),(789,733),(758,811),(705,899),(653,945),(590,975),(568,959),(582,904),(627,805)], .004),
 ('Beef_small', [(1045,773),(1081,762),(1110,780),(1128,825),(1103,848),(1080,827)], .005),
 ('Bok_choy_leaf', [(1214,867),(1269,861),(1306,841),(1322,852),(1336,888),(1336,914),(1318,944),(1264,948),(1209,937),(1165,914),(1174,888)], .005),
 ('Cabbage_right', [(1407,986),(1484,957),(1539,990),(1563,1047),(1527,1116),(1492,1138),(1432,1111),(1404,1073)], .005),
 ('Cabbage_front', [(830,1105),(900,1090),(983,1126),(1031,1170),(983,1228),(894,1232),(812,1202),(790,1161)], .0035),
 ('Cabbage_small', [(1214,1189),(1284,1201),(1322,1227),(1314,1260),(1277,1269),(1204,1237)], .003),
 ('Cabbage_back', [(1252,424),(1308,415),(1365,437),(1370,492),(1333,524),(1269,492)], .005),
 ('Tomato_right', [(1438,670),(1491,692),(1538,739),(1562,809),(1539,861),(1508,855),(1488,793),(1461,738)], .006),
 ('Tomato_cube', [(1363,604),(1418,620),(1437,656),(1405,693),(1350,673),(1343,631)], .004),
 ('Onion_white', [(1377,769),(1428,782),(1456,813),(1426,839),(1380,834),(1342,863),(1316,853),(1321,820)], .003),
 ('Wood_ear_1', [(562,1001),(604,1002),(636,975),(671,981),(698,1015),(687,1059),(649,1072),(621,1098),(579,1125),(548,1103),(547,1059)], .007),
 ('Wood_ear_2', [(642,967),(674,951),(697,978),(715,1013),(705,1045),(675,1049),(654,1015)], .006),
 ('Egg_back', [(854,452),(917,427),(980,425),(1033,445),(1056,474),(1024,510),(967,533),(907,525),(871,501)], .003),
 ('Cabbage_bottom', [(871,1243),(942,1271),(1036,1293),(1084,1321),(1076,1352),(999,1352),(908,1326),(877,1304)], .003),
]
metadata=[]
mask_all=np.zeros((2048,2048),np.uint8)
for name,points,height in regions:
    p=np.float32(points).reshape(-1,1,2)
    uv=cv2.perspectiveTransform(p,H).reshape(-1,2)
    mask=np.zeros((2048,2048),np.uint8)
    cv2.fillPoly(mask,[uv.astype(np.int32)],255)
    mask_all=cv2.bitwise_or(mask_all,mask)
    x,y,w,h=cv2.boundingRect(uv.astype(np.int32))
    pad=12; x=max(0,x-pad); y=max(0,y-pad); w=min(2048-x,w+2*pad); h=min(2048-y,h+2*pad)
    rgba=np.dstack([rectified[y:y+h,x:x+w],mask[y:y+h,x:x+w]])
    Image.fromarray(rgba).save(OUT/f'{name}.png')
    metadata.append({'name':name,'polygon':uv.tolist(),'bbox':[x,y,w,h],'height':height})
(OUT/'ingredients.json').write_text(json.dumps(metadata,indent=2))
# Preserve real suspended egg/vegetable detail while replacing occluded food and baked glare.
rng=np.random.default_rng(81)
ys,xs=np.mgrid[0:2048,0:2048].astype(np.float32)
coarse=rng.random((40,40)).astype(np.float32)
coarse=cv2.resize(coarse,(2048,2048),interpolation=cv2.INTER_CUBIC)
base=np.empty_like(rectified)
base[:,:,0]=np.clip(180+coarse*45,0,255)
base[:,:,1]=np.clip(83+coarse*42,0,255)
base[:,:,2]=np.clip(7+coarse*14,0,255)
hsv=cv2.cvtColor(rectified,cv2.COLOR_RGB2HSV)
glare=((hsv[:,:,1]<82)&(hsv[:,:,2]>152)).astype(np.uint8)*255
replacement=cv2.dilate(mask_all,np.ones((19,19),np.uint8))
replacement=cv2.bitwise_or(replacement,cv2.dilate(glare,np.ones((5,5),np.uint8)))
blend=cv2.GaussianBlur(replacement,(33,33),9).astype(np.float32)/255
liquid=rectified.astype(np.float32)*(1-blend[:,:,None])+base.astype(np.float32)*blend[:,:,None]
# Keep texture variation subtle enough to accept new lighting.
liquid=np.clip(liquid*.78+base*.22,0,255).astype(np.uint8)
Image.fromarray(liquid).save(OUT/'broth_color.jpg',quality=97)

side=Image.open(photos[1]).convert('RGB').resize((2000,1500))
flower=np.array(side.crop((681,777,1021,1039)))
hsv=cv2.cvtColor(flower,cv2.COLOR_RGB2HSV)
alpha=cv2.inRange(hsv,np.array([90,60,12]),np.array([135,255,220]))
alpha=cv2.GaussianBlur(alpha,(3,3),.5)
blue=np.zeros_like(flower); blue[:]=[15,43,91]
flower=Image.fromarray(np.dstack((blue,alpha)))
flower.save(OUT/'flower_decal.png')
canvas=Image.new('RGB',(4096,1024),(234,234,219))
for i in range(8):
    f=flower.resize((470,410 if i%2 else 480),Image.Resampling.LANCZOS)
    if i%2:f=f.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    canvas.paste(f,(i*512+20,360 if i%2 else 290),f)
# Two thin cobalt registration bands and the thick hand-glazed lip.
d=ImageDraw.Draw(canvas)
d.rectangle((0,0,4095,48), fill=(22,62,128))
d.rectangle((0,98,4095,108),fill=(27,53,91))
d.rectangle((0,930,4095,939),fill=(27,53,91))
canvas.save(OUT/'porcelain_outer.png')
inner=Image.new('RGB',(4096,512),(234,234,220))
for i in range(22):
    f=flower.resize((170,105),Image.Resampling.LANCZOS)
    inner.paste(f,(i*187,75),f)
d=ImageDraw.Draw(inner)
for y,th in [(12,25),(55,5),(65,3),(205,5)]:d.rectangle((0,y,4095,y+th),fill=(28,61,115))
inner.save(OUT/'porcelain_inner.png')
# Front logo is an actual photograph-derived decal, preserving the lettering.
front=Image.open(photos[2]).convert('RGB').resize((2000,1500))
logo=np.array(front.crop((427,850,1181,1191)))
hsv=cv2.cvtColor(logo,cv2.COLOR_RGB2HSV)
a=np.where((hsv[:,:,1]>80)&(hsv[:,:,2]<205),255,0).astype(np.uint8)
logo=np.dstack((logo,a))
Image.fromarray(logo).save(OUT/'bowl_logo.png')

# Bread surface color from the reference; avoid including plate and bowl edges.
bread=source.crop((840,28,1093,247)).resize((1024,1024),Image.Resampling.LANCZOS)
bread.save(OUT/'bread_color.jpg',quality=97)
print('Prepared',len(regions),'food silhouettes and porcelain textures in',OUT)
