"""Round the clothed front drape without modifying the body or facial shapes."""
import bpy,sys,json,math,hashlib
from array import array
from pathlib import Path
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v33.glb'
if dest.exists():raise SystemExit('Existing v33 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v32.glb'))
garment=next(o for o in bpy.data.objects if o.type=='MESH'and any('blouse'in m.name.lower()for m in o.data.materials))
def digest():
 h=hashlib.sha256()
 for o in bpy.data.objects:
  if o.type!='MESH'or o==garment:continue
  for key in o.data.shape_keys.key_blocks if o.data.shape_keys else []:
   values=array('f',[0.])*(len(key.data)*3);key.data.foreach_get('co',values);h.update(values.tobytes())
 return h.hexdigest()
before=digest();changed=0;max_delta=0
for v in garment.data.vertices:
 p=v.co
 if not(1.065<p.z<1.305 and abs(p.x)<.235 and p.y<-.08):continue
 fade=max(0,min(1,(p.z-1.065)/.04,(1.305-p.z)/.04,(.235-abs(p.x))/.045,(-.08-p.y)/.035))
 # Broad, softly connected oval volumes rather than independently projected
 # surface points. Keep the centre placket, neckline and side boundaries.
 placket=min(1,max(0,(abs(p.x)-.012)/.025))
 ellipse=((abs(p.x)-.095)/.115)**2+((p.z-1.182)/.090)**2
 desired=-.088-.102*math.exp(-ellipse*1.35)
 delta=(desired-p.y)*fade*placket*.70
 p.y+=delta;changed+=1;max_delta=max(max_delta,abs(delta))
if garment.data.has_custom_normals:garment.data.normals_split_custom_set([(0,0,0)]*len(garment.data.loops))
for face in garment.data.polygons:face.use_smooth=True
garment.data.update();assert digest()==before
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig['surface_revision']='v33 rounded clothed drape, warm expression supplied by runtime'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v33','garment_vertices_refitted':changed,'maximum_fabric_displacement_m':max_delta,'body_face_and_speech_shapes_unchanged':True,'previous_v32_preserved':True,'bytes':dest.stat().st_size,'photographic_realism_verified':False}
(out/'style-v33-report.json').write_text(json.dumps(report,indent=2));print('DRAPE',json.dumps(report),flush=True)
