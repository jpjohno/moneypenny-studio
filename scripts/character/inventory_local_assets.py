"""Record saved local character deliverables without publishing their contents."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'Moneypenny-Adult-Body-Source.blend': 'Parametric body source',
    'Moneypenny-Adult-Anatomy-Study-v3.blend': 'Earlier editable anatomical study',
    'Moneypenny-Performance-Final-Fit-v3.blend': 'Latest dressed performance source',
    'Moneypenny-Performance-Export-v6.blend': 'Baked export source',
    'Moneypenny-Performance-Candidate-v6.glb': 'Geometry-verified private character candidate',
    'performance-skin-roughness.png': 'Baked procedural roughness',
    'performance-skin-normal.png': 'Baked procedural surface normal',
    'Moneypenny-Surface-Look-v9.blend': 'Procedural surface study source',
    'Moneypenny-Performance-Candidate-v9.glb': 'Reviewed procedural surface study',
    'Moneypenny-Free-Surface-v10.blend': 'Unoptimised free CC0 character assembly',
    'Moneypenny-Free-Surface-v13.blend': 'Free character browser source',
    'Moneypenny-Free-Surface-v13.glb': 'Free character browser candidate',
    'Moneypenny-Free-Surface-v16.blend': 'Rejected full-character prototype; CC0 bob source reused',
    'Moneypenny-Style-v20.blend': 'Complete local authoring source; styled clothed character',
    'Moneypenny-Style-v20.glb': 'Clothed browser export with covered-torso face mask',
    'Moneypenny-Style-v22.blend': 'Complete v22 local authoring source; cooler blonde bob and softened brows',
    'Moneypenny-Style-v22.glb': 'Clothed v22 browser export; covered-torso face mask',
    'Moneypenny-Style-v23.blend': 'Complete v23 local authoring source; longer warm blonde bob and slimmer cheeks',
    'Moneypenny-Style-v23.glb': 'Clothed v23 browser export; chest weights and torso coverage corrected',
    'Moneypenny-Style-v24.blend': 'v24 complete local styling source',
    'Moneypenny-Style-v24.glb': 'v24 clothed browser export with cutout bob and scalp coverage',
    'Moneypenny-Style-v25.blend': 'v25 complete local source with stronger cheekbone definition',
    'Moneypenny-Style-v25.glb': 'v25 clothed browser candidate; natural eye atlas and cutout bob',
    'Moneypenny-Style-v26.blend': 'v26 complete source with balanced profile and refitted blouse',
    'Moneypenny-Style-v26.glb': 'v26 clothed browser candidate; balanced profile and Jarvis presence source',
}


def main():
    items = []
    for name, role in FILES.items():
        path = ROOT / '.runtime/character-workshop' / name
        item = {'path': path.relative_to(ROOT).as_posix(), 'role': role, 'present': path.is_file()}
        if path.is_file():
            with path.open('rb') as source:
                item.update(bytes=path.stat().st_size, sha256=hashlib.file_digest(source, 'sha256').hexdigest())
        items.append(item)
    manifest = {'scope': 'Saved local files only. Unsaved Blender edits are not included.',
                'asset_contents_published_to_git': False,
                'commercial_redistribution_cleared': False,
                'rebuild': 'See CHARACTER_WORKSHOP.md and Build Performance Character.command',
                'files': items}
    destination = ROOT / 'LOCAL_CHARACTER_ASSETS.json'
    destination.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Inventoried {len(items)} local deliverables; no asset contents uploaded.')


if __name__ == '__main__':
    main()
