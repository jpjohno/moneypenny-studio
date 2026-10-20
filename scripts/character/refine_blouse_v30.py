"""Relax square fabric imprints in the clothed export; preserve the body and rig."""
import bpy,bmesh,sys,json,hashlib,math
from pathlib import Path
from array import array
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v30.glb'
if dest.exists():raise SystemExit('Existing v30 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v29.glb'))
def digest(obj):
 h=hashlib.sha256()
 for key in obj.data.shape_keys.key_blocks if obj.data.shape_keys else []:
  values=array('f',[0.])*(len(key.data)*3);key.data.foreach_get('co',values);h.update(values.tobytes())
 return h.hexdigest()
body=[o for o in bpy.data.objects if o.type=='MESH' and 'Anatomy' in o.name];before={o.name:digest(o) for o in body}
garment=next(o for o in bpy.data.objects if o.type=='MESH' and any('blouse' in m.name.lower() for m in o.data.materials))
bm=bmesh.new();bm.from_mesh(garment.data)
verts=[v for v in bm.verts if not v.is_boundary and 1.075<v.co.z<1.325 and .025<abs(v.co.x)<.24 and v.co.y<-.085]
original={v:v.co.copy() for v in verts}
for _ in range(90):bmesh.ops.smooth_vert(bm,verts=verts,factor=.4,use_axis_x=False,use_axis_y=True,use_axis_z=False)
# Blend into the existing neckline, seams and side panels rather than creasing the border.
for v in verts:
 co=original[v];fade=min(1,(co.z-1.075)/.035,(1.325-co.z)/.035,(abs(co.x)-.025)/.025,(.24-abs(co.x))/.035,(-.085-co.y)/.025);fade=max(0,fade);v.co=co.lerp(v.co,fade)
max_delta=max((abs(v.co.y-original[v].y) for v in verts),default=0)
bm.to_mesh(garment.data);bm.free();garment.data.update()
if garment.data.has_custom_normals:garment.data.normals_split_custom_set([(0,0,0)]*len(garment.data.loops))
for face in garment.data.polygons:face.use_smooth=True
assert all(digest(o)==before[o.name] for o in body)
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v30','garment_vertices_relaxed':len(verts),'maximum_fabric_displacement_m':max_delta,'body_and_facial_keys_unchanged':True,'photographic_realism_verified':False,'bytes':dest.stat().st_size};(out/'style-v30-report.json').write_text(json.dumps(report,indent=2));print('FABRIC_REPAIR',json.dumps(report))
