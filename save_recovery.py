import bpy
import os

try:
    target_path = os.path.expanduser("~/Desktop/moneypenny-studio/Moneypenny-Adult-Anatomy-Study-v3.blend")
    bpy.ops.wm.save_as_mainfile(filepath=target_path)
    print(f"SUCCESS: Character file securely written to disk folder at {target_path}")
except Exception as e:
    print(f"Save note: {e}")
