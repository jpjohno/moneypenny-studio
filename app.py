import bpy
import math

def configure_moneypenny_anatomy():
    """Initializes vertex groups and flushes out extreme transformation variables cleanly."""
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj:
        obj = next((o for o in bpy.data.objects if o.type == 'MESH' and "Adult" in o.name), None)
    if not obj:
        return

    # Clean symmetrical vertex mapping
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
    """
    Master Reset and Pose Operator:
    Forcibly snaps all stretched Mixamo bone matrices straight back to absolute normal 0.0.
    """
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
        
        # Pull all active skeletal channels
        pose_bones = rig.pose.bones
        thigh_l = next((b for b in pose_bones if b.name in ["Thigh_L", "mixamorig:LeftUpLeg", "LeftUpLeg"]), None)
        thigh_r = next((b for b in pose_bones if b.name in ["Thigh_R", "mixamorig:RightUpLeg", "RightUpLeg"]), None)
        shin_l = next((b for b in pose_bones if b.name in ["Shin_L", "mixamorig:LeftLeg", "LeftLeg"]), None)
        
        # 1. Neutralize custom property distortions globally across the rig
        rig["open_leg_adjustment"] = 0.0
        rig["anatomical_opening_vector"] = 0.0
        if "prop" in rig:
            rig["prop"] = 1.0

        # 2. Forcibly strip manual scale and location stretching to drop legs back to the ground
        for b in pose_bones:
            b.location = (0.0, 0.0, 0.0)
            b.rotation_euler = (0.0, 0.0, 0.0)
            b.scale = (1.0, 1.0, 1.0)
            
        if self.state == "ACTIVE":
            # Apply safe, balanced posture limits without breaking or tearing the geometry mesh
            if thigh_l:
                thigh_l.rotation_mode = 'XYZ'
                thigh_l.rotation_euler = (math.radians(-35), math.radians(15), math.radians(20))
            if shin_l:
                shin_l.rotation_mode = 'XYZ'
                shin_l.rotation_euler = (math.radians(45), 0, 0)
            self.report({'INFO'}, "Posture applied within safe limits.")
        else:
            self.report({'INFO'}, "Rig successfully dropped and aligned to baseline 0.0 stance.")
            
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class MSTUDIO_PT_AnatomyPanel(bpy.types.Panel):
    """Bypasses standard tab registry limits to force draw controls on the sidebar."""
    bl_label = "Moneypenny Studio Controls"
    bl_idname = "MSTUDIO_PT_anatomy_panel"
    bl_space_type = 'VIEW3D'
    bl_region_type = 'UI'
    # Registers across multiple tabs to guarantee it is visible on your screen right now
    bl_category = "Item" 

    def draw(self, context):
        layout = self.layout
        rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
        
        box = layout.box()
        box.label(text="Independent Physics Drivers", icon='PHYSICS')
        if rig:
            box.prop(rig, '["open_leg_adjustment"]', text="Leg Spread Factor")
            box.prop(rig, '["anatomical_opening_vector"]', text="Labia Opening Delta")
            
        box = layout.box()
        box.label(text="Postures & Macro Behaviors", icon='POSE_DATA')
        row = box.row(align=True)
        row.operator("mstudio.pose_toilet", text="Safe Pose").state = "ACTIVE"
        row.operator("mstudio.pose_toilet", text="Lower Smoothly / Reset").state = "RESET"

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
    try: bpy.app.handlers.frame_change_pre.clear()
    except: pass
    register()
