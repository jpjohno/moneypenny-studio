"""Fit facial brow roots to the existing face, retaining its speech rig.

This is a reversible look-development candidate, not a captured human scan.
The previous private GLB, body, face and garment geometry remain unchanged.
"""
import bpy,json,sys,hashlib
from pathlib import Path
from array import array
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v37.glb'
if dest.exists():raise SystemExit('Existing v37 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v36.glb'))
body=bpy.data.objects['Adult_Anatomy_Surface'];basis=body.data.shape_keys.key_blocks[0]
def digest():
 h=hashlib.sha256()
 for key in body.data.shape_keys.key_blocks:
  co=array('f',[0.])*(len(key.data)*3);key.data.foreach_get('co',co);h.update(co.tobytes())
 return h.hexdigest()
before=digest();tree=BVHTree.FromPolygons([v.co for v in basis.data],[list(p.vertices)for p in body.data.polygons])
kd=KDTree(len(basis.data))
for i,v in enumerate(basis.data):kd.insert(v.co,i)
kd.balance();brows=bpy.data.objects['Brow_Individual_Strands']
adj={v.index:set()for v in brows.data.vertices}
for edge in brows.data.edges:a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
unvisited=set(adj);components=[]
while unvisited:
 seed=unvisited.pop();stack=[seed];component=[seed]
 while stack:
  for index in adj[stack.pop()]&unvisited:unvisited.remove(index);stack.append(index);component.append(index)
 components.append(component)
old_gaps=[];new_gaps=[]
for component in components:
 # A triangular tapered filament has a three-vertex root at its lower end.
 ids=sorted(component,key=lambda i:brows.data.vertices[i].co.z)[:3]
 centre=sum((brows.data.vertices[i].co for i in ids),Vector())/len(ids)
 p,n,_,gap=tree.find_nearest(centre);old_gaps.append(gap)
 delta=p+n*.0002-centre
 for i in component:brows.data.vertices[i].co+=delta
 newcentre=sum((brows.data.vertices[i].co for i in ids),Vector())/len(ids)
 new_gaps.append(tree.find_nearest(newcentre)[3])
assert max(new_gaps)<.0004
# Facial brow expressions follow the same local body targets rather than
# remaining fixed to the skull while the skin below them moves.
mapping=[kd.find(v.co)[1]for v in brows.data.vertices]
if not brows.data.shape_keys:brows.shape_key_add(name='Basis')
for name in ('browDownLeft','browDownRight','browInnerUp','browOuterUpLeft','browOuterUpRight'):
 source=body.data.shape_keys.key_blocks.get(name)
 if source is None:continue
 target=brows.data.shape_keys.key_blocks.get(name)or brows.shape_key_add(name=name)
 for i,near in enumerate(mapping):target.data[i].co=brows.data.shape_keys.key_blocks[0].data[i].co+source.data[near].co-basis.data[near].co
brows.data.update();assert digest()==before
brows['fit_revision']='v37 — brow roots on actual face surface; five expression targets follow the face'
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig['surface_revision']='v37 portrait surface and expression-linked brows; v36 hand/clothing repair retained'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v37','brow_strands':len(components),'maximum_root_gap_before_m':max(old_gaps),'maximum_root_gap_after_m':max(new_gaps),'brow_expression_targets':5,'body_face_and_speech_shape_coordinates_unchanged':True,'previous_v36_preserved':True,'bytes':dest.stat().st_size,'photographic_realism_verified':False}
(out/'style-v37-report.json').write_text(json.dumps(report,indent=2)+'\n');print('PORTRAIT',json.dumps(report),flush=True)
