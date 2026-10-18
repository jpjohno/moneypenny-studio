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
