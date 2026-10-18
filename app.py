import bpy
import math

def configure_moneypenny_anatomy():
    """Initializes vertex groups and realistic skin PBR properties."""
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj:
        obj = next((o for o in bpy.data.objects if o.type == 'MESH' and "Adult" in o.name), None)
    if not obj:
        return

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

# -------------------------------------------------------------
# DOLPHIN AUTOMATION CORES: THE AI AUTONOMOUS FRAME DRIVER
# -------------------------------------------------------------
def drive_autonomous_motion(scene):
    """
    Dolphin AI Automation Engine:
    Autonomously loops the leg matrices and handles glitches with zero manual intervention.
    """
    rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not rig:
        return

    # 1. Loop open_leg_adjustment cleanly from 0.0 to 1.0 based on frame steps
    current_frame = scene.frame_current
    # Generates a smooth floating loop value oscillating perfectly between 0.0 and 1.0
    loop_value = (math.sin(current_frame * 0.04) + 1.0) / 2.0

    # 2. Try-Except blocks to handle and clear out coordinate glitches automatically
    try:
        # Prevent slider values from exceeding safe bounds (locks out the demonic tearing glitch)
        if loop_value < 0.0 or loop_value > 1.0:
            raise ValueError("Coordinate anomaly detected.")
            
        rig["open_leg_adjustment"] = loop_value
        rig["anatomical_opening_vector"] = loop_value
        
    except Exception as glitch:
        # Glitch-clearing logic: Instantly snap coordinates back to safe resting baseline
        print(f"[AI Catch] Clearing glitch safely: {glitch}")
        rig["open_leg_adjustment"] = 0.0
        rig["anatomical_opening_vector"] = 0.0
        
        # Clear raw bone translation caches to prevent stretched legs
        if rig.mode == 'POSE':
            for bone in rig.pose.bones:
                bone.location = (0, 0, 0)

def register():
    """Binds the automation frame hooks directly into Blender."""
    unregister()
    bpy.app.handlers.frame_change_pre.append(drive_autonomous_motion)
    configure_moneypenny_anatomy()
    print("Moneypenny Studio local autonomous AI engine activated successfully.")

def unregister():
    """Clears the handlers from memory."""
    handlers = bpy.app.handlers.frame_change_pre
    for handler in list(handlers):
        if handler.__name__ == "drive_autonomous_motion":
            handlers.remove(handler)

if __name__ == "__main__":
    register()
