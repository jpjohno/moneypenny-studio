"""Blender 4.5 panel for general pose authoring and motion-only GLB export.

Run inside Blender using --python or the Text Editor. Does not save the .blend,
execute model output, or send anything to the web app. Exported motion is imported
through the studio's existing motion-library picker.
"""
import json
import math
from pathlib import Path

import bpy
from bpy.props import IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from mathutils import Quaternion, Vector

bl_info = {"name": "Moneypenny Studio Motion", "version": (1, 0, 0),
           "blender": (4, 5, 0), "category": "Animation"}
POSE_KEY = "moneypenny_saved_pose_v1"


def selected_rig(context):
    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        return obj
    if obj and obj.type == 'MESH':
        return obj.find_armature()
    return None


def snapshot(rig):
    result = {}
    for bone in rig.pose.bones:
        position, rotation, scale = bone.matrix_basis.decompose()
        result[bone.name] = [list(position), list(rotation), list(scale)]
    return result


def transition(context, rig, target, frames):
    if set(target) != set(rig.pose.bones.keys()):
        raise ValueError("The saved pose belongs to a different bone layout. Capture it again.")
    if any(not track.mute for track in (rig.animation_data.nla_tracks if rig.animation_data else [])):
        raise ValueError("Mute NLA tracks before authoring a separate pose transition.")
    if any(b.constraints for b in rig.pose.bones):
        raise ValueError("This rig has constraints. Animate its control rig directly, then export the evaluated motion.")
    for values in target.values():
        if len(values) != 3 or [len(x) for x in values] != [3, 4, 3] or not all(math.isfinite(x) for part in values for x in part):
            raise ValueError("The saved pose contains invalid transforms.")
    initial = snapshot(rig)
    start = context.scene.frame_current
    rig.animation_data_create()
    previous = rig.animation_data.action
    if previous:
        previous.use_fake_user = True
    action = bpy.data.actions.new("Studio pose transition")
    action.use_fake_user = True
    rig.animation_data.action = action
    # Sample smoothstep + quaternion slerp explicitly; no Euler wrap or reliance
    # on Blender's action-slot/fcurve internals across supported versions.
    for index in range(frames + 1):
        weight = index / frames
        weight = weight * weight * (3 - 2 * weight)
        for bone in rig.pose.bones:
            a, b = initial[bone.name], target[bone.name]
            bone.rotation_mode = 'QUATERNION'
            bone.location = Vector(a[0]).lerp(Vector(b[0]), weight)
            bone.rotation_quaternion = Quaternion(a[1]).slerp(Quaternion(b[1]), weight)
            bone.scale = Vector(a[2]).lerp(Vector(b[2]), weight)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=start + index, group=bone.name)
    context.scene.frame_end = max(context.scene.frame_end, start + frames)
    context.scene.frame_set(start)
    return action


def export_motion(context, rig, filepath):
    scene = context.scene
    fps = scene.render.fps / scene.render.fps_base
    duration = (scene.frame_end - scene.frame_start) / fps
    if not 0 < duration <= 60 or scene.frame_end - scene.frame_start > 1800:
        raise ValueError("Set the scene frame range to a motion between 0 and 60 seconds, at most 1,800 frames.")
    if rig.mode != 'OBJECT':
        raise ValueError("Switch to Object Mode before exporting.")
    if not rig.data.bones:
        raise ValueError("The selected rig has no bones.")
    selected, active = list(context.selected_objects), context.view_layer.objects.active
    frame, subframe = scene.frame_current, scene.frame_subframe
    carrier = mesh = None
    try:
        # Export only the rig and a tiny skin carrier. Character geometry,
        # textures, wardrobe and private reference assets never enter this GLB.
        mesh = bpy.data.meshes.new("StudioMotionCarrier")
        mesh.from_pydata([(0, 0, 0), (.001, 0, 0), (0, .001, 0)], [], [(0, 1, 2)])
        carrier = bpy.data.objects.new("StudioMotionCarrier", mesh)
        scene.collection.objects.link(carrier)
        carrier.parent = rig
        carrier.vertex_groups.new(name=rig.data.bones[0].name).add([0, 1, 2], 1, 'REPLACE')
        carrier.modifiers.new('Motion skeleton', 'ARMATURE').object = rig
        for obj in selected:
            obj.select_set(False)
        rig.select_set(True)
        carrier.select_set(True)
        context.view_layer.objects.active = rig
        result = bpy.ops.export_scene.gltf(
            filepath=str(Path(filepath).with_suffix('.glb')), export_format='GLB',
            use_selection=True, export_animations=True, export_animation_mode='SCENE',
            export_frame_range=True, export_force_sampling=True, export_bake_animation=True,
            export_skins=True, export_materials='NONE', export_morph=False,
            export_cameras=False, export_lights=False)
        if result != {'FINISHED'}:
            raise ValueError("Blender did not finish exporting the movement.")
    finally:
        if carrier:
            bpy.data.objects.remove(carrier, do_unlink=True)
        if mesh:
            bpy.data.meshes.remove(mesh)
        rig.select_set(False)
        for obj in selected:
            obj.select_set(True)
        context.view_layer.objects.active = active
        scene.frame_set(frame, subframe=subframe)


class MSTUDIO_OT_capture_pose(bpy.types.Operator):
    bl_idname = 'mstudio.capture_pose'
    bl_label = 'Remember current pose'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = selected_rig(context)
        if not rig:
            self.report({'ERROR'}, "Select the intended character rig or its skinned mesh.")
            return {'CANCELLED'}
        rig[POSE_KEY] = json.dumps(snapshot(rig))
        self.report({'INFO'}, "Pose remembered on the selected rig. Source file has not been saved.")
        return {'FINISHED'}


class MSTUDIO_OT_transition_pose(bpy.types.Operator):
    bl_idname = 'mstudio.transition_pose'
    bl_label = 'Animate to remembered pose'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = selected_rig(context)
        if not rig or POSE_KEY not in rig:
            self.report({'ERROR'}, "Remember a pose on the selected rig first.")
            return {'CANCELLED'}
        try:
            transition(context, rig, json.loads(rig[POSE_KEY]), context.scene.mstudio_transition_frames)
        except (ValueError, TypeError, KeyError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "New timeline action created; previous action kept in the file. Play the timeline to review.")
        return {'FINISHED'}


class MSTUDIO_OT_export_motion(bpy.types.Operator, ExportHelper):
    bl_idname = 'mstudio.export_motion'
    bl_label = 'Export movement for web studio'
    filename_ext = '.glb'
    filter_glob: StringProperty(default='*.glb', options={'HIDDEN'})

    def execute(self, context):
        rig = selected_rig(context)
        if not rig:
            self.report({'ERROR'}, "Select the intended character rig or its skinned mesh.")
            return {'CANCELLED'}
        try:
            export_motion(context, rig, self.filepath)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "Movement exported. Import this GLB into the web studio's Motion library.")
        return {'FINISHED'}


class MSTUDIO_PT_motion(bpy.types.Panel):
    bl_label = 'Moneypenny Motion'
    bl_idname = 'MSTUDIO_PT_motion'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Moneypenny'

    def draw(self, context):
        layout = self.layout
        rig = selected_rig(context)
        layout.label(text=rig.name if rig else 'Select a character rig')
        column = layout.column()
        column.enabled = rig is not None
        column.operator('mstudio.capture_pose')
        column.prop(context.scene, 'mstudio_transition_frames', text='Transition frames')
        column.operator('mstudio.transition_pose')
        column.separator()
        column.operator('mstudio.export_motion')
        layout.label(text='Export uses the scene frame range.')
        layout.label(text='No automatic save or web upload.')


CLASSES = (MSTUDIO_OT_capture_pose, MSTUDIO_OT_transition_pose, MSTUDIO_OT_export_motion, MSTUDIO_PT_motion)


def register():
    for cls in CLASSES:
        old = getattr(bpy.types, cls.__name__, None)
        if old:
            bpy.utils.unregister_class(old)
        bpy.utils.register_class(cls)
    bpy.types.Scene.mstudio_transition_frames = IntProperty(name='Transition frames', default=24, min=6, max=180)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mstudio_transition_frames


if __name__ == '__main__':
    register()
