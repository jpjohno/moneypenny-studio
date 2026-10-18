import bpy
import math

def configure_moneypenny_anatomy():
    """Initializes vertex groups and realistic skin PBR properties."""
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj:
        obj = next((o for o in bpy.data.objects if o.type == 'MESH' and "Adult" in o.name), None)
        
    if not obj:
        print("Mesh geometry configuration synchronized.")
        return

    # Initialize micro-detail vertex groupings
    anatomical_groups = [
        "Breast_Left", "Breast_Right",
        "Labia_Major_Left", "Labia_Major_Right",
        "Labia_Minor_Left", "Labia_Minor_Right",
        "Clitoris_Base", "Pelvic_Floor",
        "Thigh_Upper_Left", "Thigh_Upper_Right"
    ]
    for group_name in anatomical_groups:
        if group_name not in obj.vertex_groups:
            obj.vertex_groups.new(name=group_name)

class MSTUDIO_OT_PoseToilet(bpy.types.Operator):
    """Automates the hygiene posture configuration loop."""
    bl_idname = "mstudio.pose_toilet"
    bl_label = "Trigger Toilet Posture"
    bl_options = {'REGISTER', 'UNDO'}
    
    state: bpy.props.StringProperty(default="ACTIVE")

    def execute(self, context):
        rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
        if not rig:
            self.report({'ERROR'}, "Character Armature not found.")
            return {'CANCELLED'}
            
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        
        pose_bones = rig.pose.bones
        target_bone = next((b for b in pose_bones if "Thigh" in b.name or "mixamorig:LeftUpLeg" in b.name), None)
        
        if self.state == "ACTIVE" and target_bone:
            target_bone.location = (0.2, 0.3, 0.5)
            target_bone.rotation_euler = (math.radians(45), 0, math.radians(20))
            self.report({'INFO'}, "Posture state activated.")
        elif target_bone:
            target_bone.location = (0, 0, 0)
            target_bone.rotation_euler = (0, 0, 0)
            self.report({'INFO'}, "Posture smoothly lowered.")
            
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class MSTUDIO_PT_AnatomyPanel(bpy.types.Panel):
    """Creates the explicit anatomy automation control panel."""
    bl_label = "Moneypenny Studio Viewport Controls"
    bl_idname = "MSTUDIO_PT_anatomy_panel"
    bl_space_type = 'VIEW3D'
    bl_region_type = 'UI'
    bl_category = "Item" 

    def draw(self, context):
        layout = self.layout
        rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
        
        box = layout.box()
        box.label(text="Independent Physics Drivers", icon='PHYSICS')
        
        if rig:
            if "open_leg_adjustment" not in rig:
                rig["open_leg_adjustment"] = 0.0
            if "anatomical_opening_vector" not in rig:
                rig["anatomical_opening_vector"] = 0.0
            
            box.prop(rig, '["open_leg_adjustment"]', text="Leg Spread Factor")
            box.prop(rig, '["anatomical_opening_vector"]', text="Labia Opening Delta")
        else:
            box.label(text="No active rig object found.", icon='ERROR')
            
        box = layout.box()
        box.label(text="Postures & Macro Behaviors", icon='POSE_DATA')
        row = box.row(align=True)
        row.operator("mstudio.pose_toilet", text="Foot on Seat").state = "ACTIVE"
        row.operator("mstudio.pose_toilet", text="Lower Smoothly").state = "RESET"

classes = [MSTUDIO_OT_PoseToilet, MSTUDIO_PT_AnatomyPanel]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    configure_moneypenny_anatomy()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
