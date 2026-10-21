"""Disposable Blender integration test. Run with --background --factory-startup.

Uses synthetic general-purpose rigs, never opens or saves a character source.
"""
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('studio_controls', ROOT / 'scripts/character/studio_controls.py')
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)
controls.register()
controls.register()  # Reloading the script must not leave duplicate panels.


def make_rig(name):
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    rig.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    root = rig.data.edit_bones[0]
    root.name = 'Hips'
    root.head, root.tail = (0, 0, .9), (0, 0, 1)
    for name, head, tail in [('Spine', (0, 0, 1), (0, 0, 1.4)),
                             ('LeftUpLeg', (.12, 0, .9), (.12, 0, .5)),
                             ('RightUpLeg', (-.12, 0, .9), (-.12, 0, .5))]:
        bone = rig.data.edit_bones.new(name)
        bone.head, bone.tail, bone.parent = head, tail, root
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


other = make_rig('Unrelated rig')
rig = make_rig('Selected studio rig')
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 25
scene.render.fps = 24
assert controls.selected_rig(bpy.context) == rig
before_other = controls.snapshot(other)
bone = rig.pose.bones['Spine']
bone.rotation_mode = 'QUATERNION'
bone.rotation_quaternion = Quaternion((0, 0, 1), .6)
bpy.context.view_layer.update()
assert bpy.ops.mstudio.capture_pose() == {'FINISHED'}
target = json.loads(rig[controls.POSE_KEY])
bone.rotation_quaternion = Quaternion()
bpy.context.view_layer.update()
old = bpy.data.actions.new('Keep original action')
rig.animation_data_create()
rig.animation_data.action = old
assert bpy.ops.mstudio.transition_pose() == {'FINISHED'}
assert old.use_fake_user and old.name in bpy.data.actions
assert rig.animation_data.action != old
for frame, angle in [(1, 0), (13, .3), (25, .6)]:
    scene.frame_set(frame)
    assert abs(bone.rotation_quaternion.angle - angle) < 1e-5, (frame, bone.rotation_quaternion.angle)
assert controls.snapshot(other) == before_other
saved_action = rig.animation_data.action
rig.pose.bones['Spine'].constraints.new('COPY_ROTATION')
try:
    controls.transition(bpy.context, rig, target, 24)
    raise AssertionError('Constrained rigs must not be silently re-keyed')
except ValueError:
    pass
for constraint in list(rig.pose.bones['Spine'].constraints):
    rig.pose.bones['Spine'].constraints.remove(constraint)
assert rig.animation_data.action == saved_action
selected = list(bpy.context.selected_objects)
objects = set(bpy.data.objects)
meshes = set(bpy.data.meshes)
scene.frame_set(13)
output = Path(sys.argv[sys.argv.index('--') + 1])
controls.export_motion(bpy.context, rig, output)
assert set(bpy.data.objects) == objects and set(bpy.data.meshes) == meshes
assert set(bpy.context.selected_objects) == set(selected)
assert bpy.context.active_object == rig and scene.frame_current == 13
assert rig.animation_data.action == saved_action
assert controls.snapshot(other) == before_other
scene.frame_end = 2000
try:
    controls.export_motion(bpy.context, rig, output)
    raise AssertionError('Oversized exports must fail')
except ValueError:
    pass
controls.unregister()
print('STUDIO_CONTROLS_VERIFIED', output)
