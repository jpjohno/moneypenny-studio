import bpy
import math

# -------------------------------------------------------------
# 1. CORE PIPELINE: ANATOMICAL CONFIGURATION
# -------------------------------------------------------------
def configure_moneypenny_anatomy():
    """Initializes vertex groups and realistic skin PBR properties."""
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj or obj.type != 'MESH':
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
    
    # Configure translucent subsurface scattering skin values
    for mat_slot in obj.material_slots:
        material = mat_slot.material
        if material and material.use_nodes:
            nodes = material.node_tree.nodes
            principled_node = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled_node:
                if 'Subsurface Weight' in principled_node.inputs:
                    principled_node.inputs['Subsurface Weight'].default_value = 0.15
                elif 'Subsurface' in principled_node.inputs:
                    principled_node.inputs['Subsurface'].default_value = 0.15
                if 'Subsurface Radius' in principled_node.inputs:
                    principled_node.inputs['Subsurface Radius'].default_value = (1.0, 0.48, 0.38)
                if 'Roughness' in principled_node.inputs:
                    principled_node.inputs['Roughness'].default_value = 0.45

# -------------------------------------------------------------
# 2. OPERATORS: AUTOMATED RIGGING MOVEMENT ENGINES
# -------------------------------------------------------------
class MSTUDIO_OT_PoseToilet(bpy.types.Operator):
    """Automates the hygiene posture configuration loop."""
    bl_idname = "mstudio.pose_toilet"
    bl_label = "Trigger Toilet Posture"
    bl_options = {'REGISTER', 'UNDO'}
    
    state: bpy.props.StringProperty(default="ACTIVE")

    def execute(self, context):
        rig = bpy.data.objects.get("Moneypenny_Armature")
        if not rig or rig.type != 'ARMATURE':
            self.report({'ERROR'}, "Moneypenny_Armature not found.")
            return {'CANCELLED'}
            
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        
        # Drive leg transform limits organically
        if self.state == "ACTIVE":
            if "Thigh_L" in rig.pose.bones:
                rig.pose.bones["Thigh_L"].location = (0.2, 0.3, 0.5)
                rig.pose.bones["Thigh_L"].rotation_euler = (math.radians(45), 0, math.radians(20))
            self.report({'INFO'}, "Hygiene posture state activated.")
        else:
            if "Thigh_L" in rig.pose.bones:
                rig.pose.bones["Thigh_L"].location = (0, 0, 0)
                rig.pose.bones["Thigh_L"].rotation_euler = (0, 0, 0)
            self.report({'INFO'}, "Posture smoothly lowered and reset.")
            
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

# -------------------------------------------------------------
# 3. INTERFACE: BLENDER VIEWPORT UI PANEL
# -------------------------------------------------------------
class MSTUDIO_PT_AnatomyPanel(bpy.types.Panel):
    """Creates the explicit anatomy automation control panel."""
    bl_label = "Moneypenny Studio Control Panel"
    bl_idname = "MSTUDIO_PT_anatomy_panel"
    bl_space_type = 'VIEW3D'
    bl_region_type = 'UI'
    bl_category = "Moneypenny Studio"

    def draw(self, context):
        layout = self.layout
        rig = bpy.data.objects.get("Moneypenny_Armature")
        
        # Section A: Tissue Elasticity & Physics Controls
        box = layout.box()
        box.label(text="Independent Physics Drivers", icon='PHYSICS')
        if rig:
            box.prop(rig, '["open_leg_adjustment"]', text="Leg Spread Factor")
            box.prop(rig, '["anatomical_opening_vector"]', text="Labia Opening Delta")
        else:
            box.label(text="Armature offline.", icon='ERROR')
            
        # Section B: Automated Animation Macro Routines
        box = layout.box()
        box.label(text="Postures & Macro Behaviors", icon='POSE_DATA')
        row = box.row(align=True)
        row.operator("mstudio.pose_toilet", text="Foot on Seat").state = "ACTIVE"
        row.operator("mstudio.pose_toilet", text="Lower Smoothly").state = "RESET"

# -------------------------------------------------------------
# 4. ENGINE REGISTRATION REGISTRY
# -------------------------------------------------------------
classes = [MSTUDIO_OT_PoseToilet, MSTUDIO_PT_AnatomyPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    configure_moneypenny_anatomy()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
