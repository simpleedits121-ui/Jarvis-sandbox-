"""JARVIS Character Forge v0.6: smoother parametric anime character blockout.
Offline procedural geometry; intentionally an original Rem-inspired design, not a franchise asset.
"""
from __future__ import annotations
import json, math, struct
from pathlib import Path

PALETTE = {
 "skin":(0.96,0.76,0.66,1),"skin_shadow":(0.72,0.43,0.36,1),
 "hair":(0.12,0.48,0.78,1),"hair_light":(0.30,0.70,0.92,1),
 "hair_dark":(0.055,0.25,0.48,1),"dress":(0.075,0.12,0.23,1),
 "blue":(0.12,0.48,0.83,1),"white":(0.94,0.97,1,1),
 "eye":(0.04,0.42,0.83,1),"iris_light":(0.18,0.72,0.98,1),
 "black":(0.025,0.035,0.06,1),"shoe":(0.035,0.055,0.10,1),
 "gold":(0.96,0.68,0.20,1),"pink":(0.92,0.38,0.52,1),
 "mouth":(0.42,0.12,0.18,1)
}
class Part:
 def __init__(self,name,material): self.name=name;self.material=material;self.v=[];self.f=[]
 def tri(self,a,b,c): self.f.append((a,b,c))

def ellipsoid(p,c,s,seg=32,rings=20):
 base=len(p.v)
 for j in range(rings+1):
  ph=math.pi*j/rings
  for i in range(seg):
   th=2*math.pi*i/seg
   p.v.append((c[0]+s[0]*math.sin(ph)*math.cos(th),c[1]+s[1]*math.cos(ph),c[2]+s[2]*math.sin(ph)*math.sin(th)))
 for j in range(rings):
  for i in range(seg):
   a=base+j*seg+i;b=base+j*seg+(i+1)%seg;c1=base+(j+1)*seg+(i+1)%seg;d=base+(j+1)*seg+i
   p.tri(a,d,b);p.tri(b,d,c1)

def tube(p,points,radii,sides=12):
 """Smooth swept tube through a polyline, with a stable local frame."""
 pts=[tuple(map(float,q)) for q in points]
 if len(pts)<2:return
 base=len(p.v)
 for k,pt in enumerate(pts):
  prev=pts[max(0,k-1)];nxt=pts[min(len(pts)-1,k+1)]
  t=[nxt[i]-prev[i] for i in range(3)];ln=math.sqrt(sum(v*v for v in t)) or 1;t=[v/ln for v in t]
  ref=(0,0,1) if abs(t[2])<.88 else (0,1,0)
  u=[t[1]*ref[2]-t[2]*ref[1],t[2]*ref[0]-t[0]*ref[2],t[0]*ref[1]-t[1]*ref[0]]
  ul=math.sqrt(sum(v*v for v in u)) or 1;u=[v/ul for v in u]
  v=[t[1]*u[2]-t[2]*u[1],t[2]*u[0]-t[0]*u[2],t[0]*u[1]-t[1]*u[0]]
  r=radii[k] if isinstance(radii,(list,tuple)) else radii
  for i in range(sides):
   a=2*math.pi*i/sides
   p.v.append(tuple(pt[q]+r*(u[q]*math.cos(a)+v[q]*math.sin(a)) for q in range(3)))
 for k in range(len(pts)-1):
  for i in range(sides):
   a=base+k*sides+i;b=base+k*sides+(i+1)%sides;c=base+(k+1)*sides+(i+1)%sides;d=base+(k+1)*sides+i
   p.tri(a,b,d);p.tri(b,c,d)

def ring_surface(p, rings, sides=48, thickness=False):
 base=len(p.v)
 for y,rx,rz in rings:
  for i in range(sides):
   a=2*math.pi*i/sides;p.v.append((rx*math.cos(a),y,rz*math.sin(a)))
 for j in range(len(rings)-1):
  for i in range(sides):
   a=base+j*sides+i;b=base+j*sides+(i+1)%sides;c=base+(j+1)*sides+(i+1)%sides;d=base+(j+1)*sides+i
   p.tri(a,d,b);p.tri(b,d,c)

def make_character():
 parts=[]
 def P(n,m): q=Part(n,m);parts.append(q);return q
 # body silhouette, shoulders/waist/hips
 p=P("Torso_Skin","skin");ellipsoid(p,(0,1.48,0),(0.205,.29,.135));ellipsoid(p,(0,1.25,-.005),(.205,.18,.14))
 p=P("Neck","skin");ellipsoid(p,(0,1.72,0),(.075,.12,.075),20,12)
 p=P("Face_Head","skin");ellipsoid(p,(0,2.055,.015),(.235,.305,.205),48,32)
 # subtle chin/jaw volume
 p=P("Ear_Details","skin_shadow")
 for x in (-1,1): ellipsoid(p,(x*.226,2.02,.005),(.035,.065,.045),16,12)
 # eyes layered on front plane
 p=P("Eye_Whites","white")
 for x in (-.092,.092): ellipsoid(p,(x,2.075,.196),(.061,.087,.027),24,16)
 p=P("Iris_Blue","eye")
 for x in (-.092,.092): ellipsoid(p,(x,2.07,.220),(.038,.061,.018),24,16)
 p=P("Iris_Light","iris_light")
 for x in (-.092,.092): ellipsoid(p,(x,2.055,.235),(.022,.036,.010),20,12)
 p=P("Pupils","black")
 for x in (-.092,.092): ellipsoid(p,(x,2.071,.241),(.014,.029,.008),16,12)
 p=P("Eye_Highlights","white")
 for x in (-.103,.081):
  ellipsoid(p,(x,2.096,.251),(.012,.018,.006),12,8)
  ellipsoid(p,(x+.012,2.052,.248),(.006,.008,.004),10,6)
 p=P("Upper_Eyelashes","hair_dark")
 for x in (-1,1):
  tube(p,[(x*.045,2.145,.211),(x*.09,2.158,.218),(x*.14,2.14,.20)],[.009,.012,.002],8)
 p=P("Brows","hair")
 for x in (-1,1): tube(p,[(x*.05,2.18,.195),(x*.095,2.19,.197),(x*.14,2.18,.18)],[.008,.009,.003],8)
 p=P("Nose","skin_shadow");ellipsoid(p,(0,2.005,.211),(.014,.018,.012),12,8)
 p=P("Mouth","mouth");ellipsoid(p,(0,1.935,.203),(.027,.008,.008),16,8)
 # dress fitted bodice and bib
 p=P("Maid_Bodice","dress");ellipsoid(p,(0,1.48,.008),(.215,.255,.15),32,24)
 p=P("Apron_Bib","white");ellipsoid(p,(0,1.49,.139),(.118,.19,.027),32,20)
 p=P("Apron_Bow","white")
 ellipsoid(p,(-.055,1.30,.15),(.065,.04,.025));ellipsoid(p,(.055,1.30,.15),(.065,.04,.025));ellipsoid(p,(0,1.30,.17),(.025,.03,.018))
 p=P("Collar","white")
 tube(p,[(-.15,1.68,.025),(-.09,1.72,.09),(0,1.69,.12),(.09,1.72,.09),(.15,1.68,.025)],[.027,.03,.032,.03,.027],12)
 # flared layered skirt with dark underskirt and blue outer shell
 p=P("Skirt_Underskirt","dress");ring_surface(p,[(1.30,.17,.14),(1.02,.39,.31)],64)
 p=P("Skirt_Outer","blue");ring_surface(p,[(1.29,.18,.15),(1.015,.405,.33)],64)
 p=P("Skirt_Hem","white")
 for i in range(40):
  a=2*math.pi*i/40
  tube(p,[(.39*math.cos(a),1.025,.315*math.sin(a)),(.405*math.cos(a),1.012,.33*math.sin(a))],[.009,.006],6)
 p=P("Skirt_Pleat_Seams","hair_light")
 for i in range(20):
  a=2*math.pi*i/20
  tube(p,[(.18*math.cos(a),1.28,.15*math.sin(a)),(.405*math.cos(a),1.02,.33*math.sin(a))],[.009,.004],6)
 # arms, sleeves, cuffs, palms and fingers
 p=P("Arms","skin")
 for s in (-1,1):
  tube(p,[(s*.19,1.60,0),(s*.29,1.48,.005),(s*.34,1.32,.025),(s*.37,1.20,.06)],[.067,.058,.047,.035],16)
  ellipsoid(p,(s*.37,1.17,.07),(.047,.062,.032),20,12)
  for f in range(4):
   xx=s*(.345+f*.014)
   tube(p,[(xx,1.16,.084),(xx+s*.008,1.115,.09),(xx+s*.006,1.09,.085)],[.012,.009,.004],8)
 p=P("Puff_Sleeves","white")
 for s in (-1,1):
  ellipsoid(p,(s*.235,1.565,.005),(.105,.105,.095),24,16)
  tube(p,[(s*.18,1.49,.04),(s*.25,1.46,.045),(s*.31,1.43,.04)],[.018,.02,.014],10)
 # legs and boots
 p=P("Legs","skin")
 for s in (-1,1):
  tube(p,[(s*.12,1.04,0),(s*.125,.82,0),(s*.13,.60,.005)],[.073,.061,.052],16)
 p=P("Boots","shoe")
 for s in (-1,1):
  ellipsoid(p,(s*.13,.47,.035),(.075,.15,.13),24,16)
  tube(p,[(s*.13,.54,0),(s*.13,.62,0)],[.058,.052],16)
 p=P("Boot_Cuffs","white")
 for s in (-1,1): ellipsoid(p,(s*.13,.585,.005),(.059,.025,.06),20,10)
 # hair cap/back volume, distinct curved locks
 p=P("Hair_Cap","hair");ellipsoid(p,(0,2.235,-.025),(.258,.205,.22),40,24)
 p=P("Hair_Back","hair_dark");ellipsoid(p,(0,2.015,-.145),(.265,.39,.115),36,24)
 p=P("Hair_Back_Layers","hair")
 for s in (-1,1):
  for k in range(3):
   x=s*(.17+k*.025)
   tube(p,[(x,2.20,-.10),(s*(.22+k*.018),2.02,-.19),(s*(.23+k*.018),1.82,-.15),(s*(.20+k*.02),1.70,-.10)],[.052,.048,.032,.004],12)
 p=P("Bangs_Main","hair_light")
 for i in range(7):
  x=-.18+i*.06
  tube(p,[(x*.72,2.39,.02),(x,2.30,.14),(x*.95,2.18,.19),(x*.82,2.075,.19)],[.055,.049,.031,.003],14)
 p=P("Bangs_Shadow","hair_dark")
 for i in range(6):
  x=-.15+i*.06
  tube(p,[(x*.7,2.36,.035),(x*.88,2.25,.16),(x*.8,2.16,.194)],[.014,.011,.002],8)
 p=P("Side_Framing_Locks","hair")
 for s in (-1,1):
  for k in range(2):
   x=s*(.19+k*.035)
   tube(p,[(s*.18,2.22,.045),(x,2.10,.16),(s*(.22+k*.025),1.93,.15),(s*(.205+k*.025),1.77,.12)],[.052,.045,.03,.003],14)
 # hair accessory, maid headband and bow
 p=P("Headband","white")
 tube(p,[(-.20,2.34,-.035),(-.15,2.405,-.06),(0,2.43,-.075),(.15,2.405,-.06),(.20,2.34,-.035)],[.018,.02,.02,.02,.018],12)
 p=P("Hair_Ribbon","blue")
 ellipsoid(p,(-.16,2.36,-.09),(.045,.035,.035),16,10)
 tube(p,[(-.17,2.36,-.09),(-.27,2.31,-.07),(-.30,2.23,-.045)],[.035,.023,.002],12)
 tube(p,[(-.15,2.36,-.09),(-.08,2.30,-.08),(-.04,2.22,-.05)],[.035,.022,.002],12)
 p=P("Brooch","gold");ellipsoid(p,(0,1.57,.17),(.035,.043,.018),20,12)
 p=P("Waist_Ribbon","blue")
 ellipsoid(p,(-.19,1.28,-.01),(.07,.045,.045));ellipsoid(p,(.19,1.28,-.01),(.07,.045,.045))
 return parts

def write_obj(parts,folder,stem):
 mtl=[];lines=['# JARVIS Character Forge v0.6','mtllib '+stem+'.mtl'];off=1
 for name,c in PALETTE.items():mtl += [f'newmtl {name}',f'Kd {c[0]} {c[1]} {c[2]}','Ka 0.06 0.06 0.06','Ks 0.3 0.3 0.3','Ns 48','']
 for p in parts:
  if not p.v or not p.f:continue
  lines += [f'o {p.name}',f'usemtl {p.material}']
  lines += [f'v {x:.6f} {y:.6f} {z:.6f}' for x,y,z in p.v]
  lines += [f'f {a+off} {b+off} {c+off}' for a,b,c in p.f];off+=len(p.v)
 (folder/(stem+'.obj')).write_text('\n'.join(lines)+'\n')
 (folder/(stem+'.mtl')).write_text('\n'.join(mtl))

def write_glb(parts,folder,stem):
 blob=bytearray();views=[];accessors=[];meshes=[];nodes=[];materials=[]
 def view(data,target):
  while len(blob)%4:blob.append(0)
  off=len(blob);blob.extend(data);views.append({'buffer':0,'byteOffset':off,'byteLength':len(data),'target':target});return len(views)-1
 for n,c in PALETTE.items():
  materials.append({'name':n,'pbrMetallicRoughness':{'baseColorFactor':list(c),'metallicFactor':0.0,'roughnessFactor':0.58 if n not in ('eye','gold') else .32}})
 mi={n:i for i,n in enumerate(PALETTE)}
 for p in parts:
  if not p.v or not p.f:continue
  # smooth vertex normals averaged from adjacent faces; preserve indexed geometry.
  norms=[[0.,0.,0.] for _ in p.v]
  for a,b,c in p.f:
   A=p.v[a];B=p.v[b];C=p.v[c]
   u=[B[i]-A[i] for i in range(3)];v=[C[i]-A[i] for i in range(3)]
   n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
   for idx in (a,b,c):
    for k in range(3):norms[idx][k]+=n[k]
  for n in norms:
   l=math.sqrt(sum(x*x for x in n)) or 1
   for k in range(3):n[k]/=l
  pos=[x for v in p.v for x in v];normal=[x for n in norms for x in n]
  idx=[i for f in p.f for i in f]
  pv=view(struct.pack('<%sf'%len(pos),*pos),34962)
  nv=view(struct.pack('<%sf'%len(normal),*normal),34962)
  iv=view(struct.pack('<%sI'%len(idx),*idx),34963)
  xs=pos[0::3];ys=pos[1::3];zs=pos[2::3]
  accessors.append({'bufferView':pv,'componentType':5126,'count':len(p.v),'type':'VEC3','min':[min(xs),min(ys),min(zs)],'max':[max(xs),max(ys),max(zs)]});pa=len(accessors)-1
  accessors.append({'bufferView':nv,'componentType':5126,'count':len(p.v),'type':'VEC3'});na=len(accessors)-1
  accessors.append({'bufferView':iv,'componentType':5125,'count':len(idx),'type':'SCALAR'});ia=len(accessors)-1
  meshes.append({'name':p.name,'primitives':[{'attributes':{'POSITION':pa,'NORMAL':na},'indices':ia,'material':mi[p.material]}]})
  nodes.append({'name':p.name,'mesh':len(meshes)-1})
 doc={'asset':{'version':'2.0','generator':'JARVIS Character Forge v0.6 Offline'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],'nodes':nodes,'meshes':meshes,'materials':materials,'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors}
 js=json.dumps(doc,separators=(',',':')).encode()
 while len(js)%4:js+=b' '
 while len(blob)%4:blob.append(0)
 total=12+8+len(js)+8+len(blob)
 (folder/(stem+'.glb')).write_bytes(struct.pack('<III',0x46546C67,2,total)+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(blob),0x004E4942)+blob)

def generate_character(output_dir:Path,character:str='rem-inspired')->dict:
 output_dir.mkdir(parents=True,exist_ok=True);stem='jarvis_rem_character';parts=make_character()
 write_obj(parts,output_dir,stem);write_glb(parts,output_dir,stem)
 tris=sum(len(p.f) for p in parts);verts=sum(len(p.v) for p in parts)
 report={'name':'Original blue-haired maid anime character','generator':'JARVIS Character Forge v0.6 smooth procedural geometry','character':character,'parts':len(parts),'vertices':verts,'triangles':tris,'materials':len(PALETTE),'files':[stem+'.glb',stem+'.obj',stem+'.mtl',stem+'_report.json'],'features':['smooth indexed mesh normals','layered anime eyes with iris, pupils and highlights','curved tapered hair locks and layered fringe','flared layered skirt with hem and pleat seams','separate clothing, accessories, limbs and facial features'],'limitations':['Procedural stylized model; not a direct reconstruction of a copyrighted character','No UV texture maps yet; uses PBR palette materials','No skeleton, skin weights or animation yet','Facial detail and garment folds remain stylized and need further refinement']}
 (output_dir/(stem+'_report.json')).write_text(json.dumps(report,indent=2));return report
