"""Make a browser-size copy while preserving the full authoring source."""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=root/'.runtime/character-workshop'
source=out/'Moneypenny-Free-Surface-v13.blend'
candidate=out/'Moneypenny-Free-Surface-v13.glb'
if source.exists() or candidate.exists(): raise SystemExit('Existing browser-sized study preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Free-Surface-v10.blend'))
resized=[]
textures=out/'free-surface-browser-textures'
textures.mkdir(exist_ok=True)
for im in list(bpy.data.images):
 if im.type!='IMAGE': continue
 if len(im.pixels): _=im.pixels[0]
 reduce=im.name.startswith(('vit_body_','vit_hair_normal','vit_hair_opacity','vit_face_rough')) and im.size[0]>1024
 jpeg=im.name.startswith(('vit_face_bc','vit_body_bc','vit_hair_diffuse'))
 if not reduce and not jpeg: continue
 if reduce: im.scale(1024,1024);resized.append(im.name)
 im.file_format='JPEG' if jpeg else 'PNG'
 im.filepath_raw=str(textures/(im.name.rsplit('.',1)[0]+('.jpg' if jpeg else '.png')))
 im.save()
 replacement=bpy.data.images.load(im.filepath_raw,check_existing=False)
 replacement.colorspace_settings.name=im.colorspace_settings.name
 replacement.pack()
 for mat in bpy.data.materials:
  if mat.use_nodes:
   for node in mat.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image==im: node.image=replacement
rig=bpy.data.objects['mixamo_vitruvian']
# glTF imports retain the last animation pose even after action removal.
# Reset every basis before attaching/reviewing the independently exported head.
for bone in rig.pose.bones:
 bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
# The source eyes relied on a procedural Godot shader, not ordinary glTF PBR.
# Replace those surfaces with UV-mapped iris/sclera geometry for this renderer.
for obj in list(bpy.data.objects):
 if 'eyeball' in obj.name: bpy.data.objects.remove(obj,do_unlink=True)
iris_image=bpy.data.images.get('vit_iris.png')
if iris_image is None: iris_image=bpy.data.images.load(str(root/'.runtime/free-character-research/vitruvian/vit_iris.png'))
iris_image.pack()
sclera=bpy.data.materials.new('Optical off-white sclera');sclera.use_nodes=True
shader=sclera.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.68,.65,.61,1);shader.inputs['Roughness'].default_value=.24;shader.inputs['IOR'].default_value=1.376;shader.inputs['Coat Weight'].default_value=.2
iris=bpy.data.materials.new('Radial mapped natural iris');iris.use_nodes=True
shader=iris.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.12;shader.inputs['Coat Weight'].default_value=.8;shader.inputs['Coat Roughness'].default_value=.045
texture=iris.node_tree.nodes.new('ShaderNodeTexImage');texture.image=iris_image
iris.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
for name in ['LeftEye','RightEye']:
 center=rig.data.bones[name].head_local.copy()
 vertices,faces=[],[]
 rings,segments=64,96
 radius,iris_radius=.0146,.0058
 for ring in range(rings+1):
  angle=math.pi*ring/rings
  for segment in range(segments):
   azimuth=segment*math.tau/segments
   vertices.append(center+Vector((radius*math.sin(angle)*math.cos(azimuth),-radius*math.cos(angle),radius*math.sin(angle)*math.sin(azimuth))))
   if ring:
    a=(ring-1)*segments+segment;b=(ring-1)*segments+(segment+1)%segments;c=ring*segments+(segment+1)%segments;d=ring*segments+segment
    faces.append((a,d,c,b))
 mesh=bpy.data.meshes.new(name+' optical geometry');mesh.from_pydata(vertices,[],faces);mesh.update()
 eye=bpy.data.objects.new(name+'_Optical_Eye',mesh);bpy.context.scene.collection.objects.link(eye);eye.parent=rig
 mesh.materials.append(sclera);mesh.materials.append(iris)
 uv=mesh.uv_layers.new(name='Radial iris UV')
 for polygon in mesh.polygons:
  point=sum((mesh.vertices[i].co-center for i in polygon.vertices),Vector())/len(polygon.vertices)
  polygon.material_index=1 if point.y<0 and math.hypot(point.x,point.z)<iris_radius else 0
  polygon.use_smooth=True
  for loop in polygon.loop_indices:
   point=mesh.vertices[mesh.loops[loop].vertex_index].co-center
   uv.data[loop].uv=(.5+point.x/(2*iris_radius),.5+point.z/(2*iris_radius))
 group=eye.vertex_groups.new(name=name);group.add(list(range(len(vertices))),1,'REPLACE')
 modifier=eye.modifiers.new('Gaze skinning','ARMATURE');modifier.object=rig
for material in bpy.data.materials:
 if material.name in ['VitShirt','VitPants']:
  shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  shader.inputs['Roughness'].default_value=.88;shader.inputs['Specular IOR Level'].default_value=.16;shader.inputs['Sheen Weight'].default_value=.15
 if material.name=='VitHair':
  shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  shader.inputs['Roughness'].default_value=.7;shader.inputs['Specular IOR Level'].default_value=.18
hair=bpy.data.objects['VitHair']
for obj in bpy.context.selected_objects: obj.select_set(False)
hair.select_set(True)
bpy.context.view_layer.objects.active=hair
modifier=hair.modifiers.new('Browser hair simplification','DECIMATE')
modifier.ratio=.68
modifier.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=modifier.name)
for obj in bpy.context.selected_objects: obj.select_set(False)
rig.select_set(True)
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]
for obj in parts: obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
rig['surface_revision']='free-surface-v13 — CC0 Vitruvian browser study'
rig['browser_hair_vertices']=len(hair.data.vertices)
bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
if candidate.stat().st_size>80*1024*1024: raise ValueError('Browser candidate still exceeds 80 MiB; source preserved')
bpy.ops.wm.save_as_mainfile(filepath=str(source))
scene=bpy.context.scene
scene.cycles.samples=64
scene.render.filepath=str(root/'verification/free-surface-v13-portrait.png')
bpy.ops.render.render(write_still=True)
report={'revision':'free-surface-v13','bytes':candidate.stat().st_size,'hair_vertices':len(hair.data.vertices),
        'resized_images':resized,'face_maps':'2048px colour/normal; 1024px roughness; colour JPEG encoding','cost':0,
        'source_preserved':True,'photographic_realism_verified':False,'actual_browser_acceptance':False}
(out/'free-surface-v13-report.json').write_text(json.dumps(report,indent=2))
print('FREE_BROWSER_SURFACE_READY',json.dumps(report),flush=True)
