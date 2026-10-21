"""Private clothed look comparison: replace heavy hair and painted makeup assets.
Preserve v30, body geometry, rig, clothing and all speech/expression shapes.
"""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
from array import array
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v31.glb'
if dest.exists():raise SystemExit('Existing v31 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v30.glb'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
def digest(o):
 h=hashlib.sha256()
 for key in o.data.shape_keys.key_blocks if o.data.shape_keys else []:
  values=array('f',[0.])*(len(key.data)*3);key.data.foreach_get('co',values);h.update(values.tobytes())
 return h.hexdigest()
body=[o for o in bpy.data.objects if o.type=='MESH' and 'Anatomy' in o.name];before={o.name:digest(o)for o in body}
old_triangles=sum(len(p.vertices)-2 for o in bpy.data.objects if o.type=='MESH'for p in o.data.polygons)
for o in list(bpy.data.objects):
 if o.type=='MESH' and any(m.name in {'VitHair','Soft blonde root underlayer'} for m in o.data.materials):bpy.data.objects.remove(o,do_unlink=True)
assets=root/'.runtime/character-tools/assets';folder=assets/'hair02/hair/elvs_ashley_may_hair';obj=folder/'elvs_ashley_mayhair1.obj'
verts=[];uv=[];faces=[];uvfaces=[]
for line in obj.read_text().splitlines():
 parts=line.split()
 if not parts:continue
 if parts[0]=='v':
  x,y,z=map(float,parts[1:4]);verts.append((x*.086,-z*.086,y*.105+.785))
 elif parts[0]=='vt':uv.append(tuple(map(float,parts[1:3])))
 elif parts[0]=='f':
  ids=[p.split('/')for p in parts[1:]];faces.append(tuple(int(i[0])-1 for i in ids));uvfaces.append([int(i[1])-1 for i in ids])
mesh=bpy.data.meshes.new('Feathered shoulder-length hair');mesh.from_pydata(verts,[],faces);mesh.update();hair=bpy.data.objects.new('Soft_Wavy_Bob',mesh);bpy.context.scene.collection.objects.link(hair)
layer=mesh.uv_layers.new(name='UVMap')
for poly,indices in zip(mesh.polygons,uvfaces):
 poly.use_smooth=True
 for loop,index in zip(poly.loop_indices,indices):layer.data[loop].uv=uv[index]
hair.parent=rig;head=next(b.name for b in rig.data.bones if b.name.split(':')[-1]=='Head');hair.vertex_groups.new(name=head).add(list(range(len(verts))),1,'REPLACE');hair.modifiers.new('Head skinning','ARMATURE').object=rig
material=bpy.data.materials.new('VitHair');material.use_nodes=True;material.use_backface_culling=False;material.surface_render_method='DITHERED';nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF')
color=nodes.new('ShaderNodeTexImage');color.image=bpy.data.images.load(str(folder/'80shairtex1.png'));links.new(color.outputs['Color'],shader.inputs['Base Color']);links.new(color.outputs['Alpha'],shader.inputs['Alpha'])
shader.inputs['Roughness'].default_value=.62;shader.inputs['Specular IOR Level'].default_value=.22
normal=nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(folder/'80snormals.png'));normal.image.colorspace_settings.name='Non-Color';normal_node=nodes.new('ShaderNodeNormalMap');normal_node.inputs['Strength'].default_value=.18;links.new(normal.outputs['Color'],normal_node.inputs['Color']);links.new(normal_node.outputs['Normal'],shader.inputs['Normal']);mesh.materials.append(material)
hair['attribution']='Ashley May hair by Elvaerwyn; CC-BY per original mhclo, version unspecified; hair02 pack. Geometry transformed to fit this private character.'
for o in body:
 for mat in o.data.materials:
  if not mat or not mat.use_nodes or not mat.name.startswith('Performance skin'):continue
  shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(assets/'skins01/skins/bobby_03_young_female_hairless/Young_Female_Hairless.png'));mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Specular IOR Level'].default_value=.28
  mat['skin_attribution']='Young Female Hairless by bobby_03; skins01 CC0 pack; unmodified colour texture, not a claimed scan.'
assert all(digest(o)==before[o.name]for o in body)
# Use glTF MASK for depth-correct layered cards in the browser.
threshold=nodes.new('ShaderNodeMath');threshold.operation='GREATER_THAN';threshold.inputs[1].default_value=.25;links.new(color.outputs['Alpha'],threshold.inputs[0]);
# The skin loop rebinds shader above; explicitly bind the hair alpha target.
hair_shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');links.new(threshold.outputs[0],hair_shader.inputs['Alpha'])
rig['surface_revision']='v31 — natural colour skin, low polygon feathered hair; preserved v30 rig and expressions'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
triangles=sum(len(p.vertices)-2 for o in bpy.data.objects if o.type=='MESH'for p in o.data.polygons)
report={'revision':'v31','bytes':dest.stat().st_size,'triangles_before':old_triangles,'triangles_after':triangles,'hair_triangles':sum(len(p.vertices)-2 for p in mesh.polygons),'body_and_face_shape_keys_unchanged':True,'photographic_realism_verified':False,'source_v30_preserved':True,'skin':'bobby_03 CC0','hair':hair['attribution']};(out/'style-v31-report.json').write_text(json.dumps(report,indent=2));print('NATURAL_LOOK',json.dumps(report),flush=True)
# A modest source review, not a substitute for live browser acceptance.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=512;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.16,.2,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
for name,location,power,size in [('Key',(-1,-2,2.5),110,2),('Fill',(1,-1,1.8),50,2),('Rim',(0,1,2),80,1)]:
 bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object;light.name=name;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,1.35))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-2.1,1.48));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,1.35))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.85;scene.camera=camera
scene.render.filepath=str(root/'verification/natural-v31-review.png');bpy.ops.render.render(write_still=True)
