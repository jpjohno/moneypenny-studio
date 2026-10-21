#!/bin/zsh
set -e
studio_root="${0:A:h}"
blender_app="$HOME/Applications/Blender-4.5-LTS.app/Contents/MacOS/Blender"
body_file="$studio_root/.runtime/character-workshop/Moneypenny-Adult-Body-Source.blend"
anatomy_file="$studio_root/.runtime/character-workshop/Moneypenny-Adult-Anatomy-Study-v3.blend"
if [[ ! -x "$blender_app" ]]; then
  print 'Install Blender 4.5 LTS and MPFB from their official sites. See CHARACTER_WORKSHOP.md.'
  read '?Press Return to close.'
  exit 1
fi
if [[ -f "$anatomy_file" ]]; then
  exec "$blender_app" "$anatomy_file"
fi
if [[ ! -f "$body_file" ]]; then
  "$blender_app" --background --python "$studio_root/scripts/character/build_body_source.py" -- "$studio_root"
fi
exec "$blender_app" "$body_file"
