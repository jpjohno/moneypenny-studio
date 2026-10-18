"""Neutral native review views: full outfit, posed arm, hands and feet."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
out = root / '.runtime/character-workshop'
bpy.ops.wm.open_mainfile(filepath=str(out / 'Moneypenny-Performance-Final-Fit-v3.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['Adult_Body_Rig']
data = bpy.data.cameras.new('Detail review')
camera = bpy.data.objects.new('Detail review', data)
scene.collection.objects.link(camera)
scene.camera = camera
data.type = 'ORTHO'
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples = 32
scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
def view(label, center, position, scale):
    data.ortho_scale = scale
    camera.location = position
    camera.rotation_euler = (Vector(center) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(root / 'verification' / ('performance-' + label + '.png'))
    bpy.ops.render.render(write_still=True)
view('full-outfit', (0, 0, .80), (0, -3, .90), 1.9)
rig.pose.bones['mixamorig:RightForeArm'].rotation_mode = 'XYZ'
rig.pose.bones['mixamorig:RightForeArm'].rotation_euler.z = -.7
bpy.context.view_layer.update()
view('arm-pose', (0, 0, 1.05), (0, -3, 1.10), 1.3)
rig.pose.bones['mixamorig:RightForeArm'].rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
for label, pattern, offset, scale in [('hand-detail', 'mindfront_nails_01_short', (.4, .6, .2), .22),
                                       ('foot-detail', 'mindfront_nails_toes_01', (.2, -.55, .3), .27)]:
    if label == 'foot-detail':
        bpy.data.objects['Office_Ankle_Shoes'].hide_render = True
    obj = next(obj for obj in bpy.data.objects if pattern in obj.name)
    points = [v.co for v in obj.data.vertices if v.co.x > 0]
    center = sum(points, Vector()) / len(points)
    view(label, center, center + Vector(offset), scale)
    if label == 'foot-detail':
        bpy.data.objects['Office_Ankle_Shoes'].hide_render = False
        obj.hide_render = True
        view('shoe-coverage', center, center + Vector(offset), scale)
report = {'views': ['full-outfit', 'arm-pose', 'hand-detail', 'foot-detail', 'shoe-coverage'],
          'native_rendered': True, 'human_visual_acceptance': False,
          'full_pose_and_photographic_certification': False}
(out / 'performance-detail-review.json').write_text(json.dumps(report, indent=2))
