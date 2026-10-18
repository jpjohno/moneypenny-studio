#!/bin/zsh
set -eu
studio_root="${0:A:h}"
exec python3 "$studio_root/scripts/launch_blender.py"
