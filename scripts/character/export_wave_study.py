"""Bake a small self-authored IK wave from the local source workshop to GLB.
Run with Blender loading the workshop, then --python this script -- studio_root.
Does not overwrite the editable workshop or use a third-party motion library.
"""
import bpy
import sys
from pathlib import Path
from mathutils import Quaternion
ROOT=Path(sys.argv[sys.argv.index('--')+1]).resolve()
arm=bpy.data.objects['Moneypenny_Performance_Rig'];control=bpy.data.objects['CTRL_RightHand']
ik=arm.pose.bones['RightForeArm'].constraints['Studio RightHand IK'];ik.influence=1
start=control.location.copy()
for frame,position in [(1,start),(25,(-.40,-.10,1.45)),(40,(-.48,-.10,1.48)),(52,(-.36,-.10,1.45)),(75,start)]:
    control.location=position;control.keyframe_insert('location',frame=frame)
arm.animation_data_create();arm.animation_data.action=bpy.data.actions.new('Studio wave')
hand=arm.pose.bones['RightHand'];hand.rotation_mode='QUATERNION'
for frame,angle in [(1,0),(25,.12),(40,-.15),(52,.15),(75,0)]:
    hand.rotation_quaternion=Quaternion((0,1,0),angle);hand.keyframe_insert('rotation_quaternion',frame=frame)
# A tiny weighted mesh preserves the source skeleton in a standard GLB skin.
mesh=bpy.data.meshes.new('AnimationRigCarrier');mesh.from_pydata([(0,0,0),(.001,0,0),(0,.001,0)],[],[(0,1,2)]);carrier=bpy.data.objects.new('AnimationRigCarrier',mesh);bpy.context.collection.objects.link(carrier);carrier.parent=arm;group=carrier.vertex_groups.new(name='Hips');group.add([0,1,2],1,'REPLACE');modifier=carrier.modifiers.new('Skeleton','ARMATURE');modifier.object=arm
bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=75;bpy.context.scene.render.fps=30;bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);carrier.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(ROOT/'static/motions/studio-wave.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_materials='NONE',export_morph=False,export_bake_animation=True)
print('WAVE_EXPORTED')
