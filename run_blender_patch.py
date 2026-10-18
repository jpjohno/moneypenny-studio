import bpy

def force_studio_repair():
    # 1. Target the armature rig safely
    rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not rig:
        print("Error: Rig object not found in memory stack.")
        return
        
    # Set armature active and force select state
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    
    # 2. Flush out frozen transforms and drop the leg back to zero normal position
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    bpy.ops.pose.select_all(action='DESELECT')
    print("Character bones successfully returned to default neutral rest posture.")

    # 3. Explicitly attach the custom property sliders straight to the Rig container
    if "open_leg_adjustment" not in rig:
        rig["open_leg_adjustment"] = 0.0
    if "anatomical_opening_vector" not in rig:
        rig["anatomical_opening_vector"] = 0.0
    print("Custom physics slider values registered cleanly.")

    # 4. Return safely out to normal view mode
    bpy.ops.object.mode_set(mode='OBJECT')

if __name__ == "__main__":
    force_studio_repair()
