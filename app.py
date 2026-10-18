import bpy
import math

def configure_moneypenny_anatomy():
    """Initializes vertex groups cleanly inside the mesh configuration tree."""
    obj = bpy.data.objects.get("Moneypenny_Mesh")
    if not obj:
        obj = next((o for o in bpy.data.objects if o.type == 'MESH' and "Adult" in o.name), None)
    if not obj:
        return

    # Symmetrical vertex targets array
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
# AUTOMATED TIMELINE OVERRIDE: THE AI AUTONOMOUS DRIVER LOOP
# -------------------------------------------------------------
def drive_autonomous_motion(scene):
    """
    Dolphin AI Automation Core:
    Bypasses UI selection locks to drive bone channels smoothly based on frame steps.
    """
    rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not rig:
        return

    current_frame = scene.frame_current
    # Generates a smooth, continuous loop value oscillating between 0.0 and 1.0
    loop_value = (math.sin(current_frame * 0.04) + 1.0) / 2.0

    # Explicitly lock custom properties to the timeline loop state
    rig["open_leg_adjustment"] = loop_value
    rig["anatomical_opening_vector"] = loop_value

    # Target the inner skeleton bones directly to prevent mesh scale tearing
    pose_bones = rig.pose.bones
    thigh_l = next((b for b in pose_bones if b.name in ["Thigh_L", "mixamorig:LeftUpLeg", "LeftUpLeg"]), None)
    thigh_r = next((b for b in pose_bones if b.name in ["Thigh_R", "mixamorig:RightUpLeg", "RightUpLeg"]), None)

    # Force raw bone scales back to 1.0 automatically to prevent distortions
    for b in pose_bones:
        b.scale = (1.0, 1.0, 1.0)

    try:
        # Drive symmetrical leg rotation spreads smoothly entirely through code loops
        if thigh_l:
            thigh_l.rotation_mode = 'XYZ'
            thigh_l.rotation_euler = (0, 0, math.radians(25 * loop_value))
        if thigh_r:
            thigh_r.rotation_mode = 'XYZ'
            thigh_r.rotation_euler = (0, 0, math.radians(-25 * loop_value))
    except Exception as glitch:
        print(f"Clearing tracking anomaly safely: {glitch}")

def register():
    """Binds the automation frame hooks directly into Blender."""
    unregister()
    bpy.app.handlers.frame_change_pre.append(drive_autonomous_motion)
    configure_moneypenny_anatomy()
    print("Moneypenny Studio local autonomous AI engine activated successfully.")

def unregister():
    """Clears the frame handlers cleanly from running memory blocks."""
    handlers = bpy.app.handlers.frame_change_pre
    for handler in list(handlers):
        if handler.__name__ == "drive_autonomous_motion":
            handlers.remove(handler)

if __name__ == "__main__":
    register()
