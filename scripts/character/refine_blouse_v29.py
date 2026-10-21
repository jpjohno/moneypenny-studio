"""Replace the chalky blouse finish and soften its mesh. Never edit body keys."""
import bpy,bmesh,json,hashlib,sys,math
from pathlib import Path
from array import array
from mathutils.bvhtree import BVHTree
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop'
dest=out/'Moneypenny-Style-v29.glb'
if dest.exists():raise SystemExit('Existing v29 preserved')
bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Style-v27.blend'))
rig=bpy.data.objects['Adult_Body_Rig'];body=bpy.data.objects['Adult_Anatomy_Surface'];garment=bpy.data.objects['Office_Blouse_And_Skirt']
def digest():
 h=hashlib.sha256()
 for key in body.data.shape_keys.key_blocks:
  data=array('f',[0.])*(len(key.data)*3);key.data.foreach_get('co',data);h.update(data.tobytes())
 return h.hexdigest()
before=digest();parts=[o for o in bpy.data.objects if o.parent==rig and o.type=='MESH' and not o.hide_render]
# Smooth only interior blouse vertices. Boundary loops, neckline and hem stay authored.
bm=bmesh.new();bm.from_mesh(garment.data)
verts=[v for v in bm.verts if not v.is_boundary and v.co.z>1.015]
for _ in range(4):bmesh.ops.smooth_vert(bm,verts=verts,factor=.25,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.to_mesh(garment.data);bm.free()
# Fit to the deformed body in rest space and share its arm weights. This
# prevents the old blouse's sleeve weights drifting through the character.
from mathutils.kdtree import KDTree
mods=[m for m in body.modifiers if m.type=='ARMATURE'];states=[m.show_viewport for m in mods]
for m in mods:m.show_viewport=False
deps=bpy.context.evaluated_depsgraph_get();deps.update();evaluated=body.evaluated_get(deps);surface=evaluated.to_mesh()
tree=BVHTree.FromPolygons([v.co.copy() for v in surface.vertices],[list(p.vertices) for p in surface.polygons])
kd=KDTree(len(surface.vertices))
for v in surface.vertices:kd.insert(v.co,v.index)
kd.balance();changes=0;weight_rows=[]
for vertex in garment.data.vertices:
 if vertex.co.z<1.015:continue
 nearest,normal,_,distance=tree.find_nearest(vertex.co)
 if nearest is not None and distance<.045:
  signed=(vertex.co-nearest).dot(normal)
  if signed<.010:vertex.co+=normal*(.010-signed);changes+=1
 _,index,_=kd.find(vertex.co)
 source=surface.vertices[index]
 row=sorted([(body.vertex_groups[g.group].name,g.weight) for g in source.groups if g.weight>.001],key=lambda p:-p[1])[:4]
 if row:weight_rows.append((vertex.index,row))
indices=[i for i,_ in weight_rows]
for group in garment.vertex_groups:
 if group.name in body.vertex_groups:group.remove(indices)
for index,row in weight_rows:
 total=sum(weight for _,weight in row)
 for name,weight in row:
  group=garment.vertex_groups.get(name) or garment.vertex_groups.new(name=name);group.add([index],weight/total,'REPLACE')
evaluated.to_mesh_clear()
for m,state in zip(mods,states):m.show_viewport=state
deps.update()
for face in garment.data.polygons:face.use_smooth=True
# The same UV atlas remains; a tiny neutral weave avoids a plastic uniform highlight.
image=bpy.data.images.new('Fine crepe weave',width=256,height=256,alpha=False)
pixels=array('f')
for y in range(256):
 for x in range(256):
  weave=.92+.025*math.sin(x*math.pi/2)*math.sin(y*math.pi/2)+.012*math.sin(x*1.83+y*2.79)
  pixels.extend((weave,weave,weave,1.))
image.pixels.foreach_set(pixels);image.pack()
for mat in garment.data.materials:
 if not mat or 'blouse' not in mat.name.lower():continue
 mat.name='Studio crepe blouse';mat.use_nodes=True;nodes=mat.node_tree.nodes;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 for link in list(mat.node_tree.links):
  if link.to_node==bs and link.to_socket.name in ['Base Color','Roughness','Normal']:mat.node_tree.links.remove(link)
 bs.inputs['Base Color'].default_value=(.035,.15,.18,1);bs.inputs['Roughness'].default_value=.8;bs.inputs['Metallic'].default_value=0
 bs.inputs['Coat Weight'].default_value=0;bs.inputs['Sheen Weight'].default_value=.18
 tex=nodes.new('ShaderNodeTexImage');tex.image=image
 multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1;multiply.inputs[2].default_value=(.035,.15,.18,1)
 mat.node_tree.links.new(tex.outputs['Color'],multiply.inputs[1]);mat.node_tree.links.new(multiply.outputs['Color'],bs.inputs['Base Color'])
 assert digest()==before
# Retain the existing covered export mask, and all facial visemes.
for obj in bpy.context.selected_objects:obj.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
for face in body.data.polygons:
 if .99<face.center.z<1.285 and abs(face.center.x)<.20:face.select=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.delete(type='ONLY_FACE');bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.selected_objects:obj.select_set(False)
rig.select_set(True)
for obj in parts:obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v29','blouse':'petrol crepe','body_and_facial_coordinates_preserved':True,'blouse_vertices_smoothed':len(verts),'vertices_fitted_outside_body':changes,'vertices_with_body_weights':len(weight_rows),'bytes':dest.stat().st_size,'photographic_realism_verified':False}
(out/'style-v29-report.json').write_text(json.dumps(report,indent=2));print('BLOUSE_COMPLETE',json.dumps(report))
