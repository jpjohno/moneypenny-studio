import bpy
import math

def configure_moneypenny_anatomy():
    """Initializes vertex groups and realistic skin PBR properties cleanly."""
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj:
        obj = next((o for o in bpy.data.objects if o.type == 'MESH' and "Adult" in o.name), None)
    if not obj:
        return

    # Symmetrical structural definitions for the layout tree
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
    """Controls character posture variables cleanly without scaling or tearing geometry."""
    bl_idname = "mstudio.pose_toilet"
    bl_label = "Trigger Toilet Posture"
    bl_options = {'REGISTER', 'UNDO'}
    
    state: bpy.props.StringProperty(default="ACTIVE")

    def execute(self, context):
        rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
        if not rig:
            return {'CANCELLED'}
            
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        
        pose_bones = rig.pose.bones
        thigh_bone = next((b for b in pose_bones if b.name in ["Thigh_L", "mixamorig:LeftUpLeg", "LeftUpLeg"]), None)
        shin_bone = next((b for b in pose_bones if b.name in ["Shin_L", "mixamorig:LeftLeg", "LeftLeg"]), None)
        foot_bone = next((b for b in pose_bones if b.name in ["Foot_L", "mixamorig:LeftFoot", "LeftFoot"]), None)
        
        # Ensure all bone scale parameters are strictly locked to normal 1.0 to prevent disappearing parts
        for b in pose_bones:
            b.scale = (1.0, 1.0, 1.0)
            
        if self.state == "ACTIVE":
            if thigh_bone:
                thigh_bone.rotation_mode = 'XYZ'
                thigh_bone.rotation_euler = (math.radians(-35), math.radians(15), math.radians(20))
            if shin_bone:
                shin_bone.rotation_mode = 'XYZ'
                shin_bone.rotation_euler = (math.radians(45), 0, 0)
        else:
            # Drop everything straight back to a solid balanced neutral standing stance
            for bone in [thigh_bone, shin_bone, foot_bone]:
                if bone:
                    bone.location = (0, 0, 0)
                    bone.rotation_euler = (0, 0, 0)
            
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
            
        box = layout.box()
        box.label(text="Postures & Macro Behaviors", icon='POSE_DATA')
        row = box.row(align=True)
        row.operator("mstudio.pose_toilet", text="Foot on Seat").state = "ACTIVE"
        row.operator("mstudio.pose_toilet", text="Lower Smoothly").state = "RESET"

classes = [MSTUDIO_OT_PoseToilet, MSTUDIO_PT_AnatomyPanel]

def register():
    for cls in classes:
        try: bpy.utils.register_class(cls)
        except: pass
    configure_moneypenny_anatomy()

def unregister():
    for cls in reversed(classes):
        try: bpy.utils.unregister_class(cls)
        except: pass

if __name__ == "__main__":
    # Clear any active glitchy background frame loop handlers completely
    try:
        bpy.app.handlers.frame_change_pre.clear()
    except:
        pass
    register()
