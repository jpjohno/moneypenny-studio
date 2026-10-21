"""Prepare a data-only private Blender workshop from an authorised 4D source.

Run official Blender with --disable-autoexec -b -t 2 --python this-file --
SOURCE_DIR OUTPUT.blend. The original vendor blend, Alembic and textures are
never saved over. This creates a new workshop with native Alembic playback and
the matching image sequence; it does not install a scanner or create new scans.
"""
import argparse
from array import array
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zlib

import bpy
from mathutils import Vector


NOTES = """MONEYPENNY / PRIVATE 4D CAPTURE WORKSHOP

This is an existing recorded performance: Renderpeople Aliyah dance004.
Use the timeline or Space to play the 30 fps recording, frames1 through1112.
The Alembic mesh and its matching2K image sequence must remain available in the
original source folder. The new camera and recorded-light material are review
helpers. Select the captured mesh to orbit it, inspect the cache modifier or
change its display. Save your own additional copies before experimenting.

4D means a real captured3D surface changing over time. Its connectivity and UVs
can change between frames. It is not an ordinary skinned talking character,
not arbitrary generated movement, not autonomous AI and not a new scanner.
Clothing and hair are part of the captured surface. There is no hidden naked
body under it. It cannot be undressed to reveal data that was never captured.

No vendor Text script or Python handler is required for playback in this copy.
The original embedded scripts were not executed; they were removed from this
new workshop and replaced only with these plain notes. Do not enable scripts
from another downloaded project merely to view a recording.

This local workshop does not grant Gemini, another agent or an online service
access to your computer. An authorised editor can work on a separate local
copy or prepare Blender scripts; inspect edits and preserve the source files.
Do not upload this private source/cache/texture collection or redistribute it
to customers without confirming the applicable asset licence.
"""


def file_checks(path):
    digest, crc, size = hashlib.sha256(), 0, 0
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    return {'sha256': digest.hexdigest(), 'crc32': crc & 0xffffffff, 'bytes': size}


def source_path(root, value):
    value = str(value).replace('\\', '/').removeprefix('//')
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if root not in resolved.parents:
        raise ValueError('Source reference escapes the selected source directory')
    if resolved.is_file():
        return resolved
    # Windows drive references can be stale on a Mac. A unique local basename
    # is accepted only if it resolves inside the selected source directory.
    matches = [path.resolve() for path in root.rglob(candidate.name)
               if path.is_file() and root in path.resolve().parents]
    if len(matches) != 1:
        raise ValueError('Source reference absent or ambiguous: ' + candidate.name)
    return matches[0]


def native_render_log():
    # Capture native progress because Blender evaluates ImageUser on a copied
    # render dependency graph; the original RNA frame_current can remain zero.
    sys.stdout.flush()
    with tempfile.TemporaryFile(mode='w+b') as captured:
        original_fd = os.dup(1)
        try:
            os.dup2(captured.fileno(), 1)
            bpy.ops.render.render(write_still=False)
            sys.stdout.flush()
        finally:
            os.dup2(original_fd, 1)
            os.close(original_fd)
        captured.seek(0)
        return captured.read().decode('utf-8', errors='replace')


def geometry_frame(scene, obj, texture_node, frame, sequence_evidence=None):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    # Native image-sequence time is evaluated when a material is drawn, not
    # by frame_set alone. A tiny CPU-only in-memory render exercises that path.
    render_log = sequence_evidence if sequence_evidence is not None else native_render_log()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    co = array('f', [0.]) * (len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', co)
    triangles = array('i', [0]) * (len(mesh.loop_triangles) * 3)
    mesh.loop_triangles.foreach_get('vertices', triangles)
    if not mesh.uv_layers.active:
        raise ValueError('The evaluated capture frame has no UVs')
    uv = array('f', [0.]) * (len(mesh.uv_layers.active.data) * 2)
    mesh.uv_layers.active.data.foreach_get('uv', uv)
    world = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    result = {'frame': frame, 'vertices': len(mesh.vertices),
              'triangles': len(mesh.loop_triangles), 'uvLoops': len(mesh.uv_layers.active.data),
              'geometrySha256': hashlib.sha256(co.tobytes()).hexdigest(),
              'topologySha256': hashlib.sha256(triangles.tobytes()).hexdigest(),
              'uvSha256': hashlib.sha256(uv.tobytes()).hexdigest(),
              'worldBounds': {'min': [min(p[axis] for p in world) for axis in range(3)],
                              'max': [max(p[axis] for p in world) for axis in range(3)]}}
    evaluated.to_mesh_clear()
    # Rendering uses an evaluated ImageUser, not the original RNA cached frame.
    first = Path(texture_node.image.filepath).resolve()
    stem, dot, suffix = first.stem.rpartition('.')
    if not dot or not suffix.isdigit():
        raise ValueError('The source sequence has no numbered image suffix')
    current_image = first.with_name(stem + '.' + str(frame).zfill(len(suffix)) + first.suffix)
    native_lines = [line for line in render_log.splitlines()
                    if ('Fra:' + str(frame) + ' ') in line and 'Loading ' + current_image.name in line]
    if not native_lines:
        raise ValueError('No observed native image loading for source frame ' + str(frame))
    result['sequenceFile'] = str(current_image)
    result['sequenceFileExists'] = current_image.is_file()
    result['nativeImageLoadingObserved'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-blend', default='rp_aliyah_4d_004_dancing_2k.blend')
    parser.add_argument('--provenance', default='source-2k-verification.json')
    parser.add_argument('--sequence-evidence', type=Path, help='Optional log from this source’s already observed native frame1/100 renders; skips repeating them')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root, output = args.source_dir.resolve(), args.output.resolve()
    report_file = output.with_suffix('.verification.json')
    if output.suffix.lower() != '.blend' or output.exists() or report_file.exists():
        raise FileExistsError('Choose a new workshop blend and verification path')
    source_blend, provenance_file = source_path(root, args.source_blend), source_path(root, args.provenance)
    if output in (source_blend, provenance_file):
        raise ValueError('Never overwrite the original source')
    provenance = json.loads(provenance_file.read_text())
    if provenance.get('fps') != 30 or provenance.get('frames') != 1112:
        raise ValueError('This workshop is configured for the verified30fps1112-frame source')
    before = {source_blend: file_checks(source_blend), provenance_file: file_checks(provenance_file)}
    for entry in provenance['files']:
        path = source_path(root, entry['file'])
        check = file_checks(path)
        if check['bytes'] != entry['bytes'] or check['crc32'] != entry['crc32']:
            raise ValueError('Original source verification failed: ' + path.name)
        before[path] = check
    if output in before:
        raise ValueError('Never overwrite an original asset')
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(source_blend), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    if scene.frame_start != 1 or scene.frame_end != 1112:
        raise ValueError('Unexpected source frame range')
    scene.render.fps, scene.render.fps_base = 30, 1
    for cache in bpy.data.cache_files:
        cache.filepath = str(source_path(root, cache.filepath))
        cache.override_frame = False
    captures = [obj for obj in bpy.data.objects if obj.type == 'MESH'
                and any(mod.type == 'MESH_SEQUENCE_CACHE' for mod in obj.modifiers)]
    sequences = [image for image in bpy.data.images if image.source == 'SEQUENCE']
    if len(captures) != 1 or len(sequences) != 1:
        raise ValueError('Expected one Alembic capture and one image sequence')
    capture, image = captures[0], sequences[0]
    image.filepath = str(source_path(root, image.filepath))
    image.colorspace_settings.name = 'sRGB'
    original_texts = [text.name for text in bpy.data.texts]
    for text in list(bpy.data.texts):
        bpy.data.texts.remove(text)
    notes = bpy.data.texts.new('READ_ME_4D_WORKSHOP.txt')
    notes.write(NOTES)
    notes.use_module = False
    # Captured illumination is already present in the photo sequence. An
    # emission surface avoids accidentally lighting the captured shadows twice.
    material = bpy.data.materials.new('4D captured light / matching image sequence')
    material.use_nodes = True
    material.node_tree.nodes.clear()
    texture_node = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture_node.name = 'Captured frame image sequence'
    texture_node.image = image
    user = texture_node.image_user
    user.frame_start, user.frame_duration, user.frame_offset = 1, 1112, 0
    user.use_auto_refresh, user.use_cyclic = True, False
    emission = material.node_tree.nodes.new('ShaderNodeEmission')
    surface = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(texture_node.outputs['Color'], emission.inputs['Color'])
    material.node_tree.links.new(emission.outputs[0], surface.inputs['Surface'])
    capture.data.materials.clear()
    capture.data.materials.append(material)
    bpy.ops.object.camera_add(location=(0, -3, .85))
    diagnostic_camera = bpy.context.object
    diagnostic_camera.rotation_euler = (Vector((0, 0, .85)) - diagnostic_camera.location).to_track_quat('-Z', 'Y').to_euler()
    diagnostic_camera.data.type, diagnostic_camera.data.ortho_scale = 'ORTHO', 2
    scene.camera = diagnostic_camera
    scene.render.engine = 'CYCLES'
    scene.cycles.device, scene.cycles.samples = 'CPU', 1
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.render.resolution_x, scene.render.resolution_y = 16, 16
    scene.render.resolution_percentage = 100
    sequence_evidence = args.sequence_evidence.read_text() if args.sequence_evidence else None
    frames = [geometry_frame(scene, capture, texture_node, frame, sequence_evidence) for frame in (1, 100)]
    bpy.data.objects.remove(diagnostic_camera, do_unlink=True)
    for frame in frames:
        expected = str(frame['frame']).zfill(4) + '.jpg'
        if not frame['sequenceFileExists'] or not Path(frame['sequenceFile']).name.endswith(expected):
            raise ValueError('Native image sequence did not follow the current frame: ' + json.dumps(frame))
    if frames[0]['geometrySha256'] == frames[1]['geometrySha256']:
        raise ValueError('The Alembic surface did not advance')
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bounds = frames[0]['worldBounds']
    center = Vector(tuple((bounds['min'][axis] + bounds['max'][axis]) / 2 for axis in range(3)))
    height = bounds['max'][2] - bounds['min'][2]
    bpy.ops.object.camera_add(location=center + Vector((0, -height * 2.5, height * .08)))
    camera = bpy.context.object
    camera.name = '4D Workshop / full captured person'
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type, camera.data.ortho_scale = 'ORTHO', height * 1.25
    scene.camera = camera
    if scene.world is None:
        scene.world = bpy.data.worlds.new('4D workshop neutral world')
    scene.world.color = (.025, .025, .025)
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 800, 1000
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.shading.type = 'MATERIAL'
                space.shading.use_scene_world = True
                space.clip_end = 100
                space.region_3d.view_perspective = 'CAMERA'
    capture['workshop_recording_only'] = True
    capture['source_frame_range'] = '1-1112 at30fps'
    capture['not_an_interactive_speech_or_autonomy_rig'] = True
    bpy.ops.object.select_all(action='DESELECT')
    capture.select_set(True)
    bpy.context.view_layer.objects.active = capture
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=True)
    unchanged = all(file_checks(path) == checks for path, checks in before.items())
    if not unchanged:
        raise RuntimeError('An original source hash changed during preparation')
    report = {'workshop': str(output), 'bytes': output.stat().st_size,
              'sourceBlend': source_blend.name, 'sourceBlendSha256': before[source_blend]['sha256'],
              'provenance': provenance_file.name, 'provenanceSha256': before[provenance_file]['sha256'],
              'sourceFilesVerifiedUnchanged': len(before), 'originalSourcesUnchanged': True,
              'frames': frames, 'fps': 30, 'frameStart': 1, 'frameEnd': 1112,
              'embeddedSourceScriptsExecuted': False, 'removedVendorTextBlocks': original_texts,
              'savedTextBlocks': [text.name for text in bpy.data.texts],
              'imageSequenceAutoRefresh': user.use_auto_refresh,
              'sequenceRenderEvidence': {'reusedPriorObservedRenders': bool(args.sequence_evidence), 'sha256': file_checks(args.sequence_evidence)['sha256'] if args.sequence_evidence else None},
              'recordedPerformanceOnly': True, 'newScannerInstalled': False,
              'arbitraryMotionOrAutonomy': False, 'applicationDefaultsModified': False}
    report_file.write_text(json.dumps(report, indent=2) + '\n')
    print('FOURD_WORKSHOP_READY', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
