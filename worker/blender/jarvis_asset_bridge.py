bl_info = {
    "name": "JARVIS Sandbox Asset Bridge",
    "author": "JARVIS Sandbox",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "category": "Import-Export",
    "description": "Import/export GLB assets for the JARVIS Sandbox workflow",
}

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator, Panel, AddonPreferences

class JARVIS_OT_import_latest_glb(Operator):
    bl_idname = "jarvis.import_glb"
    bl_label = "Import GLB Asset"
    filepath: StringProperty(subtype="FILE_PATH")
    def execute(self, context):
        if not self.filepath.lower().endswith(".glb"):
            self.report({"ERROR"}, "Choose a .glb file")
            return {"CANCELLED"}
        bpy.ops.import_scene.gltf(filepath=self.filepath)
        return {"FINISHED"}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

class JARVIS_OT_export_glb(Operator):
    bl_idname = "jarvis.export_glb"
    bl_label = "Export Selected as GLB"
    filepath: StringProperty(subtype="FILE_PATH", default="//jarvis_asset.glb")
    def execute(self, context):
        bpy.ops.export_scene.gltf(filepath=self.filepath, export_format="GLB", use_selection=True)
        return {"FINISHED"}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

class JARVIS_PT_asset_bridge(Panel):
    bl_label = "JARVIS Sandbox"
    bl_idname = "JARVIS_PT_asset_bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "JARVIS"
    def draw(self, context):
        layout = self.layout
        layout.operator("jarvis.import_glb", icon="IMPORT")
        layout.operator("jarvis.export_glb", icon="EXPORT")
        layout.label(text="Transfer GLB files via Sandbox workspace")

classes = (JARVIS_OT_import_latest_glb, JARVIS_OT_export_glb, JARVIS_PT_asset_bridge)
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
if __name__ == "__main__":
    register()
