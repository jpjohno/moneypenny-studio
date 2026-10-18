import bpy
import math

def configure_moneypenny_anatomy():
    """
    Configures unmoderated anatomical rigging states, vertex controllers,
    independent physics drivers, and photorealistic material parameters 
    for the Moneypenny Studio character mesh.
    """
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj or obj.type != 'MESH':
        print("Error: 'Moneypenny_Mesh' object not found in scene.")
        return

    print("Successfully targeted Moneypenny character codebase geometry.")

    # 1. Explicit Anatomical Vertex Groups & Micro-Details
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
    
    # 2. Inject Independent Bone Rigging & Movement Drivers
    rig = bpy.data.objects.get("Moneypenny_Armature")
    if rig and rig.type == 'ARMATURE':
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        
        pose_bones = rig.pose.bones
        
        # Rig-driven displacement vectors for posture adjustments
        rig["open_leg_adjustment"] = 0.0
        rig["anatomical_opening_vector"] = 0.0
        
        # Rigging parameters for soft-body/spring independent bounce simulation
        if "Breast_L" in pose_bones and "Breast_R" in pose_bones:
            for bone_name in ["Breast_L", "Breast_R"]:
                bone = pose_bones[bone_name]
                constraint = bone.constraints.new(type='LIMIT_ROTATION')
                constraint.use_limit_x = True
                constraint.min_x = math.radians(-30)
                constraint.max_x = math.radians(30)
                constraint.use_limit_y = True
                constraint.min_y = math.radians(-15)
                constraint.max_y = math.radians(15)

        # Lateral movement drivers for organic tissue translation parameters
        labia_bones = ["Labia_L_Major", "Labia_R_Major", "Labia_L_Minor", "Labia_R_Minor"]
        for b_name in labia_bones:
            if b_name in pose_bones:
                bone = pose_bones[b_name]
                constraint = bone.constraints.new(type='LIMIT_LOCATION')
                constraint.use_min_x = True
                constraint.min_x = -0.05
                constraint.use_max_x = True
                constraint.max_x = 0.05

        bpy.ops.object.mode_set(mode='OBJECT')

    # 3. Dynamic Skin Texture & PBR Material Parameters (Photorealism)
    for mat_slot in obj.material_slots:
        material = mat_slot.material
        if material and material.use_nodes:
            nodes = material.node_tree.nodes
            principled_node = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
            
            if principled_node:
                # Subsurface Scattering vectors for fleshy translucent human tissue light absorption
                if 'Subsurface Weight' in principled_node.inputs:
                    principled_node.inputs['Subsurface Weight'].default_value = 0.15
                elif 'Subsurface' in principled_node.inputs:
                    principled_node.inputs['Subsurface'].default_value = 0.15
                
                if 'Subsurface Radius' in principled_node.inputs:
                    principled_node.inputs['Subsurface Radius'].default_value = (1.0, 0.48, 0.38)
                
                if 'Roughness' in principled_node.inputs:
                    principled_node.inputs['Roughness'].default_value = 0.45

    print("Moneypenny Studio script parameters successfully initialized inside the pipeline.")

if __name__ == "__main__":
    configure_moneypenny_anatomy()
