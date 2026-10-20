"""Convert an authorised private Alembic study to bounded browser review frames.

Run with Blender --disable-autoexec -b -t 2 --python this-file -- SOURCE OUTPUT.
No embedded source Text blocks execute. The source blend/cache/textures are
read-only; only derived GLBs and the atomic output manifest are written. Each
frame evaluates its own topology/UVs and explicitly loads its matching image.
This is recorded 4D playback, not a speaking rig or generated motion.
"""
import argparse
from array import array
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import time

import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--blend', help='Source blend filename; required if ambiguous')
    parser.add_argument('--label', default='Renderpeople Aliyah dance004', help='Honest label for the captured source clip')
    parser.add_argument('--source-frames', help='Comma-separated source indices for a small review')
    parser.add_argument('--step', type=int, default=2)
    parser.add_argument('--texture-size', type=int, choices=[512, 1024], default=512)
    parser.add_argument('--quality', type=int, default=85)
    parser.add_argument('--render-preview', type=Path)
    parser.add_argument('--resume', action='store_true')
    return parser.parse_args(sys.argv[sys.argv.index('--') + 1:])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_source_path(source, value):
    # Blender projects authored on Windows can retain backslashes in // paths.
    relative = str(value).replace('\\', '/').removeprefix('//')
    direct = (source / relative).resolve()
    if direct.is_relative_to(source) and direct.is_file():
        return direct
    matches = [path.resolve() for path in source.rglob(Path(relative).name)
               if path.is_file() and path.resolve().is_relative_to(source)]
    if len(matches) != 1:
        raise ValueError('Source path is absent or ambiguous: ' + Path(relative).name)
    return matches[0].resolve()


def yup_bounds(obj, mesh):
    points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    return {
        'min': [min(p.x for p in points), min(p.z for p in points), min(-p.y for p in points)],
        'max': [max(p.x for p in points), max(p.z for p in points), max(-p.y for p in points)],
    }


def merge_bounds(frames):
    return {
        'min': [min(frame['bounds']['min'][axis] for frame in frames) for axis in range(3)],
        'max': [max(frame['bounds']['max'][axis] for frame in frames) for axis in range(3)],
    }


def write_manifest(path, manifest):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(path)


def render_preview(scene, snapshot, path, bounds):
    # A fully clothed source frame, framed from its actual current bounds.
    center = Vector(((bounds['min'][0] + bounds['max'][0]) / 2,
                     -(bounds['min'][2] + bounds['max'][2]) / 2,
                     (bounds['min'][1] + bounds['max'][1]) / 2))
    height = bounds['max'][1] - bounds['min'][1]
    bpy.ops.object.camera_add(location=center + Vector((0, -height * 2, .1 * height)))
    camera = bpy.context.object
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(height * 1.12, 1)
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 4
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x = 512
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    if scene.world is None:
        scene.world = bpy.data.worlds.new('Private 4D review world')
    scene.world.color = (.025, .025, .025)
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)


def main():
    args = arguments()
    source, output = args.source.resolve(), args.output.resolve()
    if not 1 <= args.step <= 30 or not 50 <= args.quality <= 100:
        raise ValueError('Unsupported conversion budget')
    if output == source or output.name in ('tex_2k', 'tex_4k'):
        raise ValueError('Choose a separate derived output directory')
    blends = [source / args.blend] if args.blend else list(source.glob('*.blend'))
    if len(blends) != 1 or not blends[0].is_file():
        raise ValueError('Choose exactly one source blend')
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(blends[0]), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    for cache in bpy.data.cache_files:
        cache.filepath = str(resolve_source_path(source, cache.filepath))
        cache.override_frame = False
    candidates = [obj for obj in bpy.data.objects if obj.type == 'MESH'
                  and any(mod.type == 'MESH_SEQUENCE_CACHE' for mod in obj.modifiers)]
    if len(candidates) != 1:
        raise ValueError('Expected one recorded mesh cache')
    original = candidates[0]
    sequences = [image for image in bpy.data.images if image.source == 'SEQUENCE']
    if len(sequences) != 1:
        raise ValueError('Expected one matching diffuse image sequence')
    first_image = resolve_source_path(source, sequences[0].filepath)
    prefix, _, suffix = first_image.name.rpartition('.')
    # Sequence filenames conventionally finish in .0001.jpg.
    stem, separator, number = prefix.rpartition('.')
    if not separator or not number.isdigit():
        raise ValueError('Image sequence has no numeric frame suffix')
    padding = len(number)
    source_fps = scene.render.fps / scene.render.fps_base
    all_frames = list(range(scene.frame_start, scene.frame_end + 1, args.step))
    indices = [int(value) for value in args.source_frames.split(',')] if args.source_frames else all_frames
    if not indices or len(set(indices)) != len(indices) or any(index < scene.frame_start or index > scene.frame_end for index in indices):
        raise ValueError('Source frame indices are invalid')
    fps = source_fps / args.step
    if not fps.is_integer():
        raise ValueError('Use an integral browser frame rate for this review')
    output.mkdir(parents=True, exist_ok=True)
    frames_dir = output / 'frames'
    frames_dir.mkdir(exist_ok=True)
    scratch = tempfile.TemporaryDirectory(prefix='.frame-', dir=output)
    temporary_image = Path(scratch.name) / 'current.jpg'
    manifest_path = output / 'manifest.json'
    old = json.loads(manifest_path.read_text()) if args.resume and manifest_path.is_file() else {}
    old_info = {entry['index']: entry for entry in old.get('frameInfo', [])}
    infos = []
    started = time.monotonic()
    original.hide_render = True
    for index, source_frame in enumerate(indices):
        relative = 'frames/frame' + str(index).zfill(4) + '.glb'
        destination = output / relative
        texture = first_image.parent / (stem + '.' + str(source_frame).zfill(padding) + '.' + suffix)
        if not texture.is_file():
            raise ValueError('Matching source texture is missing: ' + texture.name)
        previous = old_info.get(index)
        if previous and destination.is_file() and previous.get('sourceFrame') == source_frame and old.get('textureSize') == args.texture_size and previous.get('sha256') == sha(destination):
            infos.append(previous)
        else:
            if destination.exists():
                raise FileExistsError('Existing derived frame differs; choose a new output or matching --resume: ' + relative)
            scene.frame_set(source_frame)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated = original.evaluated_get(depsgraph)
            mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
            if not mesh.vertices or not mesh.uv_layers:
                raise ValueError('Evaluated cache frame has no surface or UVs')
            snapshot = bpy.data.objects.new('Recorded_4D_Frame', mesh)
            scene.collection.objects.link(snapshot)
            snapshot.matrix_world = original.matrix_world.copy()
            bounds = yup_bounds(snapshot, mesh)
            values = array('f', [0.]) * (len(mesh.vertices) * 3)
            mesh.vertices.foreach_get('co', values)
            geometry_hash = hashlib.sha256(values.tobytes()).hexdigest()
            mesh.calc_loop_triangles()
            image = bpy.data.images.load(str(texture), check_existing=False)
            image.source = 'FILE'
            image.colorspace_settings.name = 'sRGB'
            image.scale(args.texture_size, args.texture_size)
            image.filepath_raw = str(temporary_image)
            image.file_format = 'JPEG'
            image.save()
            bpy.data.images.remove(image)
            # Reload a true resized file; exporter must not reuse source2K bytes.
            image = bpy.data.images.load(str(temporary_image), check_existing=False)
            image.colorspace_settings.name = 'sRGB'
            material = bpy.data.materials.new('Recorded captured lighting')
            material.use_nodes = True
            material.node_tree.nodes.clear()
            tex = material.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image = image
            emission = material.node_tree.nodes.new('ShaderNodeEmission')
            surface = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
            material.node_tree.links.new(tex.outputs['Color'], emission.inputs['Color'])
            material.node_tree.links.new(emission.outputs[0], surface.inputs['Surface'])
            mesh.materials.clear()
            mesh.materials.append(material)
            bpy.ops.object.select_all(action='DESELECT')
            snapshot.select_set(True)
            bpy.context.view_layer.objects.active = snapshot
            bpy.ops.export_scene.gltf(filepath=str(destination), export_format='GLB',
                use_selection=True, export_animations=False, export_apply=True,
                export_skins=False, export_morph=False, export_extras=False,
                export_image_format='JPEG', export_jpeg_quality=args.quality)
            info = {'index': index, 'sourceFrame': source_frame, 'url': relative,
                    'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles),
                    'uvLayers': len(mesh.uv_layers), 'bounds': bounds,
                    'geometrySha256': geometry_hash, 'sourceTextureSha256': sha(texture),
                    'bytes': destination.stat().st_size, 'sha256': sha(destination)}
            if index == 0 and args.render_preview:
                render_preview(scene, snapshot, args.render_preview.resolve(), bounds)
            infos.append(info)
            bpy.data.objects.remove(snapshot, do_unlink=True)
            bpy.data.meshes.remove(mesh)
            bpy.data.materials.remove(material)
            bpy.data.images.remove(image)
            if index % 25 == 0:
                gc.collect()
        complete = len(infos) == len(indices)
        manifest = {'fps': int(fps), 'frames': [entry['url'] for entry in infos],
                    'sourceFrames': [entry['sourceFrame'] for entry in infos],
                    'bounds': merge_bounds(infos), 'frameInfo': infos,
                    'textureSize': args.texture_size, 'sourceFPS': source_fps,
                    'durationSeconds': len(infos) / fps,
                    'metadata': {'kind': 'recorded-4d', 'source': args.label,
                                 'fullSequence': complete and indices == all_frames,
                                 'totalSourceFrames': scene.frame_end - scene.frame_start + 1,
                                 'sourceUnchanged': True, 'activeCharacterUnchanged': True,
                                 'embeddedScriptsExecuted': False,
                                 'capturedLighting': True, 'interactiveSpeechRig': False},
                    'conversionComplete': complete, 'requestedFrameCount': len(indices),
                    'totalBytes': sum(entry['bytes'] for entry in infos)}
        write_manifest(manifest_path, manifest)
        if index % 25 == 0 or complete:
            print('FOURD_PROGRESS', json.dumps({'frames': len(infos), 'requested': len(indices),
                  'bytes': manifest['totalBytes'], 'elapsedSeconds': round(time.monotonic() - started, 2)}), flush=True)
    # This is a derived scratch image only; no source image is changed or removed.
    scratch.cleanup()


if __name__ == '__main__':
    main()
