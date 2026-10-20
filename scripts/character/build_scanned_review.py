"""Build the source-specific private Claudia review prototype from a prepared study.

Usage (official Blender, with source-script execution disabled)::

    Blender --disable-autoexec -b -t 2 --python build_scanned_review.py -- \
        SOURCE_REVIEW_DIR OUTPUT.glb [--proof-dir REVIEW_PNG_DIR]

Prerequisite: SOURCE_REVIEW_DIR/Claudia-private-look-review.blend is an already
prepared, privately held Blender scene containing the original Renderpeople
Claudia rigged002 scan mesh, native88-bone rig, photo materials and (for optional
proofs) a camera/light setup. This builder does not download assets, import the
vendor FBX, create that look-review scene or grant redistribution rights. The
prepared scene must not already contain baked shape keys. Original downloaded
files must match SOURCE_REVIEW_DIR/download-verification.json (or --provenance).
Its mesh/mouth dimensions and facial recipes are calibrated to this source;
accepting a directory argument does not make it a generic human rig converter.

The output contains actual native-bone baked jaw/blink/smile deformations and
14 approximate articulating visemes plus neutral silence. Unsupported face
shapes remain absent. It is not full ARKit, calibrated phoneme generation or a
verified drop-in TalkingHead avatar. TalkingHead needs graceful missing-channel
handling; live speech and photographic quality require separate review. Sources
are never saved over. App defaults and production assets are not changed.
"""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_review_dir', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-blend', default='Claudia-private-look-review.blend')
    parser.add_argument('--provenance', default='download-verification.json')
    parser.add_argument('--proof-dir', type=Path)
    return parser.parse_args(sys.argv[sys.argv.index('--') + 1:])


def main():
    args = arguments()
    review = args.source_review_dir.resolve()
    source_blend = (review / args.source_blend).resolve()
    provenance_file = (review / args.provenance).resolve()
    out = args.output.resolve()
    report_file = out.with_suffix('.review.json')
    derived = out.parent / (out.stem + '-derived')
    if out.suffix.lower() != '.glb':
        raise ValueError('The derived output must be a new GLB file')
    if not source_blend.is_file() or not provenance_file.is_file():
        raise ValueError('The prepared source blend and local provenance manifest are required')
    if out in (source_blend, provenance_file):
        raise ValueError('Never overwrite a source input')
    proof_paths = []
    if args.proof_dir:
        args.proof_dir = args.proof_dir.resolve()
        proof_paths = [args.proof_dir / (out.stem + suffix) for suffix in ('-jaw.png', '-blink.png')]
    for path in [out, report_file, derived, *proof_paths]:
        if path.exists():
            raise FileExistsError('Existing file or derived directory preserved: ' + str(path))
    provenance = json.loads(provenance_file.read_text())
    if not isinstance(provenance.get('files'), list) or not provenance['files']:
        raise ValueError('Local provenance must include actual source file hashes')
    input_hashes = {source_blend: file_sha(source_blend), provenance_file: file_sha(provenance_file)}
    for entry in provenance['files']:
        relative = Path(entry['name'].replace('\\', '/'))
        path = (review / relative).resolve()
        if relative.is_absolute() or review not in path.parents:
            raise ValueError('Source provenance paths must stay inside the review directory')
        if not path.is_file() or file_sha(path) != entry['sha256']:
            raise ValueError('Original source checksum mismatch: ' + relative.name)
        input_hashes[path] = entry['sha256']
    if out in input_hashes:
        raise ValueError('Never overwrite an original source file')
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(source_blend), load_ui=False, use_scripts=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    meshes=[o for o in bpy.data.objects if o.type=='MESH'];rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
    if len(meshes)!=1 or len(rigs)!=1:raise ValueError('The prepared Claudia study must contain one scan mesh and one original armature')
    obj,rig=meshes[0],rigs[0]
    if obj.data.shape_keys:raise ValueError('Use the original prepared study before prototype shape baking')
    for name in ['jaw','mouth_l','mouth_r','eyelid_l','eyelid_r']:
     if name not in rig.pose.bones:raise ValueError('The prepared study lacks its native '+name+' control')
    # Save actual derived files then load fresh images, so glTF cannot embed the
    # original packed8K bytes that Blender kept behind a scaled preview buffer.
    derived.mkdir(parents=True,exist_ok=False)
    texture_index=0
    for material in obj.data.materials:
     if not material.use_nodes:continue
     for node in material.node_tree.nodes:
      if node.type!='TEX_IMAGE' or not node.image:continue
      old=node.image;maximum=2048 if any(word in old.name.lower()for word in ('norm','gloss'))else 4096
      width,height=old.size
      if not width or not height:raise ValueError('The prepared study has a missing texture: '+old.name)
      texture_index+=1
      if max(width,height)>maximum:old.scale(round(width*maximum/max(width,height)),round(height*maximum/max(width,height)))
      target=derived/(str(texture_index).zfill(2)+'-'+Path(old.name).stem+'-'+str(maximum)+'.jpg');old.filepath_raw=str(target);old.file_format='JPEG';old.save()
      fresh=bpy.data.images.load(str(target),check_existing=False);fresh.colorspace_settings.name=old.colorspace_settings.name;node.image=fresh

    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    # The two separate arch-shaped mouth components are native FBX geometry.
    adj=[set()for _ in obj.data.vertices]
    for edge in obj.data.edges:a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
    remaining=set(range(len(adj)));dental=[];components=[]
    while remaining:
     stack=[remaining.pop()];indices=[]
     while stack:
      index=stack.pop();indices.append(index);new=adj[index]&remaining;remaining.difference_update(new);stack.extend(new)
     coords=[obj.matrix_world@obj.data.vertices[i].co for i in indices];bounds=[[min(v[k]for v in coords),max(v[k]for v in coords)]for k in range(3)]
     if 300<len(indices)<1000 and 1.60<bounds[2][0]<1.68 and bounds[0][1]-bounds[0][0]<.06:
      dental.extend(indices);components.append({'vertices':len(indices),'bounds':bounds})
    assert len(components)==2,'Native mouth arches not identified confidently'
    # Scan atlas is near-black on these native dental arches. Review-only material.
    tooth=bpy.data.materials.new('Native dental arches — neutral ivory review');tooth.use_nodes=True;shader=tooth.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.55,.52,.45,1);shader.inputs['Roughness'].default_value=.4;shader.inputs['Specular IOR Level'].default_value=.2
    slot=len(obj.data.materials);obj.data.materials.append(tooth);dent=set(dental);dental_faces=0
    for poly in obj.data.polygons:
     if all(i in dent for i in poly.vertices):poly.material_index=slot;dental_faces+=1
    # A fixed, conservative roughness is glTF-compatible; source gloss remains packed
    # in the separate look-study blend, not misrepresented as a metallic map.
    for material in obj.data.materials:
     if not material.use_nodes:continue
     shader=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
     if not shader:continue
     for link in list(shader.inputs['Roughness'].links):material.node_tree.links.remove(link)
     shader.inputs['Roughness'].default_value=.55;shader.inputs['Metallic'].default_value=0

    def hinge(name,degrees):
     bone=rig.pose.bones[name];axis=(rig.matrix_world@bone.bone.matrix_local).to_quaternion().inverted()@Vector((1,0,0));bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion(axis,math.radians(degrees))
    def move(name,world_delta):
     bone=rig.pose.bones[name];bone.location=(rig.matrix_world@bone.bone.matrix_local).to_3x3().inverted()@Vector(world_delta)
    def reset():
     for bone in rig.pose.bones:bone.matrix_basis.identity()
     bpy.context.view_layer.update()
    def evaluated():
     bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();evaluated_obj=obj.evaluated_get(deps);mesh=evaluated_obj.to_mesh();values=array('f',[0.])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',values);evaluated_obj.to_mesh_clear();return values
    basis=obj.shape_key_add(name='Basis');base=array('f',[0.])*(len(basis.data)*3);basis.data.foreach_get('co',base);shapes={}
    def bake(name,jaw=0,width=0,forward=0,up=0,blink=None,smile_side=None):
     reset()
     if jaw:hinge('jaw',jaw)
     for side,sign in [('l',1),('r',-1)]:
      if smile_side is None or smile_side==side:move('mouth_'+side,(sign*width,-forward,up))
     if blink:
      for side in blink:hinge('eyelid_'+side,55)
     values=evaluated();key=obj.shape_key_add(name=name);key.data.foreach_set('co',values)
     if len(values)!=len(base):raise ValueError('Facial control changed source topology')
     maximum=max((obj.matrix_world.to_3x3()@Vector(tuple(values[i+k]-base[i+k]for k in range(3)))).length for i in range(0,len(base),3))
     shapes[name]={'maximum_displacement_m':maximum,'method':'native jaw/corner/lid bone bake'}
     key.value=0;reset();return key
    bake('jawOpen',jaw=8)
    bake('eyeBlinkLeft',blink=['l']);bake('eyeBlinkRight',blink=['r'])
    bake('mouthSmileLeft',width=.0015,up=.002,smile_side='l');bake('mouthSmileRight',width=.0015,up=.002,smile_side='r')
    recipes={
     'aa':(8,.0005,0,0),'CH':(4,-.0015,.001,0),'DD':(3,.0004,0,.0003),'E':(5,.002,0,0),
     'FF':(2,.0008,0,.0004),'I':(3,.0015,0,0),'kk':(6,.0008,0,0),'nn':(2.5,.001,0,.0002),
     'O':(6,-.002,.002,0),'PP':(0,-.0007,0,.0003),'RR':(3.5,-.001,.0008,0),
     'SS':(1.5,.0008,0,0),'TH':(4,.0003,0,.0002),'U':(3.5,-.0017,.0015,0)}
    for name,(jaw,width,forward,up)in recipes.items():bake('viseme_'+name,jaw,width,forward,up)
    # Silence is the actual neutral shape, explicitly not a fabricated articulation.
    obj.shape_key_add(name='viseme_sil');shapes['viseme_sil']={'maximum_displacement_m':0,'method':'unchanged neutral silence'}
    assert all(value['maximum_displacement_m']>1e-5 for name,value in shapes.items()if name!='viseme_sil')
    reset()
    renames={'hip':'Hips','spine_01':'Spine','spine_02':'Spine1','spine_03':'Spine2','neck':'Neck','head':'Head','eye_l':'LeftEye','eye_r':'RightEye'}
    for side,prefix in [('l','Left'),('r','Right')]:
     for source,target in [('shoulder','Shoulder'),('upperarm','Arm'),('lowerarm','ForeArm'),('hand','Hand'),('upperleg','UpLeg'),('lowerleg','Leg'),('foot','Foot'),('ball','ToeBase')]:renames[source+'_'+side]=prefix+target
     for source,target in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
      for i in range(1,4):renames[f'{source}_{i:02d}_{side}']=f'{prefix}Hand{target}{i}'
    for source,target in renames.items():
     assert source in rig.data.bones,source
     rig.data.bones[source].name=target
     group=obj.vertex_groups.get(source)
     if group:group.name=target
    # TalkingHead resets its named root scale to1; apply FBX centimeter transforms
    # to data first and verify this does not change the authored world surface.
    bpy.context.view_layer.update();world_before=[obj.matrix_world@v.co for v in obj.data.vertices]
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bpy.context.view_layer.update();world_after=[obj.matrix_world@v.co for v in obj.data.vertices]
    transform_error=max((a-b).length for a,b in zip(world_before,world_after))
    assert transform_error<1e-4,('Transform application changed the scan',transform_error)
    assert max(abs(value-1)for value in rig.scale)<1e-6
    rig.name='Armature';obj.name='Claudia_Private_Scanned_Study';obj['surfaceRole']='speaking-face';obj['privateReviewOnly']=True;obj['speechQuality']='Approximate native-bone baked phonemes; not calibrated ARKit or validated live speech'
    # Optional proofs require a camera/light setup already present in the study.
    scene=bpy.context.scene
    if args.proof_dir:
     if scene.camera is None:raise ValueError('The prepared study needs a camera for optional proofs')
     args.proof_dir.mkdir(parents=True,exist_ok=True)
     obj.data.shape_keys.key_blocks['viseme_aa'].value=1;scene.render.filepath=str(proof_paths[0]);bpy.ops.render.render(write_still=True);obj.data.shape_keys.key_blocks['viseme_aa'].value=0
     obj.data.shape_keys.key_blocks['eyeBlinkLeft'].value=1;obj.data.shape_keys.key_blocks['eyeBlinkRight'].value=1;scene.render.filepath=str(proof_paths[1]);bpy.ops.render.render(write_still=True)
    for key in obj.data.shape_keys.key_blocks:key.value=0
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_image_format='JPEG',export_jpeg_quality=88,export_apply=False)
    obj.data.calc_loop_triangles()
    report={'private_owner_prototype_only':True,'application_defaults_modified':False,'source_files_hashes_verified':True,'scan':'Renderpeople Claudia rigged002','vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles),'native_dental_components':components,'dental_faces_review_material':dental_faces,'bones':len(rig.data.bones),'mixamo_names_mapped':len(renames),'shapes':shapes,'articulating_visemes':14,'neutral_silence':True,'no_full_arkit_claim':True,'phoneme_accuracy_verified':False,'live_speech_verified':False,'browser_acceptance_verified':False,'independent_geometry_contract_verified_by_this_builder':False,'transforms_applied_world_error_m':transform_error,'root_scale':list(rig.scale),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    assert out.stat().st_size<40*1024*1024,'Private prototype exceeds review budget'
    for source_path,expected_hash in input_hashes.items():
     if file_sha(source_path)!=expected_hash:raise RuntimeError('A source input changed during the build: '+source_path.name)
    report['provenance']={'prepared_blend':source_blend.name,'prepared_blend_sha256':input_hashes[source_blend],'source_manifest':provenance_file.name,'source_manifest_sha256':input_hashes[provenance_file],'source_manifest_scope':provenance.get('scope'),'source_download':provenance.get('source'),'original_file_count_verified':len(provenance['files']),'customer_redistribution_approved':False}
    report['unsupported_mesh_shapes']='absent; this is not a full ARKit face'
    report['talkinghead_runtime_caveat']='Additional missing-channel handling is required; direct TalkingHead loading was not verified'
    report['dental_visibility_verified']=False
    report['proof_files']=[str(path)for path in proof_paths]
    report_file.write_text(json.dumps(report,indent=2));print('PRIVATE_PROTOTYPE',json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
