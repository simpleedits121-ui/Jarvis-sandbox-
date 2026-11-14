"""Lightweight CPU-first JARVIS production workers.

These are deterministic tool workers, not separate heavyweight neural models.
They create a scene specification, Blender Python build script and OBJ preview.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

MATERIALS = {
    "midnight": [0.035, 0.075, 0.12, 1.0],
    "wall": [0.12, 0.19, 0.27, 1.0],
    "floor": [0.045, 0.065, 0.085, 1.0],
    "cyan": [0.02, 0.55, 0.78, 1.0],
    "white": [0.78, 0.86, 0.92, 1.0],
    "wood": [0.30, 0.16, 0.075, 1.0],
    "black": [0.012, 0.018, 0.028, 1.0],
    "green": [0.055, 0.32, 0.16, 1.0],
    "gold": [0.75, 0.42, 0.08, 1.0],
    "pink": [0.75, 0.16, 0.34, 1.0],
}


def _obj(name: str, kind: str, loc: tuple[float, float, float], scale: tuple[float, float, float], material: str) -> dict[str, Any]:
    return {"name": name, "kind": kind, "location": list(loc), "scale": list(scale), "material": material}


class GeometryWorker:
    def build(self, description: str) -> list[dict[str, Any]]:
        d = description.lower()
        is_lab = any(k in d for k in ("lab", "laboratory", "studio", "workshop"))
        room_label = "Laboratory" if is_lab else "Creative Room"
        items = [
            _obj("Room_Floor", "cube", (0, 0, -0.16), (6.0, 5.0, 0.16), "floor"),
            _obj("Back_Wall", "cube", (0, 2.45, 1.8), (6.0, 0.12, 1.8), "wall"),
            _obj("Left_Wall", "cube", (-2.95, 0, 1.8), (0.12, 5.0, 1.8), "wall"),
            _obj("Desk_Top", "cube", (0.1, -0.25, 1.0), (2.2, 0.85, 0.10), "wood"),
            _obj("Desk_Leg_L", "cube", (-1.75, -0.25, 0.48), (0.09, 0.72, 0.48), "black"),
            _obj("Desk_Leg_R", "cube", (1.95, -0.25, 0.48), (0.09, 0.72, 0.48), "black"),
            _obj("Monitor_Body", "cube", (0.15, 0.28, 1.58), (0.78, 0.08, 0.48), "black"),
            _obj("Monitor_Screen", "cube", (0.15, 0.185, 1.59), (0.69, 0.012, 0.39), "cyan"),
            _obj("Monitor_Stand", "cylinder", (0.15, 0.28, 1.12), (0.07, 0.07, 0.23), "black"),
            _obj("Keyboard", "cube", (0.15, -0.82, 1.13), (0.62, 0.22, 0.035), "white"),
            _obj("Chair_Seat", "cube", (0.1, -2.0, 0.72), (0.62, 0.58, 0.12), "black"),
            _obj("Chair_Back", "cube", (0.1, -2.48, 1.25), (0.62, 0.10, 0.55), "black"),
            _obj("Window_Glow", "cube", (-1.95, 2.30, 2.0), (0.72, 0.025, 0.72), "cyan"),
            _obj("Shelf", "cube", (2.25, 1.65, 1.25), (0.45, 0.35, 0.08), "wood"),
            _obj("Shelf_Books", "cube", (2.25, 1.62, 1.52), (0.34, 0.22, 0.18), "gold"),
            _obj("Plant_Pot", "cylinder", (-2.35, -1.75, 0.28), (0.24, 0.24, 0.28), "gold"),
            _obj("Plant_Crown", "sphere", (-2.35, -1.75, 0.85), (0.38, 0.38, 0.48), "green"),
            _obj("Ceiling_Light", "cube", (0, 0.5, 3.35), (1.15, 0.18, 0.035), "white"),
        ]
        # A simple mannequin placeholder is intentionally labelled as a placeholder;
        # it is not a photorealistic reconstruction or a rigged human.
        if any(k in d for k in ("character", "person", "selfie", "human", "myself")):
            items += [
                _obj("Character_Placeholder_Torso", "cube", (-1.1, -0.6, 1.0), (0.28, 0.18, 0.42), "pink"),
                _obj("Character_Placeholder_Head", "sphere", (-1.1, -0.6, 1.58), (0.22, 0.22, 0.25), "white"),
                _obj("Character_Placeholder_Leg_L", "cylinder", (-1.25, -0.6, 0.38), (0.09, 0.09, 0.34), "black"),
                _obj("Character_Placeholder_Leg_R", "cylinder", (-0.95, -0.6, 0.38), (0.09, 0.09, 0.34), "black"),
            ]
        return items


class MaterialWorker:
    def assign(self, objects: list[dict[str, Any]]) -> dict[str, list[float]]:
        used = {o["material"] for o in objects}
        return {name: MATERIALS[name] for name in sorted(used) if name in MATERIALS}


class WorldWorker:
    def build(self, description: str) -> dict[str, Any]:
        return {"name": "JARVIS Procedural Room", "description": description[:500],
                "dimensions": [6.0, 5.0, 3.6], "units": "meters", "style": "stylized cinematic sci-fi"}


class CinematographyWorker:
    def build(self) -> dict[str, Any]:
        return {"camera_location_start": [7.5, -9.0, 6.0], "camera_location_end": [5.8, -7.0, 4.8],
                "look_at": [0.0, 0.0, 1.0], "lens_mm": 42, "frames": [1, 120], "fps": 24,
                "resolution": [1280, 720]}


class QualityWorker:
    def inspect(self, objects: list[dict[str, Any]]) -> list[str]:
        issues = []
        names = [o["name"] for o in objects]
        if len(names) != len(set(names)):
            issues.append("Duplicate object names detected")
        for obj in objects:
            if any(not math.isfinite(float(v)) for v in obj["location"] + obj["scale"]):
                issues.append(f"Non-finite transform in {obj['name']}")
            if any(float(v) <= 0 for v in obj["scale"]):
                issues.append(f"Non-positive dimensions in {obj['name']}")
        return issues


def make_blender_script(spec: dict[str, Any]) -> str:
    spec_json = json.dumps(spec, separators=(",", ":"))
    return r'''# Generated by JARVIS CPU-first worker team. No arbitrary model code is executed.
import bpy, json, math, os
from mathutils import Vector
SPEC = json.loads(''' + repr(spec_json) + r''')

# Reset the current scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

materials = {}
for name, color in SPEC["materials"].items():
    mat = bpy.data.materials.new(name="JARVIS_" + name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.48
        if name == "cyan":
            bsdf.inputs["Emission Color"].default_value = color
            bsdf.inputs["Emission Strength"].default_value = 0.35
    materials[name] = mat

def apply_material(obj, name):
    if name in materials:
        obj.data.materials.append(materials[name])

def add_item(item):
    kind = item["kind"]
    loc = item["location"]
    scale = item["scale"]
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc)
    elif kind == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1, depth=2, location=loc)
    else:
        bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    obj = bpy.context.object
    obj.name = item["name"]
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_material(obj, item["material"])
    if kind in ("sphere", "cylinder"):
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj

for item in SPEC["objects"]:
    add_item(item)

# Soft cinematic lighting.
def point_light(name, location, power, color, size):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.radians(25), 0, math.radians(25))
    return obj

point_light("JARVIS_Key_Light", (1.0, -3.0, 5.5), 850, (0.62, 0.82, 1.0), 5.0)
point_light("JARVIS_Rim_Light", (-3.0, 2.0, 4.0), 650, (0.08, 0.55, 1.0), 3.0)
point_light("JARVIS_Fill_Light", (4.0, 1.0, 3.0), 350, (1.0, 0.55, 0.25), 2.5)

cam_data = bpy.data.cameras.new("JARVIS_Cinematic_Camera")
cam = bpy.data.objects.new("JARVIS_Cinematic_Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.data.lens = SPEC["camera"]["lens_mm"]
scene = bpy.context.scene
scene.camera = cam
look_at = Vector(SPEC["camera"]["look_at"])
for frame, location in zip(SPEC["camera"]["frames"], [SPEC["camera"]["camera_location_start"], SPEC["camera"]["camera_location_end"]]):
    cam.location = location
    direction = look_at - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)

scene.frame_start, scene.frame_end = SPEC["camera"]["frames"]
scene.render.fps = SPEC["camera"]["fps"]
scene.render.resolution_x, scene.render.resolution_y = SPEC["camera"]["resolution"]
scene.render.resolution_percentage = 70
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"
scene.world.color = (0.025, 0.035, 0.06)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(os.path.dirname(__file__), "render_")
scene.frame_set(1)
# Save beside this script. Rendering is a separate explicit operation.
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(__file__), "jarvis_scene.blend"))
print("JARVIS scene built:", SPEC["world"]["name"])
'''


def make_obj(objects: list[dict[str, Any]]) -> str:
    lines = ["# JARVIS CPU preview OBJ", "mtllib scene_preview.mtl"]
    vertex_index = 1
    for item in objects:
        x, y, z = item["location"]
        sx, sy, sz = item["scale"]
        verts = [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),
                 (-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]
        lines.append("o " + re.sub(r"[^A-Za-z0-9_]", "_", item["name"]))
        lines.append("usemtl " + item["material"])
        for vx, vy, vz in verts:
            lines.append(f"v {x+vx:.5f} {y+vy:.5f} {z+vz:.5f}")
        faces = [(1,2,3,4),(5,8,7,6),(1,5,6,2),(2,6,7,3),(3,7,8,4),(5,1,4,8)]
        for face in faces:
            lines.append("f " + " ".join(str(vertex_index + n - 1) for n in face))
        vertex_index += 8
    return "\n".join(lines) + "\n"


def make_mtl(materials: dict[str, list[float]]) -> str:
    lines = ["# JARVIS preview materials"]
    for name, rgba in materials.items():
        r, g, b = rgba[:3]
        lines += [f"newmtl {name}", f"Kd {r:.4f} {g:.4f} {b:.4f}", "Ka 0.05 0.05 0.05", "Ks 0.15 0.15 0.15", "Ns 32", ""]
    return "\n".join(lines)


def build_scene_project(root: Path, name: str, description: str) -> dict[str, Any]:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:48] or "scene"
    project = root / safe
    suffix = 2
    while project.exists():
        project = root / f"{safe}_{suffix}"
        suffix += 1
    project.mkdir(parents=True, exist_ok=False)

    geometry = GeometryWorker()
    material = MaterialWorker()
    world = WorldWorker()
    cinematography = CinematographyWorker()
    quality = QualityWorker()
    objects = geometry.build(description)
    mats = material.assign(objects)
    issues = quality.inspect(objects)
    spec = {"world": world.build(description), "objects": objects, "materials": mats,
            "camera": cinematography.build(), "quality_issues": issues,
            "workers": ["Geometry Worker", "Material Worker", "World Worker", "Cinematography Worker", "Animation Worker", "Quality Worker"]}
    (project / "scene_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    (project / "scene.py").write_text(make_blender_script(spec), encoding="utf-8")
    (project / "scene_preview.obj").write_text(make_obj(objects), encoding="utf-8")
    (project / "scene_preview.mtl").write_text(make_mtl(mats), encoding="utf-8")
    (project / "README.md").write_text(
        "# JARVIS generated scene\n\n" + description +
        "\n\n## Files\n- `scene_preview.obj`: CPU-generated geometry preview; import into Blender.\n- `scene_preview.mtl`: preview materials.\n- `scene.py`: deterministic Blender build script; run from Blender's Scripting workspace where supported.\n- `scene_spec.json`: worker plan and scene data.\n\nThe current local worker creates a procedural room and a labelled mannequin placeholder when a person/character is requested. It does not reconstruct a real person from a photo, create a production rig, or render a final cinematic automatically.\n",
        encoding="utf-8")
    return {"project": project.name, "path": str(project), "files": ["scene_spec.json", "scene.py", "scene_preview.obj", "scene_preview.mtl", "README.md"],
            "object_count": len(objects), "quality_issues": issues, "workers": spec["workers"]}
