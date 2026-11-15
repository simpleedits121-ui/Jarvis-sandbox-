from __future__ import annotations
import json, math, time, uuid
from pathlib import Path
from typing import Any

ALLOWED={"cube","sphere","cylinder","capsule","plane"}

class SpatialEngine:
    """Local editable scene graph and bounded construction-worker runtime."""
    def __init__(self, workspace: Path):
        self.root=(workspace/"spatial").resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.scene_path=self.root/"scene.json"
        self.log_path=self.root/"construction.json"
        self.scene=self._load(self.scene_path, {"scene_id":"main","objects":[],"version":1})
        self.log=self._load(self.log_path, {"events":[]})
    def _load(self,p,default):
        try:
            v=json.loads(p.read_text())
            return v if isinstance(v,dict) else default
        except (OSError,ValueError): return default
    def _save(self):
        for p,v in ((self.scene_path,self.scene),(self.log_path,self.log)):
            tmp=p.with_suffix(".tmp"); tmp.write_text(json.dumps(v,indent=2)); tmp.replace(p)
    def snapshot(self):
        return {"scene":self.scene,"recent_events":self.log["events"][-80:],
                "engine":"local_spatial_v1","neural_inference":False}
    def _event(self,worker,action,detail,obj=None):
        self.log["events"].append({"id":str(uuid.uuid4()),"time":time.time(),"worker":worker,
            "action":action,"detail":detail,"object_id":obj,"state":"completed"})
        self.log["events"]=self.log["events"][-500:]
    def operation(self,op:dict[str,Any]):
        kind=op.get("operation")
        if kind=="create_primitive":
            typ=op.get("type","")
            if typ not in ALLOWED: raise ValueError("Unsupported primitive")
            name=str(op.get("name","Object"))[:64]
            params=op.get("parameters",{})
            scale=params.get("radius",[1,1,1]) if typ=="sphere" else params.get("size",[1,1,1])
            if not isinstance(scale,list) or len(scale)!=3: scale=[1,1,1]
            obj={"id":str(uuid.uuid4()),"name":name,"type":typ,
                 "transform":op.get("transform",{"position":[0,0,0],"rotation":[0,0,0]}),
                 "scale":[max(.001,min(100,abs(float(x)))) for x in scale],
                 "material":{"base_color":[0.65,0.72,0.82,1],"roughness":0.7},
                 "region":op.get("region","general"),"parent":op.get("parent")}
            self.scene["objects"].append(obj); self._event(op.get("worker","builder"),"place",f"Placed {typ} {name}",obj["id"])
            self._save(); return obj
        if kind in ("transform","assign_material","rename","delete"):
            oid=op.get("object_id")
            obj=next((x for x in self.scene["objects"] if x["id"]==oid),None)
            if not obj: raise ValueError("Object not found")
            if kind=="transform":
                tr=op.get("transform",{})
                for key in ("position","rotation"):
                    if key in tr and (not isinstance(tr[key],list) or len(tr[key])!=3): raise ValueError("Invalid transform")
                obj["transform"].update(tr)
            elif kind=="assign_material":
                mat=op.get("material",{})
                color=mat.get("base_color",[.7,.7,.7,1])
                if not isinstance(color,list) or len(color) not in (3,4): raise ValueError("Invalid color")
                obj["material"]={"base_color":color,"roughness":max(0,min(1,float(mat.get("roughness",.7))))}
            elif kind=="rename": obj["name"]=str(op.get("name","Object"))[:64]
            else: self.scene["objects"].remove(obj)
            self._event(op.get("worker","builder"),kind,f"{kind} {obj['name']}",oid); self._save(); return obj
        raise ValueError("Unknown operation")
    def build_demo(self,goal:str):
        """Build a visible, editable blockout using human-like staged workers."""
        stages=[
          ("surveyor","Mapped reference proportions and reserved construction regions."),
          ("structural_builder","Placed torso, head, pelvis and limb foundation components."),
          ("skin_workers","Added local surface-form components to face and body regions."),
          ("detail_workers","Placed eye, nose, hair and accessory guide components."),
          ("inspector","Checked object names, transforms and scene integrity.")
        ]
        made=[]
        specs=[
          ("Torso","capsule",[0,1.35,0],[.34,.55,.22],"structure"),
          ("Head","sphere",[0,2.12,0],[.29,.36,.27],"head"),
          ("Pelvis","capsule",[0,.85,0],[.30,.22,.20],"structure"),
          ("LeftArm","capsule",[-.48,1.38,0],[.13,.43,.13],"limb"),
          ("RightArm","capsule",[.48,1.38,0],[.13,.43,.13],"limb"),
          ("LeftLeg","capsule",[-.17,.35,0],[.15,.43,.16],"limb"),
          ("RightLeg","capsule",[.17,.35,0],[.15,.43,.16],"limb"),
          ("EyeGuideL","sphere",[-.11,2.18,.23],[.055,.075,.035],"face_detail"),
          ("EyeGuideR","sphere",[.11,2.18,.23],[.055,.075,.035],"face_detail")
        ]
        for worker,detail in stages:
            self._event(worker,"inspect" if worker in ("surveyor","inspector") else "construct",detail)
            if worker=="structural_builder":
                for n,t,pos,sc,reg in specs[:7]:
                    made.append(self.operation({"operation":"create_primitive","type":t,"name":n,
                       "parameters":{"size":sc},"transform":{"position":pos,"rotation":[0,0,0]},"region":reg,"worker":worker}))
            if worker=="detail_workers":
                for n,t,pos,sc,reg in specs[7:]:
                    made.append(self.operation({"operation":"create_primitive","type":t,"name":n,
                       "parameters":{"radius":sc},"transform":{"position":pos,"rotation":[0,0,0]},"region":reg,"worker":worker}))
        return {"created":len(made),"objects":made,"events":self.log["events"][-len(stages):],
                "note":"Editable low-cost blockout; not a finished anatomical character or neural reconstruction."}
