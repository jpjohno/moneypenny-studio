"""Locate the real Blender installation and open the local authoring source."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def blender_path():
    candidates = [os.environ.get('MONEYPENNY_BLENDER'),
                  str(Path.home() / 'Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender'),
                  '/Applications/Blender.app/Contents/MacOS/Blender', shutil.which('blender')]
    return next((Path(p) for p in candidates if p and Path(p).is_file() and os.access(p, os.X_OK)), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, help='An explicitly chosen .blend source')
    parser.add_argument('--check', action='store_true', help='Check paths without opening or modifying Blender')
    parser.add_argument('--no-controls', action='store_true', help='Open a body or captured-mesh study without the humanoid motion panel')
    args = parser.parse_args()
    executable = blender_path()
    if not executable:
        raise SystemExit('Blender was not found. Set MONEYPENNY_BLENDER to its executable path.')
    workshop = ROOT / '.runtime/character-workshop'
    source = args.file or next((workshop / name for name in (
        'Moneypenny-Style-v26.blend', 'Moneypenny-Style-v25.blend', 'Moneypenny-Free-Surface-Reviewed.blend', 'Moneypenny-Surface-Look-v9.blend', 'Moneypenny-Performance-Final-Fit-v3.blend')
        if (workshop / name).is_file()), workshop / 'Moneypenny-Performance-Final-Fit-v3.blend')
    if not source.is_file():
        raise SystemExit('Local character source was not found. Use --file /path/to/source.blend or build the performance source first.')
    print(f'Blender: {executable}\nSource: {source}\nExisting Blender windows and unsaved work are left alone.', flush=True)
    if not args.check:
        command = [str(executable), '--disable-autoexec', str(source)]
        if not args.no_controls:
            command += ['--python', str(ROOT / 'scripts/character/studio_controls.py')]
        return subprocess.call(command, cwd=ROOT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
