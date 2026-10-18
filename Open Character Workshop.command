#!/bin/zsh
set -e
studio_root="${0:A:h}"
blender_app="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
if [[ ! -x "$blender_app" ]]; then
  print 'Install Blender 4.5 LTS from blender.org, then see CHARACTER_WORKSHOP.md.'
  read '?Press Return to close.'
  exit 1
fi
workshop_file="$studio_root/.runtime/character-workshop/Moneypenny-Character-Workshop.blend"
if [[ ! -f "$workshop_file" ]]; then
  "$blender_app" --background --python "$studio_root/scripts/character/build_workshop.py" -- "$studio_root"
fi
exec "$blender_app" "$workshop_file"
