"""Resumable, deterministic native render sweep for material/light review.

Small previews compare actual 3D surfaces. Count is a search budget, never a
quality certificate. Full-size selected frames must still be visually reviewed.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--count',type=int,default=1000)
    parser.add_argument('--size',type=int,default=128)
    parser.add_argument('--samples',type=int,default=4)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--stop',type=int)
    parser.add_argument('--frame',type=int,help='Render one selected configuration at review resolution')
    parser.add_argument('--save-source',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not 1<=args.count<=1000 or not 64<=args.size<=1600 or not 1<=args.samples<=256:
        raise ValueError('Invalid bounded render budget')
    root=args.root.resolve()
    out=root/'.runtime/character-workshop'
    target=out/'surface-sweep'
    target.mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(out/'Moneypenny-Surface-Look-v7.blend'))
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=args.samples
    scene.cycles.use_denoising=args.samples>=16
    scene.cycles.use_adaptive_sampling=False
    scene.render.use_persistent_data=True
    scene.render.resolution_x=args.size
    scene.render.resolution_y=round(args.size*1.25)
    scene.render.resolution_percentage=100
    scene.camera.data.dof.use_dof=False
    rig=bpy.data.objects['Adult_Body_Rig']
    body=bpy.data.objects['Adult_Anatomy_Surface']
    skin=body.data.materials[0]
    shader=skin.node_tree.nodes.get('Principled BSDF')
    rough_input=shader.inputs['Roughness']
    rough_source=rough_input.links[0].from_socket
    rough_scale=skin.node_tree.nodes.new('ShaderNodeMath')
    rough_scale.operation='MULTIPLY'
    skin.node_tree.links.new(rough_source,rough_scale.inputs[0])
    skin.node_tree.links.new(rough_scale.outputs[0],rough_input)
    # Avoid reflecting two full glossy layers over the iris.
    eyes=next(o for o in bpy.data.objects if o.parent==rig and o.name.endswith('.high-poly'))
    eye_shader=next(n for n in eyes.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    eye_shader.inputs['Coat Weight'].default_value=0
    eye_shader.inputs['Specular IOR Level'].default_value=.18
    eye_shader.inputs['Roughness'].default_value=.35
    old_hair=next(o for o in bpy.data.objects if o.parent==rig and '.ponytail01' in o.name)
    lara=next(o for o in bpy.data.objects if o.parent==rig and '.elvs_lara_hair' in o.name)
    strands=bpy.data.objects['Hair_Individual_Strands']
    key=bpy.data.objects['Large portrait key']
    fill=bpy.data.objects['Cool portrait fill']
    rim=bpy.data.objects['Hair separation']
    # Hair variants are contiguous so persistent geometry is reused per group.
    def configuration(index):
        return {'index':index,'hair':['cap-strands','lara','lara-strands','strands'][index//250],
                'skin_roughness_scale':.85+((index%5)/4)*.35,
                'subsurface_weight':.06+((index//5)%5)/4*.14,
                'exposure':-.9+((index//25)%5)/4*.8,
                'fill_ratio':.16+((index//125)%2)*.2}
    def apply(config):
        mode=config['hair']
        old_hair.hide_render=mode!='cap-strands'
        lara.hide_render=mode not in ('lara','lara-strands')
        strands.hide_render=mode=='lara'
        rough_scale.inputs[1].default_value=config['skin_roughness_scale']
        shader.inputs['Subsurface Weight'].default_value=config['subsurface_weight']
        scene.view_settings.exposure=config['exposure']
        key.data.energy=40
        fill.data.energy=40*config['fill_ratio']
        rim.data.energy=12
    indices=[args.frame] if args.frame is not None else range(args.start,min(args.count,args.stop or args.count))
    started=time.time()
    manifest=target/'renders.jsonl'
    for index in indices:
        if not 0<=index<1000: raise ValueError('Variant outside bounded grid')
        config=configuration(index)
        suffix='review' if args.frame is not None else 'preview'
        file=target/f'{index:04d}-{suffix}.png'
        if file.exists() and args.frame is None:
            continue
        apply(config)
        scene.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
        record={**config,'file':file.name,'width':args.size,'samples':args.samples,'rendered':True}
        with manifest.open('a') as output: output.write(json.dumps(record)+'\n')
        if index%25==0 or args.frame is not None:
            print('SWEEP_PROGRESS',json.dumps({'last_index':index,'elapsed_seconds':round(time.time()-started,1),'record':record}),flush=True)
        if args.save_source:
            bpy.ops.wm.save_as_mainfile(filepath=str(out/f'Moneypenny-Surface-Review-{index:04d}.blend'))
    print('SWEEP_COMPLETE',json.dumps({'requested_budget':args.count,'elapsed_seconds':round(time.time()-started,1),'render_directory':str(target)}),flush=True)


if __name__=='__main__': main()
