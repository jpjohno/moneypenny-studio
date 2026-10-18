"""Build a separate editable adult body; preserve the performance workshop.

Blender --background --python this_script -- studio_root [profile.json]
Shape controls are real MPFB macros, applied before fitting its skeleton.
No photographic or detailed anatomy certification is implied.
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:]
root=Path(args[0]).resolve();out=root/'.runtime/character-workshop'
out.mkdir(parents=True,exist_ok=True)
destination=out/'Moneypenny-Adult-Body-Source.blend'
if destination.exists():raise SystemExit('Existing body source preserved: '+str(destination))
profile_path=Path(args[1]) if len(args)>1 else Path(__file__).with_name('body-profile.example.json')
profile=json.loads(profile_path.read_text())
allowed={'height','weight','muscle','proportions','cupsize','firmness'}
if profile.get('version')!=1 or set(profile)-allowed-{'version'}:raise ValueError('Unknown body profile setting.')
for key in allowed:
    value=profile.get(key,.5)
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=1:raise ValueError('Body controls must be between 0 and 1.')
bpy.ops.wm.read_factory_settings(use_empty=True)
import addon_utils
addon_utils.enable('bl_ext.user_default.mpfb',default_set=True,persistent=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
macro=TargetService.get_default_macro_info_dict()
macro.update({key:profile.get(key,.5) for key in allowed})
macro.update(gender=0.0,age=.5)  # This authoring path always creates an adult.
body=HumanService.create_human(macro_detail_dict=macro)
body.name='Adult_Body_Source';rig=HumanService.add_builtin_rig(body,'mixamo')
rig.name='Adult_Body_Rig';rig.show_in_front=True
for poly in body.data.polygons:poly.use_smooth=True
for modifier in body.modifiers:
    if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=True
subdivision=body.modifiers.new('Smooth silhouette — editable','SUBSURF');subdivision.levels=1;subdivision.render_levels=2

# Reuse only the CC0 skin image already supplied with the studio sample.
bpy.ops.import_scene.gltf(filepath=str(root/'static/avatars/mpfb.glb'))
reference=[obj for obj in bpy.context.scene.objects if obj not in (body,rig) and not obj.name.startswith('Adult_')]
image=next((image for image in bpy.data.images if image.name.startswith('young_lightskinned_female_diffuse2')),None)
has_skin_image=image is not None
material=bpy.data.materials.new('Adult skin — source look development');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value=(.52,.30,.22,1)
shader.inputs['Roughness'].default_value=.5
shader.inputs['IOR'].default_value=1.4
shader.inputs['Subsurface Weight'].default_value=.08
shader.inputs['Subsurface Radius'].default_value=(1,.35,.18)
shader.inputs['Subsurface Scale'].default_value=.001
if image:
    texture=nodes.new('ShaderNodeTexImage');texture.image=image;texture.label='Existing CC0 diffuse, not a new scan'
    links.new(texture.outputs['Color'],shader.inputs['Base Color'])
coordinates=nodes.new('ShaderNodeTexCoord');pores=nodes.new('ShaderNodeTexNoise');pores.inputs['Scale'].default_value=850;pores.inputs['Detail'].default_value=2
links.new(coordinates.outputs['Object'],pores.inputs['Vector'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.00008
links.new(pores.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
body.data.materials.clear();body.data.materials.append(material)
# Keep the sample available as hidden reference, separate from the complete base.
collection=bpy.data.collections.new('CLOTHED REFERENCE — hidden');bpy.context.scene.collection.children.link(collection)
for obj in reference:
    for previous in list(obj.users_collection):previous.objects.unlink(obj)
    collection.objects.link(obj)
collection.hide_viewport=True;collection.hide_render=True
for label,location,power,size in [('Key',(2,-3,3),500,3),('Fill',(-2,-2,2),200,3),('Rim',(0,2,3),400,2)]:
    data=bpy.data.lights.new(label,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(label,data);bpy.context.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene;scene.world=bpy.data.worlds.new('Neutral body workshop');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1)
scene.render.engine='BLENDER_EEVEE_NEXT'
body['asset_status']='Unfinished adult body source. Detailed anatomy, eyes/hair/nails, expression and mouth shapes, corrective poses and fitted garments still need work. Not ready to replace the live avatar.'
body['body_profile']=json.dumps(profile)
notes=bpy.data.texts.new('BODY SOURCE STATUS');notes.write(body['asset_status']+'\nShape controls use MPFB human macros. The profile is applied before rig fitting. Smooth shading, editable subdivision, preserve-volume skinning and a skin surface material are present. Procedural skin nodes require baking before browser export. Do not export an untested base as the finished speaking character.\n')
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for image in bpy.data.images:
    if image.source=='FILE' and not image.packed_file:
        try:image.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
report={'status':'unfinished_source','vertices':len(body.data.vertices),'bones':len(rig.data.bones),'profile':profile,'skin_image':has_skin_image,'detailed_anatomy_verified':False,'browser_face_ready':False}
(out/'body-source-report.json').write_text(json.dumps(report,indent=2))
print('BODY_SOURCE_READY',destination)
