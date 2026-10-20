"""Repair displaced fingernails and replace the angular front cloth fit.
Private model source; preserve prior versions, body and expression shapes.
"""
import bpy,sys,json,math,hashlib
from pathlib import Path
from array import array
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v36.glb'
if dest.exists():raise SystemExit('Existing v36 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v33.glb'))
body=bpy.data.objects['Adult_Anatomy_Surface'];base=body.data.shape_keys.key_blocks[0]
def digest():
 h=hashlib.sha256()
 for key in body.data.shape_keys.key_blocks:
  data=array('f',[0.])*(len(key.data)*3);key.data.foreach_get('co',data);h.update(data.tobytes())
 return h.hexdigest()
before=digest();tree=BVHTree.FromPolygons([v.co for v in base.data],[list(p.vertices)for p in body.data.polygons]);kd=KDTree(len(base.data))
for i,v in enumerate(base.data):kd.insert(v.co,i)
kd.balance();nails=next(o for o in bpy.data.objects if o.type=='MESH'and 'nails_01_short'in o.name)
# The source nails had inherited a lateral width deformation absent from the
# distal fingers. Fit each connected nail shell to the actual hand surface.
adj={v.index:set()for v in nails.data.vertices}
for edge in nails.data.edges:a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
unvisited=set(adj);components=[]
while unvisited:
 seed=unvisited.pop();stack=[seed];component=[seed]
 while stack:
  for index in adj[stack.pop()]&unvisited:unvisited.remove(index);stack.append(index);component.append(index)
 components.append(component)
errors=[];distances=[]
for component in components:
 center=sum((nails.data.vertices[i].co for i in component),Vector())/len(component);p,n,_,d=tree.find_nearest(center);errors.append(d);delta=p+n*.00035-center
 for index in component:
  v=nails.data.vertices[index];v.co+=delta
  point,normal,_,distance=tree.find_nearest(v.co)
  # Keep the thin shell on the finger instead of projecting beyond its edge.
  v.co=point+normal*.00035
  _,near,_=kd.find(v.co);source=body.data.vertices[near]
  weights=[(body.vertex_groups[g.group].name,g.weight)for g in source.groups if g.weight>.001]
  weights=sorted(weights,key=lambda item:-item[1])[:4];total=sum(w for _,w in weights)
  for group in nails.vertex_groups:group.remove([index])
  for name,weight in weights:
   group=nails.vertex_groups.get(name)or nails.vertex_groups.new(name=name);group.add([index],weight/total,'REPLACE')
  distances.append(tree.find_nearest(v.co)[3])
nails.data.update()
assert max(distances)<.0005
nails['fit_revision']='v36 — fitted within 0.5 mm of the existing hand surface, body-matched skin weights'
garment=next(o for o in bpy.data.objects if o.type=='MESH'and any('blouse'in m.name.lower()for m in o.data.materials))
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
# Cuffs were accidentally assigned the skirt material by a height-only split.
blouse_slot=next(i for i,m in enumerate(garment.data.materials) if 'blouse' in m.name.lower())
cuff_faces=0
for polygon in garment.data.polygons:
 if polygon.material_index==blouse_slot:continue
 arm_weight=sum(sum(g.weight for g in garment.data.vertices[index].groups if any(part in garment.vertex_groups[g.group].name for part in ('ForeArm','Hand')))for index in polygon.vertices)/len(polygon.vertices)
 if arm_weight>.10:polygon.material_index=blouse_slot;cuff_faces+=1
changed=0;maximum=0
for v in garment.data.vertices:
 p=v.co
 if not(1.005<p.z<1.33 and abs(p.x)<.245 and p.y<-.025):continue
 blend=smooth(1.005,1.035,p.z)*(1-smooth(1.29,1.33,p.z))*(1-smooth(.13,.19,abs(p.x)))*smooth(.025,.07,-p.y)
 # A continuous front loft replaces the old disconnected drape fields. The
 # centre placket shares the cloth surface rather than forming a stiff ridge.
 width=.225;cross=math.sqrt(max(.04,1-(p.x/width)**2))
 torso=.085*cross
 volume=.086*math.exp(-(((abs(p.x)-.092)/.112)**2+((p.z-1.185)/.085)**2)*1.15)
 desired=-torso-volume-.003
 delta=(desired-p.y)*blend*.60;p.y+=delta;maximum=max(maximum,abs(delta));changed+=1
if garment.data.has_custom_normals:garment.data.normals_split_custom_set([(0,0,0)]*len(garment.data.loops))
for polygon in garment.data.polygons:polygon.use_smooth=True
garment.data.update();assert digest()==before
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig['surface_revision']='v36 attached nails and continuous blouse front'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v36','nail_shell_components':len(components),'nail_center_gap_before_m':{'min':min(errors),'max':max(errors)},'maximum_nail_surface_gap_after_m':max(distances),'nail_weights':'nearest body surface, top four normalised influences','cuff_faces_reassigned':cuff_faces,'garment_vertices_refitted':changed,'maximum_fabric_displacement_m':maximum,'body_and_face_shape_coordinates_unchanged':True,'source_v33_preserved':True,'bytes':dest.stat().st_size,'photographic_realism_verified':False}
(out/'style-v36-report.json').write_text(json.dumps(report,indent=2));print('HAND_FIT',json.dumps(report),flush=True)
