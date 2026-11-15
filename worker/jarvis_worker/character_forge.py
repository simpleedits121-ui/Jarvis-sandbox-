"""Offline procedural anime maid character generator. No network/model required.
Creates a stylized, editable GLB + OBJ/MTL starter asset (not a production rig).
"""
from __future__ import annotations
import json, math, struct
from pathlib import Path
from typing import Iterable

# RGBA linear-ish palette inspired by a blue-haired fantasy maid; not an exact franchise model.
PALETTE = {
    "skin": (0.93, 0.70, 0.58, 1), "hair": (0.12, 0.48, 0.78, 1),
    "hair_light": (0.28, 0.68, 0.91, 1), "dress": (0.10, 0.15, 0.28, 1),
    "white": (0.91, 0.94, 1.0, 1), "blue": (0.12, 0.48, 0.83, 1),
    "gold": (0.95, 0.68, 0.20, 1), "eye": (0.08, 0.48, 0.84, 1),
    "black": (0.025, 0.035, 0.06, 1), "shoe": (0.045, 0.06, 0.11, 1),
    "pink": (0.95, 0.48, 0.62, 1),
}
class Part:
    def __init__(self, name, material): self.name=name; self.material=material; self.v=[]; self.f=[]
    def tri(self,a,b,c): self.f.append((a,b,c))

def sphere(p, center, scale, seg=16, rings=10):
    base=len(p.v)
    for j in range(rings+1):
        phi=math.pi*j/rings
        for i in range(seg):
            th=2*math.pi*i/seg
            p.v.append((center[0]+scale[0]*math.sin(phi)*math.cos(th), center[1]+scale[1]*math.cos(phi), center[2]+scale[2]*math.sin(phi)*math.sin(th)))
    for j in range(rings):
        for i in range(seg):
            a=base+j*seg+i; b=base+j*seg+(i+1)%seg; c=base+(j+1)*seg+(i+1)%seg; d=base+(j+1)*seg+i
            p.tri(a,b,d); p.tri(b,c,d)

def cylinder_between(p, a, b, r1, r2=None, sides=12):
    if r2 is None:r2=r1
    ax,ay,az=a; bx,by,bz=b; dx=bx-ax;dy=by-ay;dz=bz-az
    length=math.sqrt(dx*dx+dy*dy+dz*dz) or 1
    ux,uy,uz=dx/length,dy/length,dz/length
    # stable perpendicular basis
    ref=(0,1,0) if abs(uy)<0.9 else (1,0,0)
    vx=uy*ref[2]-uz*ref[1]; vy=uz*ref[0]-ux*ref[2]; vz=ux*ref[1]-uy*ref[0]
    vl=math.sqrt(vx*vx+vy*vy+vz*vz) or 1; vx/=vl;vy/=vl;vz/=vl
    wx=uy*vz-uz*vy; wy=uz*vx-ux*vz; wz=ux*vy-uy*vx
    base=len(p.v)
    for point,r in ((a,r1),(b,r2)):
        for i in range(sides):
            t=2*math.pi*i/sides
            p.v.append((point[0]+r*(vx*math.cos(t)+wx*math.sin(t)),point[1]+r*(vy*math.cos(t)+wy*math.sin(t)),point[2]+r*(vz*math.cos(t)+wz*math.sin(t))))
    for i in range(sides):
        n=(i+1)%sides; p.tri(base+i,base+n,base+sides+i);p.tri(base+n,base+sides+n,base+sides+i)
    p.v.extend([a,b]); ca=len(p.v)-2; cb=ca+1
    for i in range(sides):
        n=(i+1)%sides;p.tri(ca,base+n,base+i);p.tri(cb,base+sides+i,base+sides+n)

def make_character():
    parts=[]
    def part(name,mat):
        x=Part(name,mat);parts.append(x);return x
    # body / silhouette, Y is vertical; front faces +Z
    p=part('Body_Core','skin'); sphere(p,(0,1.02,0),(0.23,0.34,0.14)); sphere(p,(0,1.48,0),(0.18,0.22,0.13))
    p=part('Head','skin'); sphere(p,(0,2.02,0),(0.255,0.32,0.23),24,16)
    p=part('Neck','skin'); cylinder_between(p,(0,1.69,0),(0,1.82,0),0.075,0.07)
    # face eyes, iris highlights, mouth and brows
    p=part('Eyes_Blue','eye')
    for x in (-0.105,0.105): sphere(p,(x,2.055,0.207),(0.052,0.078,0.025),12,8)
    p=part('Eye_Highlights','white')
    for x in (-0.115,0.095): sphere(p,(x-0.012,2.082,0.231),(0.014,0.022,0.009),8,6)
    p=part('Mouth','pink'); sphere(p,(0,1.91,0.224),(0.035,0.009,0.008),10,6)
    p=part('Brows','hair');
    for x in (-0.105,0.105): cylinder_between(p,(x-0.045,2.145,0.205),(x+0.045,2.15,0.205),0.012,0.009,8)
    # dress bodice, collar and apron
    p=part('Dress_Bodice','dress'); sphere(p,(0,1.43,0),(0.225,0.27,0.17))
    p=part('White_Collar','white'); cylinder_between(p,(-0.14,1.64,0.02),(0,1.72,0.04),0.055,0.04); cylinder_between(p,(0,1.72,0.04),(0.14,1.64,0.02),0.04,0.055)
    p=part('Apron','white'); sphere(p,(0,1.37,0.155),(0.15,0.22,0.035))
    p=part('Skirt_Blue','dress')
    # flared skirt surface as rings
    base=len(p.v); n=32
    for y,r in ((1.27,0.19),(1.04,0.39)):
        for i in range(n):
            a=2*math.pi*i/n;p.v.append((r*math.cos(a),y,r*math.sin(a)))
    for i in range(n):j=(i+1)%n;p.tri(base+i,base+j,base+n+i);p.tri(base+j,base+n+j,base+n+i)
    # pleat accents
    p=part('Skirt_Pleats','blue')
    for i in range(16):
        a=2*math.pi*i/16; r=0.395
        cylinder_between(p,(0.21*math.cos(a),1.25,0.21*math.sin(a)),(r*math.cos(a),1.045,r*math.sin(a)),0.012,0.009,6)
    p=part('Apron_Ruffles','white')
    for i in range(24):
        a=2*math.pi*i/24;sphere(p,(0.29*math.cos(a),1.055,0.29*math.sin(a)),(0.035,0.045,0.025),8,5)
    # arms, cuffs, gloves
    p=part('Arms','skin')
    for side in (-1,1):
        shoulder=(side*0.22,1.57,0); elbow=(side*0.34,1.34,0.035); hand=(side*0.39,1.15,0.10)
        cylinder_between(p,shoulder,elbow,0.075,0.058); cylinder_between(p,elbow,hand,0.055,0.04); sphere(p,hand,(0.055,0.07,0.045))
    p=part('Sleeves','white')
    for side in (-1,1): cylinder_between(p,(side*0.22,1.57,0),(side*0.29,1.46,0.02),0.095,0.07)
    p=part('Legs','skin')
    for side in (-1,1):
        x=side*0.14;cylinder_between(p,(x,1.03,0),(x,0.56,0),0.075,0.055);sphere(p,(x,0.53,0),(0.06,0.07,0.06))
    p=part('Boots','shoe')
    for side in (-1,1):
        x=side*0.14;sphere(p,(x,0.39,0.055),(0.09,0.14,0.15));cylinder_between(p,(x,0.42,0),(x,0.52,0),0.07,0.065)
    p=part('Hair_Cap','hair');sphere(p,(0,2.19,-0.015),(0.275,0.23,0.245),24,14)
    p=part('Hair_Back','hair');sphere(p,(0,1.99,-0.16),(0.29,0.43,0.15),20,12)
    p=part('Hair_Fringe','hair')
    for x in (-0.19,-0.12,-0.04,0.04,0.12,0.19):
        cylinder_between(p,(x*0.7,2.28,0.12),(x,2.02,0.205),0.055,0.018,10)
    p=part('Side_Locks','hair_light')
    for side in (-1,1):
        cylinder_between(p,(side*0.22,2.13,0.02),(side*0.24,1.73,0.02),0.065,0.025,10)
    p=part('Hair_Ribbon','blue')
    sphere(p,(-0.13,2.32,-0.015),(0.13,0.055,0.045));cylinder_between(p,(-0.2,2.31,-0.01),(-0.32,2.22,-0.005),0.045,0.008,8);cylinder_between(p,(-0.08,2.31,-0.01),(0.03,2.22,-0.005),0.045,0.008,8)
    p=part('Maid_Headband','white');cylinder_between(p,(-0.19,2.31,-0.015),(0.19,2.31,-0.015),0.025,0.025,10)
    p=part('Gold_Brooch','gold');sphere(p,(0,1.53,0.18),(0.045,0.055,0.025),10,8)
    # small boot/garment trim accents
    p=part('Gold_Trim','gold')
    cylinder_between(p,(-0.23,1.2,0),(0.23,1.2,0),0.012,0.012,8)
    return parts

def write_obj(parts, folder, stem):
    mtl=[]; lines=['# JARVIS Character Forge procedural anime character','mtllib '+stem+'.mtl']; offset=1
    for name,color in PALETTE.items(): mtl += [f'newmtl {name}',f'Kd {color[0]} {color[1]} {color[2]}','Ka 0.08 0.08 0.08','Ks 0.25 0.25 0.25','Ns 32','']
    for p in parts:
        lines += [f'o {p.name}',f'usemtl {p.material}']
        lines += [f'v {x:.6f} {y:.6f} {z:.6f}' for x,y,z in p.v]
        lines += [f'f {a+offset} {b+offset} {c+offset}' for a,b,c in p.f]
        offset += len(p.v)
    (folder/(stem+'.obj')).write_text('\n'.join(lines)+'\n');(folder/(stem+'.mtl')).write_text('\n'.join(mtl))

def write_glb(parts, folder, stem):
    blob=bytearray(); views=[]; accessors=[]; meshes=[]; nodes=[]; materials=[]
    def add_view(data, target):
        while len(blob)%4: blob.append(0)
        off=len(blob);blob.extend(data);views.append({'buffer':0,'byteOffset':off,'byteLength':len(data),'target':target});return len(views)-1
    for name,c in PALETTE.items(): materials.append({'name':name,'pbrMetallicRoughness':{'baseColorFactor':list(c),'metallicFactor':0.0,'roughnessFactor':0.72}})
    mat_index={n:i for i,n in enumerate(PALETTE)}
    for p in parts:
        if not p.v or not p.f: continue
        pos=[v for tri in p.f for idx in tri for v in p.v[idx]]
        # duplicate vertices per face for flat-shaded clean procedural surfaces
        packed=struct.pack('<%sf'%len(pos),*pos); vi=add_view(packed,34962)
        count=len(pos)//3
        xs=pos[0::3];ys=pos[1::3];zs=pos[2::3]
        accessors.append({'bufferView':vi,'componentType':5126,'count':count,'type':'VEC3','min':[min(xs),min(ys),min(zs)],'max':[max(xs),max(ys),max(zs)]}); ai=len(accessors)-1
        # Flat face normals; vertices are duplicated per triangle above.
        normals=[]
        for k in range(0, len(pos), 9):
            a=pos[k:k+3]; b=pos[k+3:k+6]; c=pos[k+6:k+9]
            u=(b[0]-a[0],b[1]-a[1],b[2]-a[2]); v=(c[0]-a[0],c[1]-a[1],c[2]-a[2])
            nx=u[1]*v[2]-u[2]*v[1]; ny=u[2]*v[0]-u[0]*v[2]; nz=u[0]*v[1]-u[1]*v[0]
            length=math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0; normal=(nx/length,ny/length,nz/length)
            normals.extend(normal*3)
        ni_view=add_view(struct.pack('<%sf'%len(normals),*normals),34962)
        accessors.append({'bufferView':ni_view,'componentType':5126,'count':count,'type':'VEC3'}); ni=len(accessors)-1
        # sequential indices
        inds=list(range(count)); ib=struct.pack('<%sI'%len(inds),*inds); ii_view=add_view(ib,34963)
        accessors.append({'bufferView':ii_view,'componentType':5125,'count':len(inds),'type':'SCALAR'});ii=len(accessors)-1
        meshes.append({'name':p.name,'primitives':[{'attributes':{'POSITION':ai,'NORMAL':ni},'indices':ii,'material':mat_index[p.material]}]})
        nodes.append({'name':p.name,'mesh':len(meshes)-1})
    doc={'asset':{'version':'2.0','generator':'JARVIS Character Forge Offline'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],'nodes':nodes,'meshes':meshes,'materials':materials,'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors}
    js=json.dumps(doc,separators=(',',':')).encode();
    while len(js)%4:js+=b' '
    while len(blob)%4:blob.append(0)
    total=12+8+len(js)+8+len(blob)
    glb=struct.pack('<III',0x46546C67,2,total)+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(blob),0x004E4942)+blob
    (folder/(stem+'.glb')).write_bytes(glb)

def generate_character(output_dir: Path, character: str='rem-inspired') -> dict:
    output_dir.mkdir(parents=True,exist_ok=True)
    stem='jarvis_rem_character'
    parts=make_character();write_obj(parts,output_dir,stem);write_glb(parts,output_dir,stem)
    report={'name':'Rem-inspired anime maid (procedural original starter)','generator':'JARVIS Character Forge offline procedural v0.1','character':character,'parts':len(parts),'triangles':sum(len(p.f) for p in parts),'files':[stem+'.glb',stem+'.obj',stem+'.mtl'],'limitations':['Stylized blockout, not a production-quality likeness','No UV maps or textures yet','No skeleton/skin weights/animation yet','GLB contains separate named mesh parts and palette materials']}
    (output_dir/(stem+'_report.json')).write_text(json.dumps(report,indent=2))
    return report
