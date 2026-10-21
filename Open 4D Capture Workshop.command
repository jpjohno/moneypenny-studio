#!/bin/zsh
set -eu
studio_root="${0:A:h}"
exec python3 "$studio_root/scripts/launch_blender.py" --file "$studio_root/.runtime/scan-review/renderpeople-4d/workshop/Moneypenny-4D-Capture-Workshop.blend" --no-controls
