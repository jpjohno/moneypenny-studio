"""Run with Blender --background --python this_file -- /path/to/studio.
Creates an editable character/animation workshop; does not certify photorealism.
"""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(sys.argv[sys.argv.index('--')+1]).resolve()
OUT=ROOT/'.runtime/character-workshop';OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'Moneypenny-Character-Workshop.blend').exists():
    print('Existing workshop preserved:',OUT/'Moneypenny-Character-Workshop.blend');raise SystemExit(0)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'static/avatars/mpfb.glb'))
arm=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
arm.name='Moneypenny_Performance_Rig';arm.show_in_front=True
controls=bpy.data.collections.new('PERFORMANCE CONTROLS');bpy.context.scene.collection.children.link(controls)
for side in ('Left','Right'):
    for limb,end,chain in [('Hand','Hand',2),('Foot','Foot',2)]:
        name=side+end;bone=arm.pose.bones.get(name)
        if not bone:continue
        control=bpy.data.objects.new('CTRL_'+name,None);controls.objects.link(control);control.empty_display_type='SPHERE';control.empty_display_size=.055;control.location=arm.matrix_world@bone.head
        control['usage']='Move this target to pose the limb. IK constraint is on the forearm/shin; enable its influence when animating.'
        parent=arm.pose.bones.get(side+('ForeArm' if limb=='Hand' else 'Leg'))
        ik=parent.constraints.new('IK');ik.name='Studio '+name+' IK';ik.target=control;ik.chain_count=chain;ik.use_tail=True;ik.use_stretch=False;ik.influence=0
# Preserve the original clothed sample while adding a separate editable adult base.
try:
    import addon_utils
    if not addon_utils.check('bl_ext.user_default.mpfb')[1]:addon_utils.enable('bl_ext.user_default.mpfb',default_set=True,persistent=True)
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    macro=TargetService.get_default_macro_info_dict();macro['gender']=0.0;macro['age']=.5
    previous=set(bpy.data.objects)
    base=HumanService.create_human(macro_detail_dict=macro)
    base.name='Adult_Body_Source_UNFINISHED'
    source_rig=HumanService.add_builtin_rig(base,'mixamo')
    collection=bpy.data.collections.new('ADULT BODY SOURCE — unfinished asset, hidden');bpy.context.scene.collection.children.link(collection)
    for obj in set(bpy.data.objects)-previous:
        for old in list(obj.users_collection):old.objects.unlink(obj)
        collection.objects.link(obj)
    collection.hide_viewport=True;collection.hide_render=True
    base['status']='Adult base mesh only. Surface anatomy, detailed skin, hair, facial shapes, garment fitting and visual review are unfinished. Do not call this a finished photoreal character.'
except Exception as error:
    print('Adult source build unavailable:',type(error).__name__,str(error))
# Ground and a neutral studio setup for animation review.
bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,-.015));floor=bpy.context.object;floor.name='Studio_Ground'
material=bpy.data.materials.new('Studio Ground');material.diffuse_color=(.08,.12,.10,1);floor.data.materials.append(material)
for name,location,power,size in [('Key',(3,-4,4),700,4),('Fill',(-3,-2,2),350,3),('Rim',(1,3,3),500,2)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-4.4,1.4));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=camera;camera.data.lens=52
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.fps=30;scene.frame_end=300
scene.world=bpy.data.worlds.new('Studio World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.14,1)
notes=bpy.data.texts.new('READ ME — production status');notes.write('Editable workshop, not a completed photographic character. The visible person is the original CC0 sample. MPFB adult base, when built, is in a hidden source collection. Limb IK controls are in PERFORMANCE CONTROLS; constraint influence starts at zero to preserve the sample. Author and bake corrected motion, then export a self-contained GLB for the studio motion library. Garments must be separate fitted meshes; dressing animation and anatomical surface detail require source work and inspection. No pose, motion or anatomy certification is implied.\n')
for image in bpy.data.images:
    if image.packed_file is None and image.source=='FILE':
        try:image.pack()
        except RuntimeError:pass
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Moneypenny-Character-Workshop.blend'))
print('WORKSHOP_READY',OUT/'Moneypenny-Character-Workshop.blend')
