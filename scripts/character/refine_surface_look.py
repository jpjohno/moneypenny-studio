"""Build a reversible surface look-development candidate from the working rig.

Retains the original texture, skinning and speech shapes. Microdetail is
procedural, not captured skin or a claim of photographic reconstruction.
Outputs a new packed source, browser GLB, portrait and provenance report.
"""
import argparse
import json
import math
import random
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = args.root.resolve()
    out = root / '.runtime/character-workshop'
    source = out / 'Moneypenny-Performance-Export-v6.blend'
    destination = out / 'Moneypenny-Surface-Look-v7.blend'
    candidate = out / 'Moneypenny-Performance-Candidate-v7.glb'
    if destination.exists() or candidate.exists():
        raise SystemExit('Existing v7 preserved. Review it before rebuilding.')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    body = bpy.data.objects['Adult_Anatomy_Surface']
    rig = bpy.data.objects['Adult_Body_Rig']
    skin = body.data.materials[0]
    nodes, links = skin.node_tree.nodes, skin.node_tree.links
    shader = nodes.get('Principled BSDF')
    output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    # Spatially varying oil/roughness follows the actual head, lips and hands,
    # rather than giving the entire body one plastic highlight response.
    attr = body.data.attributes.new(name='SurfaceRoughness', type='FLOAT', domain='POINT')
    for vertex, value in zip(body.data.vertices, attr.data):
        x, y, z = vertex.co
        front = max(0, min(1, (-y - .04) / .04))
        nose = math.exp(-((x / .018)**2 + ((z - 1.466) / .025)**2)) * front
        forehead = math.exp(-((x / .045)**2 + ((z - 1.535) / .026)**2)) * front
        lips = math.exp(-((x / .029)**4 + ((z - 1.431) / .008)**4)) * front
        value.value = .49 - .13 * nose - .045 * forehead - .18 * lips
    attribute = nodes.new('ShaderNodeAttribute')
    attribute.attribute_name = 'SurfaceRoughness'
    attribute.label = 'Face-specific oil and lip response'
    coordinates = nodes.new('ShaderNodeTexCoord')
    fine = nodes.new('ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value = 1900
    fine.inputs['Detail'].default_value = 2
    fine.inputs['Roughness'].default_value = .65
    links.new(coordinates.outputs['Object'], fine.inputs['Vector'])
    coarse = nodes.new('ShaderNodeTexNoise')
    coarse.inputs['Scale'].default_value = 320
    coarse.inputs['Detail'].default_value = 3
    links.new(coordinates.outputs['Object'], coarse.inputs['Vector'])
    bump_coarse = nodes.new('ShaderNodeBump')
    bump_coarse.inputs['Strength'].default_value = .13
    bump_coarse.inputs['Distance'].default_value = .000035
    links.new(coarse.outputs['Fac'], bump_coarse.inputs['Height'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .23
    bump.inputs['Distance'].default_value = .000025
    links.new(fine.outputs['Fac'], bump.inputs['Height'])
    links.new(bump_coarse.outputs['Normal'], bump.inputs['Normal'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    links.new(attribute.outputs['Fac'], shader.inputs['Roughness'])
    shader.inputs['IOR'].default_value = 1.4
    shader.inputs['Specular IOR Level'].default_value = .32
    shader.inputs['Subsurface Weight'].default_value = .14
    shader.inputs['Subsurface Radius'].default_value = (1, .42, .23)
    shader.inputs['Subsurface Scale'].default_value = .0012
    # Independent strand tones avoid a single broad white scalp highlight.
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.parent != rig:
            continue
        for material in obj.data.materials:
            if not material or not material.use_nodes:
                continue
            bsdf = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if not bsdf:
                continue
            if 'ponytail' in obj.name:
                bsdf.inputs['Roughness'].default_value = .52
                bsdf.inputs['Specular IOR Level'].default_value = .22
            elif obj.name == 'Hair_Individual_Strands':
                bsdf.inputs['Roughness'].default_value = .42
                bsdf.inputs['Specular IOR Level'].default_value = .27
                anisotropy = bsdf.inputs.get('Anisotropic IOR Level') or bsdf.inputs.get('Anisotropic')
                if anisotropy is not None:
                    anisotropy.default_value = .65
            elif 'high-poly' in obj.name:
                bsdf.inputs['Roughness'].default_value = .23
                bsdf.inputs['Coat Weight'].default_value = .32
                bsdf.inputs['Coat Roughness'].default_value = .06
            elif 'Corneal' in obj.name:
                bsdf.inputs['IOR'].default_value = 1.376
                bsdf.inputs['Roughness'].default_value = .018
    # Add tapered, individually skinned short brow hairs over the existing cards.
    rng = random.Random(20261018)
    verts, faces = [], []
    for brow in [o for o in bpy.data.objects if 'eyebrow001' in o.name and o.type == 'MESH' and o.parent == rig]:
        triangles = []
        for face in brow.data.polygons:
            ids = list(face.vertices)
            for i in range(1, len(ids)-1):
                a,b,c = [brow.matrix_world @ brow.data.vertices[k].co for k in (ids[0], ids[i], ids[i+1])]
                area = (b-a).cross(c-a).length / 2
                if area:
                    triangles.append((a,b,c,area))
        for n in range(760):
            a,b,c,_ = rng.choices(triangles, weights=[t[3] for t in triangles])[0]
            u,v = rng.random(),rng.random()
            if u+v > 1: u,v = 1-u,1-v
            p = a*(1-u-v)+b*u+c*v
            p.y -= .0006
            length = rng.uniform(.0018,.0038)
            side = 1 if p.x > 0 else -1
            direction = Vector((side*.65, -.08, .75)).normalized()
            start = len(verts)
            for step in range(4):
                t=step/3
                center = p + direction*length*t + Vector((0,-math.sin(t*math.pi)*.0003,0))
                radius = .000045*(1-.92*t)
                for corner in range(3):
                    angle=corner*math.tau/3
                    verts.append(center+Vector((radius*math.cos(angle),radius*math.sin(angle),0)))
                if step:
                    for corner in range(3):
                        faces.append((start+(step-1)*3+corner,start+(step-1)*3+(corner+1)%3,start+step*3+(corner+1)%3,start+step*3+corner))
    mesh = bpy.data.meshes.new('Tapered brow filaments')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    brows = bpy.data.objects.new('Brow_Individual_Strands',mesh)
    scene.collection.objects.link(brows)
    brows.parent=rig
    group=brows.vertex_groups.new(name='Head')
    group.add(list(range(len(verts))),1,'REPLACE')
    modifier=brows.modifiers.new('Head skinning','ARMATURE')
    modifier.object=rig
    material=bpy.data.materials.new('Brow filaments — natural brown')
    material.use_nodes=True
    bsdf=material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(.045,.017,.009,1)
    bsdf.inputs['Roughness'].default_value=.52
    mesh.materials.append(material)
    for polygon in mesh.polygons: polygon.use_smooth=True
    # Bake native microgeometry into portable browser normal/roughness textures.
    scene.render.engine='CYCLES'
    scene.cycles.samples=1
    scene.cycles.use_denoising=True
    scene.render.bake.margin=12
    for obj in bpy.context.selected_objects: obj.select_set(False)
    body.hide_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active=body
    texture=nodes.new('ShaderNodeTexImage')
    rough=bpy.data.images.new('v7 spatial skin roughness',2048,2048,alpha=False)
    rough.colorspace_settings.name='Non-Color'
    texture.image=rough
    nodes.active=texture
    emission=nodes.new('ShaderNodeEmission')
    links.new(attribute.outputs['Fac'],emission.inputs['Color'])
    links.new(emission.outputs[0],output.inputs['Surface'])
    bpy.ops.object.bake(type='EMIT')
    links.new(shader.outputs[0],output.inputs['Surface'])
    nodes.remove(emission)
    rough.filepath_raw=str(out/'surface-v7-roughness.png')
    rough.file_format='PNG'
    rough.save()
    rough.pack()
    normal=bpy.data.images.new('v7 multiscale skin normal',2048,2048,alpha=False)
    normal.colorspace_settings.name='Non-Color'
    target=nodes.new('ShaderNodeTexImage')
    target.image=normal
    nodes.active=target
    bpy.ops.object.bake(type='NORMAL')
    normal.filepath_raw=str(out/'surface-v7-normal.png')
    normal.file_format='PNG'
    normal.save()
    normal.pack()
    links.new(texture.outputs['Color'],shader.inputs['Roughness'])
    normal_node=nodes.new('ShaderNodeNormalMap')
    links.new(target.outputs['Color'],normal_node.inputs['Color'])
    links.new(normal_node.outputs['Normal'],shader.inputs['Normal'])
    parts=[o for o in bpy.data.objects if o.parent==rig and o.type=='MESH' and not o.hide_render]
    for obj in bpy.context.selected_objects: obj.select_set(False)
    rig.hide_set(False)
    rig.select_set(True)
    for obj in parts:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    rig['surface_revision']='v7 — layered skin, optical eyes, groom and brow detail'
    bpy.ops.export_scene.gltf(filepath=str(candidate),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_skins=True,export_extras=True,export_apply=False)
    if candidate.stat().st_size>80*1024*1024: raise ValueError('Candidate exceeds browser import limit')
    # Packed native look scene and real rendered portrait; preserve the v6 source.
    for obj in parts:
        for modifier in obj.modifiers:
            if modifier.type=='SUBSURF': modifier.show_render=True
    for obj in [o for o in bpy.data.objects if o.type=='LIGHT']:
        bpy.data.objects.remove(obj,do_unlink=True)
    def area(name,position,power,size,color):
        data=bpy.data.lights.new(name,'AREA')
        data.energy=power
        data.shape='DISK'
        data.size=size
        data.color=color
        obj=bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location=position
        obj.rotation_euler=(Vector((0,0,1.4))-obj.location).to_track_quat('-Z','Y').to_euler()
    area('Large portrait key',(-.65,-1.0,2.05),65,.8,(1,.9,.8))
    area('Cool portrait fill',(.75,-.6,1.65),24,.7,(.82,.89,1))
    area('Hair separation',(.3,.5,1.95),55,.55,(1,.92,.84))
    scene.world.use_nodes=True
    background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
    background.inputs['Color'].default_value=(.085,.1,.12,1)
    background.inputs['Strength'].default_value=.32
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=0
    camera=scene.camera
    camera.data.type='PERSP'
    camera.data.lens=85
    camera.data.dof.use_dof=True
    camera.data.dof.focus_distance=1.22
    camera.data.dof.aperture_fstop=8
    camera.location=(.16,-1.22,1.50)
    camera.rotation_euler=(Vector((0,-.015,1.44))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=760
    scene.render.resolution_y=960
    scene.render.resolution_percentage=100
    scene.cycles.samples=48
    scene.cycles.adaptive_threshold=.045
    scene.render.image_settings.file_format='PNG'
    portrait=root/'verification/surface-v7-portrait.png'
    scene.render.filepath=str(portrait)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    bpy.ops.render.render(write_still=True)
    report={'revision':'v7','source':str(source.relative_to(root)),'output':str(candidate.relative_to(root)),
            'bytes':candidate.stat().st_size,'new_brow_strands':len(verts)//12,
            'skin_color':'Existing 2048px MargaretToigo CC0 painted skin; no invented scan claim',
            'new_maps':['2048px spatial roughness','2048px multiscale normal'],
            'hair':'Existing skinned groom retained; revised reflectance and tapered brow filaments',
            'render':str(portrait.relative_to(root)),'photographic_realism_verified':False,
            'commercial_rights_cleared':False,'body_geometry_and_speech_shapes':'Preserved'}
    (out/'surface-v7-report.json').write_text(json.dumps(report,indent=2))
    print('SURFACE_CANDIDATE_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__': main()
