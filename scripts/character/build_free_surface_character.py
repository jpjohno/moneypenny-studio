"""Assemble the pinned CC0 Vitruvian character as a browser/native study.

Uses data assets only, no upstream executable scripts. No paid tools/assets.
Source licensing and checksums live beside the downloads. This is not a claim
that source marketing descriptions establish photographic quality.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assets=root/'.runtime/free-character-research/vitruvian'
out=root/'.runtime/character-workshop'
source=out/'Moneypenny-Free-Surface-v10.blend'
candidate=out/'Moneypenny-Free-Surface-v10.glb'
if source.exists() or candidate.exists(): raise SystemExit('Existing free-surface study preserved')
manifest=json.loads((assets/'source-manifest.json').read_text())
for record in manifest['files']:
 data=(assets/record['local_file']).read_bytes()
 if hashlib.sha256(data).hexdigest()!=record['sha256']: raise ValueError('Source checksum mismatch: '+record['local_file'])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
for filename in ['vitruvian_body.glb','vitruvian_head.glb','vitruvian_hair_rigged.glb']:
 bpy.ops.import_scene.gltf(filepath=str(assets/filename))
rig=bpy.data.objects['mixamo_vitruvian']
rig.animation_data_clear()
for obj in list(bpy.data.objects):
 if obj.name.startswith('Icosphere'): bpy.data.objects.remove(obj,do_unlink=True)
 elif obj.animation_data: obj.animation_data_clear()
head=next(o for o in bpy.data.objects if o.type=='MESH' and o.data.shape_keys)
head.name='Moneypenny_Face'
# Bake imported static transforms before attaching the facial surfaces.
facial=[o for o in bpy.data.objects if o.type=='MESH' and o not in [bpy.data.objects.get(n) for n in ['cm_vitruvian','Shirt','Pants','VitHair']]]
eyes=[o for o in facial if 'eyeball' in o.name]
eye_centers={('LeftEye' if o.matrix_world.translation.x>0 else 'RightEye'):o.matrix_world.translation.copy() for o in eyes}
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,point in eye_centers.items():
 bone=rig.data.edit_bones.new(name)
 bone.head=point
 bone.tail=point+Vector((0,-.015,0))
 bone.parent=rig.data.edit_bones['mixamorig:Head']
bpy.ops.object.mode_set(mode='OBJECT')
# Flatten the imported static facial meshes to world-space; apply transforms to
# every shape consistently, then attach to a single compatible main skeleton.
for obj in facial:
 matrix=obj.matrix_world.copy()
 obj.data.transform(matrix,shape_keys=True)
 obj.parent=None
 obj.matrix_world=Matrix.Identity(4)
 obj.parent=rig
 name='LeftEye' if obj in eyes and matrix.translation.x>0 else 'RightEye' if obj in eyes else 'mixamorig:Head'
 group=obj.vertex_groups.new(name=name)
 group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
 modifier=obj.modifiers.new('Facial skinning','ARMATURE')
 modifier.object=rig
# Hair stays a rigged head attachment; browser spring-bone simulation is a
# separate task. Do not imply Godot physics were ported by exporting geometry.
hair=bpy.data.objects['VitHair']
for modifier in list(hair.modifiers):
 if modifier.type=='ARMATURE': hair.modifiers.remove(modifier)
hair.vertex_groups.clear()
hair.parent=rig
hair.matrix_parent_inverse=Matrix.Identity(4)
group=hair.vertex_groups.new(name='mixamorig:Head')
group.add(list(range(len(hair.data.vertices))),1,'REPLACE')
modifier=hair.modifiers.new('Head attachment','ARMATURE')
modifier.object=rig
bpy.data.objects.remove(bpy.data.objects['HairRig'],do_unlink=True)
# Bridge the actual authored FACS deformations into TalkingHead's contract.
original=head.data.shape_keys.key_blocks
basis=original[0]
visemes={'aa':'aa_02','CH':'ey_eh_uh_04','DD':'aa_02','E':'ey_eh_uh_04','FF':'f_v_18','I':'ey_eh_uh_04','kk':'aa_02','nn':'aa_02','O':'ow_08','PP':'p_b_m_21','RR':'Lips_Up_Funnel','sil':None,'SS':'ey_eh_uh_04','TH':'aa_02','U':'ow_08'}
def clone_shape(name,reference,mask=None,strength=1):
 key=head.shape_key_add(name=name)
 if reference:
  for i,(a,b) in enumerate(zip(basis.data,original[reference].data)):
   factor=1 if mask is None else max(0,min(1,.5+a.co.x*mask/ .01))
   key.data[i].co=a.co+(b.co-a.co)*factor*strength
 return key
for name,reference in visemes.items(): clone_shape('viseme_'+name,reference)
for side,mask in [('Left',1),('Right',-1)]:
 clone_shape('eyeBlink'+side,'Eyes_Closed_Max',mask)
 clone_shape('mouthSmile'+side,'Happy',mask,.6)
 clone_shape('browInnerUp','Eyebrows_Raised_Left',None,.7) if side=='Left' else None
 clone_shape('browDown'+side,'Eyebrows_Frown_'+side)
clone_shape('jawOpen','Jaw_Lower')
clone_shape('mouthPucker','Kiss',None,.5)
clone_shape('mouthFrownLeft','Sad',1,.6)
clone_shape('mouthFrownRight','Sad',-1,.6)
# Reconstruct PBR materials from the actual upstream data maps. Godot's
# runtime shaders are not directly portable to a GLB.
images={}
def image(name,noncolor=False):
 if name not in images:
  im=bpy.data.images.load(str(assets/name),check_existing=True)
  if noncolor: im.colorspace_settings.name='Non-Color'
  images[name]=im
 return images[name]
def pbr(material,color=None,normal=None,rough=None,tint=None,alpha=None):
 material.use_nodes=True
 nodes,links=material.node_tree.nodes,material.node_tree.links
 shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 shader.inputs['Metallic'].default_value=0
 shader.inputs['Roughness'].default_value=.45
 shader.inputs['IOR'].default_value=1.4
 shader.inputs['Specular IOR Level'].default_value=.3
 if tint: shader.inputs['Base Color'].default_value=tint
 for filename,socket,noncolor in [(color,'Base Color',False),(rough,'Roughness',True),(alpha,'Alpha',True)]:
  if filename:
   texture=nodes.new('ShaderNodeTexImage');texture.image=image(filename,noncolor)
   links.new(texture.outputs['Color'],shader.inputs[socket])
 if normal:
  texture=nodes.new('ShaderNodeTexImage');texture.image=image(normal,True)
  normal_node=nodes.new('ShaderNodeNormalMap')
  normal_node.inputs['Strength'].default_value=.6
  links.new(texture.outputs['Color'],normal_node.inputs['Color'])
  links.new(normal_node.outputs['Normal'],shader.inputs['Normal'])
 return shader
for material in list(bpy.data.materials):
 name=material.name
 if name=='VitSkin':
  shader=pbr(material,'vit_face_bc.png','vit_face_n.png','vit_face_rough.png')
  shader.inputs['Subsurface Weight'].default_value=.1
  shader.inputs['Subsurface Scale'].default_value=.0012
  shader.inputs['Subsurface Radius'].default_value=(1,.4,.2)
 elif name=='VitBody': pbr(material,'vit_body_bc.png','vit_body_n.png','vit_body_rough.png')
 elif name=='VitMouth': pbr(material,'vit_mouth.png')
 elif name.startswith('VitSclera'): pbr(material,'vit_sclera.png')
 elif name.startswith('VitIris'): pbr(material,'vit_iris.png')
 elif name.startswith('VitCornea'):
  shader=pbr(material,tint=(1,1,1,1));shader.inputs['Transmission Weight'].default_value=1;shader.inputs['Roughness'].default_value=.02;shader.inputs['IOR'].default_value=1.376
 elif name=='VitHair':
  shader=pbr(material,'vit_hair_diffuse.png','vit_hair_normal.png',alpha='vit_hair_opacity.png')
  shader.inputs['Roughness'].default_value=.5
  material.surface_render_method='DITHERED'
 elif name=='VitShirt': pbr(material,tint=(.04,.075,.06,1))
 elif name=='VitPants': pbr(material,tint=(.035,.04,.055,1))
 elif name=='VitShoes': pbr(material,tint=(.022,.016,.013,1))
 elif name.startswith('VitEyeBack'): pbr(material,tint=(.02,.015,.01,1))
 elif name=='VitTearline':
  shader=pbr(material,tint=(.55,.25,.2,1));shader.inputs['Roughness'].default_value=.12
 elif name=='VitCaruncle': pbr(material,tint=(.3,.09,.075,1))
for obj in facial:
 if obj.name.startswith('Eyeshadow'): obj.hide_render=True; obj.hide_set(True)
# Export all three parts with one skeleton and exact runtime bone names.
renames={b.name:b.name.replace('mixamorig:','') for b in rig.data.bones}
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]
for obj in parts:
 for group in obj.vertex_groups:
  if group.name in renames: group.name=renames[group.name]
 for polygon in obj.data.polygons: polygon.use_smooth=True
for bone in list(rig.data.bones): bone.name=renames[bone.name]
for name,label in [('Shirt','CC0 shirt'),('Pants','CC0 trousers')]:
 obj=bpy.data.objects[name];obj['wardrobeSlot']=name.lower();obj['wardrobeLabel']=label
for obj in bpy.context.selected_objects: obj.select_set(False)
rig.select_set(True)
for obj in parts: obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
rig['asset_source']='Vitruvian CC0 character via '+manifest['repository']+' @ '+manifest['commit']
rig['photographic_realism_verified']=False
rig['physics_hair_ported']=False
# Reduce storage and preserve all exported texture data inside the scene.
for im in images.values(): im.pack()
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('Neutral portrait world');scene.world.use_nodes=True
world=scene.world.node_tree.nodes.get('Background');world.inputs['Color'].default_value=(.085,.1,.12,1);world.inputs['Strength'].default_value=.25
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
def area(name,position,power,size,color):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
 obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position
 obj.rotation_euler=(Vector((0,0,1.6))-obj.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-.7,-1,2.1),42,.8,(1,.92,.85))
area('Fill',(.65,-.6,1.8),14,.7,(.83,.9,1))
area('Hair rim',(.35,.5,2),12,.5,(1,.93,.86))
data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',data);scene.collection.objects.link(camera);scene.camera=camera
data.lens=85;camera.location=(.17,-1.22,1.68);camera.rotation_euler=(Vector((0,0,1.58))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=760;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(root/'verification/free-surface-v10-portrait.png')
bpy.ops.wm.save_as_mainfile(filepath=str(source))
bpy.ops.render.render(write_still=True)
report={'revision':'free-surface-v10','source_commit':manifest['commit'],'asset_licence':'CC0 per upstream NOTICE.md',
        'bones':len(rig.data.bones),'hair_vertices':len(hair.data.vertices),'head_shapes':len(head.data.shape_keys.key_blocks)-1,
        'speech_visemes':15,'bytes':candidate.stat().st_size,'photographic_realism_verified':False,
        'spring_hair_simulation_ported':False,'authored_joint_correctives':False,'actual_browser_acceptance':False,
        'local_only':True,'source_scripts_executed':False,'cost':0}
(out/'free-surface-v10-report.json').write_text(json.dumps(report,indent=2))
print('FREE_SURFACE_COMPLETE',json.dumps(report),flush=True)
