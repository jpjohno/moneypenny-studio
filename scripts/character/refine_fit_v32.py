"""Private clothed fit correction, preserving previous exports and facial motion.
Reduces chest projection and relaxes angular fabric imprints; no new detail.
"""
import bpy,bmesh,sys,json,math,hashlib
from array import array
from pathlib import Path
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v32.glb'
if dest.exists():raise SystemExit('Existing v32 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v31.glb'))
garment=next(o for o in bpy.data.objects if o.type=='MESH'and any('blouse' in m.name.lower()for m in o.data.materials))
body=next(o for o in bpy.data.objects if o.type=='MESH'and 'Anatomy' in o.name)
def face_digest():
 h=hashlib.sha256()
 for key in body.data.shape_keys.key_blocks:
  h.update(array('f',[c for v in key.data if v.co.z>1.4 for c in v.co]).tobytes())
 return h.hexdigest()
face_before=face_digest()
def change(p):
 w=math.exp(-(((abs(p.x)-.105)/.115)**4+((p.z-1.17)/.11)**4)*1.3)
 front=max(0,min(1,(-p.y-.065)/.12))
 return .035*w*front
changed=0;maximum=0
for obj in [body,garment]:
 basis=obj.data.shape_keys.key_blocks[0]if obj.data.shape_keys else None
 for i,v in enumerate(basis.data if basis else obj.data.vertices):
  delta=change(v.co)
  if delta<1e-7:continue
  if basis:
   for key in obj.data.shape_keys.key_blocks:key.data[i].co.y+=delta
  else:v.co.y+=delta
  maximum=max(maximum,delta);changed+=1
 obj.data.update()
# glTF splits vertices at UV/normal boundaries. Restore adjacency before fabric
# relaxation, otherwise every split loop is treated as a pinned boundary.
bm=bmesh.new();bm.from_mesh(garment.data);before=len(bm.verts)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
selected=[v for v in bm.verts if not v.is_boundary and 1.07<v.co.z<1.31 and .025<abs(v.co.x)<.235 and v.co.y<-.08]
original={v:v.co.copy()for v in selected}
for _ in range(120):bmesh.ops.smooth_vert(bm,verts=selected,factor=.35,use_axis_x=False,use_axis_y=True,use_axis_z=False)
for v in selected:
 p=original[v];fade=max(0,min(1,(p.z-1.07)/.035,(1.31-p.z)/.035,(abs(p.x)-.025)/.025,(.235-abs(p.x))/.035,(-.08-p.y)/.025));v.co=p.lerp(v.co,fade)
after=len(bm.verts);bm.to_mesh(garment.data);bm.free();garment.data.update()
if garment.data.has_custom_normals:garment.data.normals_split_custom_set([(0,0,0)]*len(garment.data.loops))
for face in garment.data.polygons:face.use_smooth=True
for mat in garment.data.materials:
 if 'blouse'not in mat.name.lower():continue
 shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for link in list(shader.inputs['Base Color'].links):mat.node_tree.links.remove(link)
 shader.inputs['Base Color'].default_value=(.035,.11,.14,1);shader.inputs['Roughness'].default_value=.72
 mat['fit_revision']='v32 — reduced projection, continuous smooth fabric; preserved neckline and seam boundaries'
# Standardise the hair slot after glTF import adds a numerical material suffix.
for mat in bpy.data.materials:
 if mat.name.startswith('VitHair.'):
  old=bpy.data.materials.get('VitHair')
  if old and old.users==0:bpy.data.materials.remove(old)
  mat.name='VitHair'
assert face_digest()==face_before, 'Facial coordinates changed'
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig['surface_revision']='v32 clothed fit, natural skin and feathered hair'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v32','maximum_chest_projection_reduction_m':maximum,'vertices_adjusted':changed,'garment_vertices_before_weld':before,'garment_vertices_after_weld':after,'fabric_vertices_relaxed':len(selected),'face_and_viseme_geometry_unchanged':True,'previous_v31_preserved':True,'bytes':dest.stat().st_size,'photographic_realism_verified':False}
(out/'style-v32-report.json').write_text(json.dumps(report,indent=2));print('FIT',json.dumps(report),flush=True)
