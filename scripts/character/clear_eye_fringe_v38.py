"""Clear three hair cards from the eye; preserve the private v37 source."""
import bpy,json,sys
from pathlib import Path
root=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=root/'.runtime/character-workshop';dest=out/'Moneypenny-Style-v38.glb'
if dest.exists():raise SystemExit('Existing v38 preserved')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(out/'Moneypenny-Style-v37.glb'))
hair=next(o for o in bpy.data.objects if o.type=='MESH'and any(m.name=='VitHair'for m in o.data.materials))
adj={v.index:set()for v in hair.data.vertices}
for edge in hair.data.edges:a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
unvisited=set(adj);cards=[]
while unvisited:
 seed=unvisited.pop();stack=[seed];card=[seed]
 while stack:
  for index in adj[stack.pop()]&unvisited:unvisited.remove(index);stack.append(index);card.append(index)
 cards.append(card)
def crosses(p):return 1.47<p.z<1.50 and -.055<p.x<0 and p.y<-.12
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
selected=[card for card in cards if any(crosses(hair.data.vertices[i].co)for i in card)]
before=sum(crosses(v.co)for v in hair.data.vertices);changed=0;maximum=0
for card in selected:
 for i in card:
  p=hair.data.vertices[i].co
  w=smooth(1.43,1.47,p.z)*(1-smooth(1.50,1.54,p.z))*smooth(.095,.115,-p.y)*(1-smooth(.055,.08,abs(p.x)))
  delta=.035*w;p.x-=delta
  if delta>1e-8:changed+=1;maximum=max(maximum,delta)
hair.data.update()
if hair.data.has_custom_normals:hair.data.normals_split_custom_set([(0,0,0)]*len(hair.data.loops))
for p in hair.data.polygons:p.use_smooth=True
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig['surface_revision']='v38 — clear eye fringe, surface-fitted expressive brows; retained v36 hands and blouse'
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
report={'revision':'v38','cards_refitted':len(selected),'vertices_shifted':changed,'maximum_side_sweep_m':maximum,'eye_band_vertices_before':before,'eye_band_vertices_after':sum(crosses(v.co)for v in hair.data.vertices),'roots_above_1_54m_unchanged':True,'body_face_and_speech_geometry_unchanged':True,'previous_v37_preserved':True,'bytes':dest.stat().st_size,'photographic_realism_verified':False}
(out/'style-v38-report.json').write_text(json.dumps(report,indent=2)+'\n');print('EYE_FRINGE',json.dumps(report),flush=True)
